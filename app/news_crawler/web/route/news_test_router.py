from fastapi import APIRouter, Path
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.common.config.api_metadata import common_responses
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import success_response, handle_service_error

router = APIRouter()


@router.post(
    "/{symbol}",
    response_model=ApiResponse,
    summary="뉴스 크롤링 테스트",
    description="""
    특정 심볼에 대한 Yahoo Finance 뉴스를 크롤링하여 데이터베이스에 저장합니다.
    
    **주요 기능:**
    - Yahoo Finance에서 최신 뉴스 수집
    - 뉴스 데이터 정제 및 저장
    - 중복 뉴스 필터링
    
    **사용 용도:**
    - 뉴스 크롤링 시스템 테스트
    - 특정 종목 뉴스 수동 수집
    - 크롤링 성능 검증
    """,
    tags=["News Crawler"],
    responses={
        **common_responses,
        200: {
            "description": "뉴스 크롤링이 성공적으로 완료되었습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "AAPL 뉴스 크롤링이 완료되었습니다",
                        "data": {
                            "symbol": "AAPL",
                            "crawled_count": 15,
                            "saved_count": 12,
                            "duplicate_count": 3,
                        },
                    }
                }
            },
        },
    },
)
def crawl_and_save_news(
    symbol: str = Path(
        ...,
        example="AAPL",
        description="뉴스를 크롤링할 주식 심볼",
        min_length=1,
        max_length=10,
    )
):
    """
    지정된 심볼의 Yahoo Finance 뉴스를 크롤링하여 저장합니다.

    크롤링된 뉴스는 자동으로 데이터베이스에 저장되며,
    중복 뉴스는 필터링됩니다.
    """
    try:
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()

        return success_response(
            data={"symbol": symbol, "result": result},
            message=f"{symbol} 뉴스 크롤링이 완료되었습니다",
        )
    except Exception as e:
        handle_service_error(e, f"{symbol} 뉴스 크롤링 실패")
