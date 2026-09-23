"""Database models for imported UCI customer data and prediction history."""

from datetime import datetime, timezone

from app.extensions import db


class Customer(db.Model):
    """A customer identified by a simple, reusable dashboard-facing code."""

    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    predictions = db.relationship(
        "PredictionRecord", back_populates="customer", lazy="dynamic", cascade="all, delete-orphan"
    )


class CustomerProfile(db.Model):
    """Historical UCI features used to complete a prediction request."""

    __tablename__ = "customer_profiles"

    id = db.Column(db.Integer, primary_key=True)
    uci_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    LIMIT_BAL = db.Column(db.Float, nullable=False)
    SEX = db.Column(db.Float, nullable=False)
    EDUCATION = db.Column(db.Float, nullable=False)
    MARRIAGE = db.Column(db.Float, nullable=False)
    AGE = db.Column(db.Float, nullable=False)
    PAY_0 = db.Column(db.Float, nullable=False)
    PAY_2 = db.Column(db.Float, nullable=False)
    PAY_3 = db.Column(db.Float, nullable=False)
    PAY_4 = db.Column(db.Float, nullable=False)
    PAY_5 = db.Column(db.Float, nullable=False)
    PAY_6 = db.Column(db.Float, nullable=False)
    BILL_AMT2 = db.Column(db.Float, nullable=False)
    BILL_AMT3 = db.Column(db.Float, nullable=False)
    BILL_AMT4 = db.Column(db.Float, nullable=False)
    BILL_AMT5 = db.Column(db.Float, nullable=False)
    BILL_AMT6 = db.Column(db.Float, nullable=False)
    PAY_AMT2 = db.Column(db.Float, nullable=False)
    PAY_AMT3 = db.Column(db.Float, nullable=False)
    PAY_AMT4 = db.Column(db.Float, nullable=False)
    PAY_AMT5 = db.Column(db.Float, nullable=False)
    PAY_AMT6 = db.Column(db.Float, nullable=False)

    def to_raw_dict(self, current_month=None):
        """Return the stored fields needed by notebook preprocessing, with current month override."""
        data = {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name not in {"id", "uci_id"}
        }

        if current_month:
            data["BILL_AMT1"] = float(current_month.get("BILL_AMT1", data.get("BILL_AMT1", 0.0)))
            data["PAY_AMT1"] = float(current_month.get("PAY_AMT1", data.get("PAY_AMT1", 0.0)))

        for column_name in [
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
        ]:
            data.setdefault(column_name, 0.0)

        return data


class PredictionRecord(db.Model):
    """One prediction and the latest month values submitted for it."""

    __tablename__ = "prediction_records"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("customer_profiles.id"), nullable=False, index=True)
    customer = db.relationship("Customer", back_populates="predictions")
    BILL_AMT1 = db.Column(db.Float, nullable=False)
    PAY_AMT1 = db.Column(db.Float, nullable=False)
    Total_bill = db.Column(db.Float, nullable=False)
    Total_pay = db.Column(db.Float, nullable=False)
    Outstanding = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    prediction_label = db.Column(db.String(32), nullable=False)
    default_probability = db.Column(db.Float, nullable=False)
    selected_model = db.Column(db.String(64), nullable=False)
    model_predictions = db.Column(db.JSON, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
