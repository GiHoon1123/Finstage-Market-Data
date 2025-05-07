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
    result = service.get_statements_from_db(symbol)

    if not result:
        return {"message": f"{symbol}에 대한 데이터가 DB에 없습니다."}

    return result