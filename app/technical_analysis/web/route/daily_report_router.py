"""
일일 종합 분석 리포트 API 라우터

일일 종합 분석 리포트 관련 API 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)
from app.technical_analysis.dto.report_response import DailyReportResponse
from app.common.config.api_metadata import common_responses

router = APIRouter()


@router.post(
    "/generate",
    response_model=DailyReportResponse,
    summary="일일 종합 분석 리포트 생성",
    description="""
    당일의 모든 기술적 분석 데이터를 종합하여 일일 리포트를 생성합니다.
    
    **포함 내용:**
    - 시장 전체 요약
    - 발생한 신호들 분석
    - 성과 지표 계산
    - 투자 추천 사항
    - 위험 요소 분석
    
    **활용 방안:**
    - 일일 투자 브리핑
    - 포트폴리오 점검
    - 시장 동향 파악
    """,
    tags=["Daily Report"],
    responses={
        **common_responses,
        201: {
            "description": "일일 리포트가 성공적으로 생성되었습니다.",
            "model": DailyReportResponse,
        },
    },
)
async def generate_daily_report() -> DailyReportResponse:
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


@router.get(
    "/preview",
    response_model=DailyReportResponse,
    summary="일일 리포트 미리보기",
    description="""
    실제 생성하지 않고 일일 리포트의 미리보기를 제공합니다.
    
    **주요 기능:**
    - 빠른 데이터 요약
    - 리소스 절약형 미리보기
    - 실시간 시장 상황 반영
    """,
    tags=["Daily Report"],
)
async def preview_daily_report() -> DailyReportResponse:
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


@router.get(
    "/status",
    summary="리포트 시스템 상태",
    description="일일 리포트 생성 시스템의 상태를 확인합니다.",
    tags=["Daily Report"],
)
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


@router.get(
    "/health",
    summary="리포트 서비스 헬스 체크",
    description="일일 리포트 서비스의 상태를 확인합니다.",
    tags=["Health Check"],
)
async def health_check():
    """일일 리포트 서비스 헬스 체크"""
    return {
        "service": "Daily Comprehensive Report",
        "status": "healthy",
        "description": "매일 오전 8시 종합 분석 리포트 자동 생성 및 전송",
    }
