# app/services/company_import_service.py

import json
from sqlalchemy.dialects.mysql import insert
from app.models.symbol import Symbol
from app.infra.db.db import SessionLocal

FILE_PATH = "app/infra/data/nasdaq_full_tickers.json"


def import_symbols_from_file():
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 필요한 필드만 추출
    records = [
        {
            "symbol": item["symbol"],
            "name": item["name"],
            "country": item["country"],
        }
        for item in raw
        if "symbol" in item and "name" in item and "country" in item
    ]

    session = SessionLocal()
    try:
        for record in records:
            stmt = insert(Symbol).values(**record)
            stmt = stmt.on_duplicate_key_update(
                name=stmt.inserted.name,
                country=stmt.inserted.country,
            )
            session.execute(stmt)
        session.commit()
        print(f"[✓] {len(records)} companies upserted.")
    except Exception as e:
        session.rollback()
        print(f"[✗] Error during import: {e}")
    finally:
        session.close()


def run_import():
    print(">>> Importing company data from JSON file...")
    import_symbols_from_file()
    print(">>> Done.")


# If you want to run directly:
if __name__ == "__main__":
    run_import()
