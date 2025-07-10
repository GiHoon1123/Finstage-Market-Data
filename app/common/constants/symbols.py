from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class SymbolInfo:
    name: str                          # 표시 이름 (예: "애플")
    category: str                      # 뉴스나 분류용 카테고리 (예: "종목", "지수")
    monitoring_category: str          # 모니터링 기준 카테고리 (예: "ETF(Long)")
    is_monitored: bool = True         # 실시간 가격 체크 여부

# 심볼별 등록 정보
SYMBOL_REGISTRY: Dict[str, SymbolInfo] = {
    # ✅ 지수
    "^IXIC": SymbolInfo("나스닥 지수", "지수", "지수"),
    "^GSPC": SymbolInfo("S&P 500 지수", "지수", "지수"),
    "^DJI":  SymbolInfo("다우존스 지수", "지수", "지수"),

    # ✅ 선물
    "ES=F":  SymbolInfo("S&P 500 선물", "선물", "선물"),
    "NQ=F":  SymbolInfo("나스닥 선물", "선물", "선물"),
    "YM=F":  SymbolInfo("다우존스 선물", "선물", "선물"),

    # ✅ 종목
    "AAPL": SymbolInfo("애플", "종목", "종목"),
    "AMZN": SymbolInfo("아마존", "종목", "종목"),
    "GOOGL": SymbolInfo("구글", "종목", "종목"),
    "TSLA": SymbolInfo("테슬라", "종목", "종목"),
    "MSFT": SymbolInfo("마이크로소프트", "종목", "종목"),
    "META": SymbolInfo("메타", "종목", "종목"),
    "NVDA": SymbolInfo("엔비디아", "종목", "종목"),

    # ✅ ETF(Long)
    "SOXL": SymbolInfo("디렉시온 미국 반도체 3배 ETF", "ETF", "ETF(Long)"),
    "TQQQ": SymbolInfo("프로셰어즈 QQQ 3배 ETF", "ETF", "ETF(Long)"),
    "TSLL": SymbolInfo("디렉시온 테슬라 2배 ETF", "ETF", "ETF(Long)"),
    "NVDL": SymbolInfo("그래닛셰어즈 엔비디아 데일리 2배 롱 ETF", "ETF", "ETF(Long)"),

    # ✅ ETF(Short)
    "SOXS": SymbolInfo("디렉시온 미국 반도체 3배 인버스 ETF", "ETF", "ETF(Short)"),
    "SQQQ": SymbolInfo("프로셰어즈 QQQ 3배 인버스 ETF", "ETF", "ETF(Short)"),
    "TSLQ": SymbolInfo("TRADR 테슬라 2배 인버스 ETF", "ETF", "ETF(Short)"),
    "NVD":  SymbolInfo("그래닛셰어즈 엔비디아 데일리 2배 인버스 ETF", "ETF", "ETF(Short)"),

    # ✅ 뉴스 전용
    "INVESTING:ECONOMY": SymbolInfo("인베스팅 경제 뉴스", "국제뉴스", "뉴스", is_monitored=False),
    "INVESTING:US": SymbolInfo("인베스팅 미국 뉴스", "국제뉴스", "뉴스", is_monitored=False),
    "INVESTING:MARKET": SymbolInfo("인베스팅 시장 분석", "국제뉴스", "뉴스", is_monitored=False),
    "INVESTING:COMMODITY": SymbolInfo("인베스팅 원자재 뉴스", "국제뉴스", "뉴스", is_monitored=False),
    "INVESTING:FOREX": SymbolInfo("인베스팅 외환 뉴스", "국제뉴스", "뉴스", is_monitored=False),
}
