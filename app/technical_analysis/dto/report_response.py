from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class DailyReportResponse(BaseModel):
    """일일 리포트 응답 모델"""

    report_id: str = Field(..., example="report_20250809", description="리포트 ID")
    generated_at: str = Field(
        ..., example="2025-08-09T12:00:00Z", description="생성 시간"
    )
    market_summary: Dict[str, Any] = Field(..., description="시장 요약")
    signal_summary: Dict[str, Any] = Field(..., description="신호 요약")
    performance_metrics: Dict[str, Any] = Field(..., description="성과 지표")
    recommendations: List[str] = Field(..., description="추천 사항")

    class Config:
        schema_extra = {
            "example": {
                "report_id": "report_20250809",
                "generated_at": "2025-08-09T12:00:00Z",
                "market_summary": {
                    "total_signals": 45,
                    "bullish_signals": 28,
                    "bearish_signals": 17,
                },
                "signal_summary": {
                    "ma_breakouts": 12,
                    "rsi_signals": 8,
                    "macd_signals": 15,
                },
                "performance_metrics": {"success_rate": 72.5, "avg_return": 2.3},
                "recommendations": ["AAPL 매수 신호 강함", "MSFT 관심 종목으로 추가"],
            }
        }
