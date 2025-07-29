"""
일일 종합 분석 리포트 API 라우터

일일 종합 분석 리포트 관련 API 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)

router = APIRouter()


@router.post("/generate", summary="일일 종합 분석 리포트 생성")
async def generate_daily_report() -> Dict[str, Any]:
    """
    일일 종합 분석 리포트를 수동으로 생성하고 텔레그램으로 전송합니다.

    Returns:
        리포트 생성 결과
    """
    try:
        service = DailyComprehensiveReportService()
        result = service.generate_daily_report()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "status": "success",
            "message": "일일 종합 분석 리포트가 성공적으로 생성되고 전송되었습니다.",
            "result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 생성 실패: {str(e)}")


@router.get("/preview", summary="일일 종합 분석 리포트 미리보기")
async def preview_daily_report() -> Dict[str, Any]:
    """
    일일 종합 분석 리포트의 미리보기를 생성합니다 (텔레그램 전송 없음).

    Returns:
        리포트 미리보기 내용
    """
    try:
        service = DailyComprehensiveReportService()

        # 각 분석 모듈별 데이터 수집
        backtesting_data = service._get_backtesting_analysis()
        pattern_data = service._get_pattern_analysis()
        ml_data = service._get_ml_analysis()
        insights_data = service._get_investment_insights()

        # 리포트 메시지 생성 (전송은 하지 않음)
        report_message = service._generate_report_message(
            backtesting_data, pattern_data, ml_data, insights_data
        )

        return {
            "status": "success",
            "message": "리포트 미리보기가 생성되었습니다.",
            "preview": {
                "report_message": report_message,
                "message_length": len(report_message),
                "analysis_modules": {
                    "backtesting": (
                        len(backtesting_data)
                        if isinstance(backtesting_data, dict)
                        else 0
                    ),
                    "patterns": (
                        len(pattern_data) if isinstance(pattern_data, dict) else 0
                    ),
                    "ml_analysis": len(ml_data) if isinstance(ml_data, dict) else 0,
                    "insights": (
                        len(insights_data) if isinstance(insights_data, dict) else 0
                    ),
                },
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"미리보기 생성 실패: {str(e)}")


@router.get("/status", summary="일일 리포트 시스템 상태 확인")
async def get_report_status() -> Dict[str, Any]:
    """
    일일 종합 분석 리포트 시스템의 상태를 확인합니다.

    Returns:
        시스템 상태 정보
    """
    try:
        service = DailyComprehensiveReportService()

        # 각 서비스 상태 확인
        status_info = {
            "backtesting_service": "available",
            "pattern_service": "available",
            "advanced_pattern_service": "available",
            "target_symbols": service.target_symbols,
            "symbol_names": service.symbol_names,
        }

        # 간단한 연결 테스트
        try:
            session = service._get_session()
            if session:
                status_info["database_connection"] = "connected"
                session.close()
            else:
                status_info["database_connection"] = "disconnected"
        except Exception as e:
            status_info["database_connection"] = f"error: {str(e)}"

        return {
            "status": "healthy",
            "message": "일일 리포트 시스템이 정상 작동 중입니다.",
            "system_info": status_info,
            "features": [
                "백테스팅 성과 분석",
                "패턴 분석 결과",
                "머신러닝 기반 분석",
                "투자 인사이트 제공",
                "용어 해설 포함",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.get("/health", summary="헬스 체크")
async def health_check():
    """일일 리포트 서비스 헬스 체크"""
    return {
        "service": "Daily Comprehensive Report",
        "status": "healthy",
        "description": "매일 오전 8시 종합 분석 리포트 자동 생성 및 전송",
    }
