"""Import UCI customer history into the configured database."""

from pathlib import Path

import pandas as pd

from app import create_app
from app.extensions import db
from app.models import CustomerProfile


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "UCI_Credit_Card.xls"

PROFILE_COLUMNS = [
    "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE", "PAY_0",
    "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
]


def main():
    """Create the profile table and upsert all UCI rows."""
    data = pd.read_excel(DATASET_PATH, header=1)
    data = data.rename(columns={"ID": "uci_id"})
    missing = {"uci_id", *PROFILE_COLUMNS} - set(data.columns)
    if missing:
        raise ValueError("Dataset is missing columns: " + ", ".join(sorted(missing)))

    app = create_app()
    with app.app_context():
        db.create_all()
        for row in data[["uci_id", *PROFILE_COLUMNS]].to_dict(orient="records"):
            profile = CustomerProfile.query.filter_by(uci_id=int(row["uci_id"])).first()
            if profile is None:
                profile = CustomerProfile(uci_id=int(row.pop("uci_id")))
                db.session.add(profile)
            else:
                row.pop("uci_id")
            for column, value in row.items():
                setattr(profile, column, float(value))
        db.session.commit()
    print(f"Imported {len(data)} customer profiles into customer_profiles.")


if __name__ == "__main__":
    main()