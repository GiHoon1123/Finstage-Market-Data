from typing import Optional, Dict
from app.company.service.financial_service import load_statements  # 너가 방금 작성한 함수 import

def handle_get_financials(symbol: str) -> Optional[Dict]:
    return load_statements(symbol)
