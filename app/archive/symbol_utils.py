from typing import Optional, List
from app.archive.symbols import SYMBOL_REGISTRY, SymbolInfo

def get_symbol_name(symbol: str) -> str:
    return SYMBOL_REGISTRY.get(symbol, SymbolInfo(name=symbol, category="기타", monitoring_category="기타")).name

def get_symbol_category(symbol: str) -> str:
    return SYMBOL_REGISTRY.get(symbol, SymbolInfo(name=symbol, category="기타", monitoring_category="기타")).category

def get_monitoring_category(symbol: str) -> str:
    return SYMBOL_REGISTRY.get(symbol, SymbolInfo(name=symbol, category="기타", monitoring_category="기타")).monitoring_category

def is_monitored_symbol(symbol: str) -> bool:
    return SYMBOL_REGISTRY.get(symbol, SymbolInfo(name=symbol, category="기타", monitoring_category="기타")).is_monitored

def get_all_monitored_symbols() -> List[str]:
    return [symbol for symbol, info in SYMBOL_REGISTRY.items() if info.is_monitored]
