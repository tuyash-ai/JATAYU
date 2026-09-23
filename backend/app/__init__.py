"""Flask application factory for the Credit Card Default Prediction API."""

import os
from pathlib import Path

import pandas as pd
from flask import Flask
from sqlalchemy import inspect, text

from config import Config
from app.extensions import cors, db
from app.models import CustomerProfile
from app.routes.health import health_bp
from app.routes.predict import predict_bp
from app.routes.dashboard import dashboard_bp


REQUIRED_PREDICTION_COLUMNS = {
    "id",
    "customer_id",
    "profile_id",
    "BILL_AMT1",
    "PAY_AMT1",
    "Total_bill",
    "Total_pay",
    "Outstanding",
    "prediction",
    "prediction_label",
    "default_probability",
    "selected_model",
    "model_predictions",
    "created_at",
}

PROFILE_COLUMNS = [
    "LIMIT_BAL",
    "SEX",
    "EDUCATION",
    "MARRIAGE",
    "AGE",
    "PAY_0",
    "PAY_2",
    "PAY_3",
    "PAY_4",
    "PAY_5",
    "PAY_6",
    "BILL_AMT2",
    "BILL_AMT3",
    "BILL_AMT4",
    "BILL_AMT5",
    "BILL_AMT6",
    "PAY_AMT2",
    "PAY_AMT3",
    "PAY_AMT4",
    "PAY_AMT5",
    "PAY_AMT6",
]
PROFILE_EXPECTED_COLUMNS = {"id", "uci_id", *PROFILE_COLUMNS}


def _seed_customer_profiles():
    """Populate the customer profile table from the UCI Excel without duplicate IDs."""
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "UCI_Credit_Card.xls"
    if not dataset_path.exists():
        return

    data = pd.read_excel(dataset_path, header=1)
    data = data.rename(columns={"ID": "uci_id"})

    existing_rows = {profile.uci_id: profile for profile in CustomerProfile.query.all()}
    for row in data[["uci_id", *PROFILE_COLUMNS]].to_dict(orient="records"):
        uci_id = int(row["uci_id"])
        profile = existing_rows.get(uci_id)
        if profile is None:
            profile = CustomerProfile(uci_id=uci_id)
            db.session.add(profile)

        for column, value in row.items():
            if column == "uci_id":
                continue
            setattr(profile, column, float(value))

    db.session.commit()


def create_app(config_class=Config, reset_database=False):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["RESET_DATABASE_ON_START"] = reset_database or str(
        os.getenv("RESET_DATABASE", "")
    ).lower() in {"1", "true", "yes"}

    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    app.register_blueprint(health_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        if app.config["RESET_DATABASE_ON_START"]:
            db.drop_all()
        else:
            if "prediction_records" in tables:
                columns = {column["name"] for column in inspector.get_columns("prediction_records")}
                if columns != REQUIRED_PREDICTION_COLUMNS:
                    db.session.execute(text("DROP TABLE IF EXISTS prediction_records"))
                    db.session.commit()

            if "customer_profiles" in tables:
                columns = {column["name"] for column in inspector.get_columns("customer_profiles")}
                if columns != PROFILE_EXPECTED_COLUMNS:
                    db.session.execute(text("DROP TABLE IF EXISTS customer_profiles"))
                    db.session.commit()

        db.create_all()
        _seed_customer_profiles()

    return app
