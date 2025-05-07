from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.services.financial_service import FinancialService
from app.infra.db.db import get_db
import pandas as pd
import json

router = APIRouter()

def safe_df_to_dict(df: pd.DataFrame) -> dict:
    return json.loads(df.to_json())

@router.get("/financials")
def get_financials(symbol: str = Query(...), db: Session = Depends(get_db)):
    service = FinancialService(db)
    result = service.load_statements(symbol)

    if not result:
        return None

    return result
