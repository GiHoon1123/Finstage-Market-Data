"""
비동기 API 라우터 예시

FastAPI의 비동기 기능을 활용한 고성능 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.common.utils.async_api_client import AsyncApiClient
from app.common.utils.async_executor import async_timed
from app.common.utils.cache_manager import default_cache_manager
from app.common.utils.performance_monitor import measure_time

# 라우터 생성
router = APIRouter()

# 비동기 API 클라이언트
yahoo_client = AsyncApiClient()


@router.get("/async/symbols/{symbol}/price")
@async_timed()
async def get_symbol_price(symbol: str):
    """
    심볼의 현재 가격 조회 (비동기)

    Args:
        symbol: 주식 심볼 (예: AAPL, MSFT)
    """
    # 캐시 키
    cache_key = f"price:{symbol}"

    # 캐시 확인
    cached_data = default_cache_manager.get(cache_key)
    if cached_data:
        return {
            "symbol": symbol,
            "price": cached_data["price"],
            "timestamp": cached_data["timestamp"],
            "source": "cache",
        }

    # Yahoo Finance API URL
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "1d"}

    try:
        # 비동기 API 호출
        data = await yahoo_client.get(url, params)

        # 응답 파싱
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice")
        timestamp = datetime.now().isoformat()

        # 결과 생성
        response = {
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp,
            "source": "api",
        }

        # 캐시에 저장 (5분)
        default_cache_manager.set(
            cache_key, {"price": price, "timestamp": timestamp}, ttl=300
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API 호출 실패: {str(e)}")


@router.get("/async/symbols/batch")
@async_timed()
async def get_batch_prices(
    symbols: str = Query(..., description="쉼표로 구분된 심볼 목록")
):
    """
    여러 심볼의 가격을 한 번에 조회 (비동기 병렬 처리)

    Args:
        symbols: 쉼표로 구분된 심볼 목록 (예: AAPL,MSFT,GOOG)
    """
    # 심볼 목록 파싱
    symbol_list = [s.strip() for s in symbols.split(",")]

    # 비동기 API 클라이언트
    async with AsyncApiClient() as client:
        # URL 목록 생성
        urls = [
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            for symbol in symbol_list
        ]
        params = {"interval": "1d", "range": "1d"}

        # 병렬 요청 실행
        results = await client.fetch_multiple(urls, params, concurrency=5, delay=0.2)

    # 결과 처리
    prices = {}
    for i, result in enumerate(results):
        symbol = symbol_list[i]
        if result and "chart" in result and result["chart"]["result"]:
            price = result["chart"]["result"][0]["meta"].get("regularMarketPrice")
            prices[symbol] = price
        else:
            prices[symbol] = None

    return {"timestamp": datetime.now().isoformat(), "prices": prices}


@router.get("/async/technical/analysis/{symbol}")
@async_timed()
async def get_technical_analysis(symbol: str, period: str = "1mo"):
    """
    기술적 분석 결과 조회 (비동기)

    Args:
        symbol: 주식 심볼 (예: AAPL, MSFT)
        period: 데이터 기간 (예: 1d, 1mo, 3mo, 1y)
    """
    # 캐시 키
    cache_key = f"tech_analysis:{symbol}:{period}"

    # 캐시 확인
    cached_data = default_cache_manager.get(cache_key)
    if cached_data:
        return {**cached_data, "source": "cache"}

    # Yahoo Finance API URL
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": period}

    try:
        # 비동기 API 호출
        data = await yahoo_client.get(url, params)

        # 응답 파싱
        result = data["chart"]["result"][0]

        # 간단한 기술적 분석 수행
        timestamp = result["timestamp"]
        close_prices = result["indicators"]["quote"][0]["close"]

        # 이동평균 계산
        ma_20 = (
            sum(close_prices[-20:]) / min(20, len(close_prices))
            if len(close_prices) >= 5
            else None
        )
        ma_50 = (
            sum(close_prices[-50:]) / min(50, len(close_prices))
            if len(close_prices) >= 10
            else None
        )

        # 현재 가격
        current_price = close_prices[-1] if close_prices else None

        # 분석 결과
        analysis = {
            "symbol": symbol,
            "current_price": current_price,
            "ma_20": ma_20,
            "ma_50": ma_50,
            "timestamp": datetime.now().isoformat(),
            "trend": "bullish" if (ma_20 and current_price > ma_20) else "bearish",
            "source": "api",
        }

        # 캐시에 저장 (10분)
        default_cache_manager.set(
            cache_key, {k: v for k, v in analysis.items() if k != "source"}, ttl=600
        )

        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기술적 분석 실패: {str(e)}")
