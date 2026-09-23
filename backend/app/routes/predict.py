"""Prediction endpoint backed by the saved ML pipeline."""

from functools import lru_cache
from pathlib import Path
from statistics import mode

import joblib
import pandas as pd
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.extensions import db
from app.models import Customer, CustomerProfile, PredictionRecord
from app.schemas import PredictionRequest
from ml.feature_engineering import transform_raw_input


predict_bp = Blueprint("predict", __name__, url_prefix="/api")
MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "credit_default_full_model_bundle.pkl"


@lru_cache(maxsize=1)
def get_model_assets():
    """Load the uploaded bundle containing models, thresholds, and metadata."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing trained model file: {MODEL_PATH.name}")
    artifact = joblib.load(MODEL_PATH)
    precision_scores = {
        model_key: metrics["threshold_tuned_f1"]["precision"]
        for model_key, metrics in artifact["test_metrics"].items()
    }
    best_model_key = max(precision_scores, key=precision_scores.get)
    display_names = {
        "random_forest": "Random Forest",
        "xgboost": "XGBoost",
        "logistic_regression": "Logistic Regression",
    }
    return {
        "pipelines": artifact["models"],
        "thresholds": artifact["thresholds"],
        "selected_model": {
            "name": display_names[best_model_key],
            "key": best_model_key,
            "precision": precision_scores[best_model_key],
        },
        "ensemble_method": artifact["ensemble"]["method"],
        "selection_metric": "precision",
    }


@predict_bp.post("/predict")
def predict():
    """Look up a customer, add current-month values, and predict risk."""
    try:
        payload = PredictionRequest.model_validate(request.get_json(silent=True))
    except ValidationError as error:
        return jsonify({"success": False, "error": error.errors()}), 400

    try:
        profile = CustomerProfile.query.filter_by(uci_id=payload.customer_id).first()
        if profile is None:
            return jsonify({"success": False, "error": "Customer ID was not found."}), 404

        raw_values = profile.to_raw_dict(
            {
                "BILL_AMT1": float(payload.BILL_AMT1),
                "PAY_AMT1": float(payload.PAY_AMT1),
            }
        )

        required_raw_columns = [
            "LIMIT_BAL",
            "AGE",
            "PAY_0",
            "BILL_AMT1",
            "BILL_AMT2",
            "BILL_AMT3",
            "BILL_AMT4",
            "BILL_AMT5",
            "BILL_AMT6",
            "PAY_AMT1",
            "PAY_AMT2",
            "PAY_AMT3",
            "PAY_AMT4",
            "PAY_AMT5",
            "PAY_AMT6",
        ]
        for column_name in required_raw_columns:
            raw_values.setdefault(column_name, 0.0)

        raw_frame = pd.DataFrame([raw_values])
        model_input = transform_raw_input(raw_frame)
        assets = get_model_assets()
        model_results = []

        display_names = {
            "random_forest": "Random Forest",
            "xgboost": "XGBoost",
            "logistic_regression": "Logistic Regression",
        }
        for model_key, pipeline in assets["pipelines"].items():
            default_probability = float(pipeline.predict_proba(model_input)[0, 1])
            threshold = float(assets["thresholds"][model_key])
            prediction_value = int(default_probability >= threshold)
            model_results.append(
                {
                    "name": display_names.get(model_key, model_key),
                    "is_best_model": model_key == assets["selected_model"]["key"],
                    "value": prediction_value,
                    "label": "Default" if prediction_value == 1 else "No Default",
                    "default_probability": default_probability,
                    "threshold": threshold,
                    "shap_explanation": [],
                }
            )

        model_results.sort(key=lambda item: not item["is_best_model"])
        prediction_value = mode([item["value"] for item in model_results])
        prediction_label = "Default" if prediction_value == 1 else "No Default"
        default_probability = sum(item["default_probability"] for item in model_results) / len(model_results)
        stored_model_predictions = {
            item["name"]: item for item in model_results
        }
        model_features = model_input.iloc[0]
        total_bill = sum(raw_values[f"BILL_AMT{i}"] for i in range(1, 7))
        total_pay = sum(raw_values[f"PAY_AMT{i}"] for i in range(1, 7))
        outstanding = total_bill - total_pay
    except FileNotFoundError as error:
        return jsonify({"success": False, "error": str(error)}), 503
    except (KeyError, TypeError, ValueError, OSError) as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception as error:
        return jsonify({"success": False, "error": f"Model is unavailable: {error}"}), 503

    customer = Customer.query.filter_by(customer_code=str(profile.uci_id)).first()
    if customer is None:
        customer = Customer(customer_code=str(profile.uci_id))
        db.session.add(customer)
        db.session.flush()

    record = PredictionRecord(
        customer=customer,
        profile_id=profile.id,
        BILL_AMT1=payload.BILL_AMT1,
        PAY_AMT1=payload.PAY_AMT1,
        Total_bill=float(total_bill),
        Total_pay=float(total_pay),
        Outstanding=float(outstanding),
        prediction=prediction_value,
        prediction_label=prediction_label,
        default_probability=default_probability,
        selected_model=assets["selected_model"]["name"],
        model_predictions=stored_model_predictions,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "prediction": {
                "value": prediction_value,
                "label": prediction_label,
                "default_probability": default_probability,
            },
            "best_model": assets["selected_model"]["name"],
            "selection_metric": assets["selection_metric"],
            "final_verdict": prediction_label,
            "models": model_results,
            "features": {
                "LIMIT_BAL": float(model_features["LIMIT_BAL"]),
                "AGE": float(model_features["AGE"]),
                "PAY_0": float(model_features["PAY_0"]),
                "BILL_AMT1": float(model_features["BILL_AMT1"]),
                "Total_bill": float(total_bill),
                "Total_pay": float(total_pay),
                "Outstanding": float(outstanding),
            },
            "prediction_id": record.id,
            "customer_code": customer.customer_code,
            "customer_id": profile.uci_id,
        }
    ), 200
