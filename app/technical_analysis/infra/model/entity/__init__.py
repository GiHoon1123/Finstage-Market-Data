"""
기술적 분석 엔티티 패키지

SQLAlchemy 매핑 순서를 정의하여 순환 참조 문제를 해결합니다.
"""

# 의존성이 없는 엔티티부터 임포트
from .daily_prices import DailyPrice
from .technical_signals import TechnicalSignal
from .signal_outcomes import SignalOutcome
from .signal_patterns import SignalPattern

# 모든 엔티티를 한 번에 임포트할 수 있도록 __all__ 정의
__all__ = ["DailyPrice", "TechnicalSignal", "SignalOutcome", "SignalPattern"]
