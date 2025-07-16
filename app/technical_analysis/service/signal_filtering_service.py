"""
신호 필터링 서비스

Phase 3의 핵심 기능으로, 신호 품질 기반 지능형 필터링을 제공합니다.

주요 기능:
1. 품질 기반 필터링 - A등급 신호만 알림 발송
2. 사용자별 맞춤 설정 - 개인화된 알림 기준
3. 적응형 임계값 - 시장 상황에 따른 동적 조정
4. 중복 신호 제거 - 유사한 신호들의 스팸 방지
5. 시장 상황 필터 - 상승장/하락장에 따른 선별적 알림

필터링 기준:
- 신호 품질 점수 (0~100점)
- 과거 성공률 (백테스팅 기반)
- 시장 상황 적합성
- 신호 강도 (돌파폭, RSI 수준 등)
- 거래량 확인 (거래량 급증 여부)
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.service.backtesting_service import BacktestingService
from app.technical_analysis.infra.model.repository.technical_signal_repository import TechnicalSignalRepository
from app.technical_analysis.infra.model.repository.signal_outcome_repository import SignalOutcomeRepository
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class SignalFilteringService:
    """
    신호 필터링을 담당하는 서비스
    
    신호 품질 기반으로 알림 발송 여부를 결정합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.signal_repository: Optional[TechnicalSignalRepository] = None
        self.outcome_repository: Optional[SignalOutcomeRepository] = None
        self.backtesting_service = BacktestingService()
        
        # 기본 필터링 설정
        self.default_settings = {
            "min_quality_score": 70,  # B등급 이상
            "min_success_rate": 0.6,  # 60% 이상 성공률
            "min_signal_strength": 0.5,  # 최소 신호 강도
            "require_volume_confirmation": True,  # 거래량 확인 필요
            "max_signals_per_hour": 3,  # 시간당 최대 알림 수
            "enabled_signal_types": [
                "MA200_breakout_up",
                "MA200_breakout_down", 
                "golden_cross",
                "dead_cross",
                "RSI_oversold",
                "RSI_overbought"
            ],
            "market_condition_filter": True,  # 시장 상황 필터 사용
        }

    def _get_session_and_repositories(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.signal_repository = TechnicalSignalRepository(self.session)
            self.outcome_repository = SignalOutcomeRepository(self.session)
        return self.session, self.signal_repository, self.outcome_repository

    # =================================================================
    # 메인 필터링 함수
    # =================================================================

    def should_send_alert(
        self, 
        signal: TechnicalSignal, 
        user_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        신호에 대한 알림 발송 여부 결정
        
        Args:
            signal: 평가할 신호
            user_settings: 사용자별 설정 (None이면 기본 설정 사용)
            
        Returns:
            필터링 결과
            {
                "should_send": bool,
                "reason": str,
                "quality_score": float,
                "filter_results": dict
            }
        """
        session, signal_repo, outcome_repo = self._get_session_and_repositories()
        
        try:
            # 설정 병합
            settings = self._merge_settings(user_settings)
            
            print(f"🔍 신호 필터링 시작: {signal.signal_type} ({signal.symbol})")
            
            # 각 필터 적용
            filter_results = {}
            
            # 1. 신호 타입 필터
            type_filter = self._check_signal_type_filter(signal, settings)
            filter_results["signal_type"] = type_filter
            
            if not type_filter["passed"]:
                return self._create_filter_result(False, type_filter["reason"], 0, filter_results)
            
            # 2. 품질 점수 필터
            quality_filter = self._check_quality_score_filter(signal, settings)
            filter_results["quality_score"] = quality_filter
            
            if not quality_filter["passed"]:
                return self._create_filter_result(False, quality_filter["reason"], quality_filter["score"], filter_results)
            
            # 3. 성공률 필터
            success_rate_filter = self._check_success_rate_filter(signal, settings)
            filter_results["success_rate"] = success_rate_filter
            
            if not success_rate_filter["passed"]:
                return self._create_filter_result(False, success_rate_filter["reason"], quality_filter["score"], filter_results)
            
            # 4. 신호 강도 필터
            strength_filter = self._check_signal_strength_filter(signal, settings)
            filter_results["signal_strength"] = strength_filter
            
            if not strength_filter["passed"]:
                return self._create_filter_result(False, strength_filter["reason"], quality_filter["score"], filter_results)
            
            # 5. 거래량 필터
            volume_filter = self._check_volume_filter(signal, settings)
            filter_results["volume"] = volume_filter
            
            if not volume_filter["passed"]:
                return self._create_filter_result(False, volume_filter["reason"], quality_filter["score"], filter_results)
            
            # 6. 중복 신호 필터
            duplicate_filter = self._check_duplicate_filter(signal, settings)
            filter_results["duplicate"] = duplicate_filter
            
            if not duplicate_filter["passed"]:
                return self._create_filter_result(False, duplicate_filter["reason"], quality_filter["score"], filter_results)
            
            # 7. 시장 상황 필터
            market_filter = self._check_market_condition_filter(signal, settings)
            filter_results["market_condition"] = market_filter
            
            if not market_filter["passed"]:
                return self._create_filter_result(False, market_filter["reason"], quality_filter["score"], filter_results)
            
            # 8. 알림 빈도 제한
            frequency_filter = self._check_frequency_limit_filter(signal, settings)
            filter_results["frequency"] = frequency_filter
            
            if not frequency_filter["passed"]:
                return self._create_filter_result(False, frequency_filter["reason"], quality_filter["score"], filter_results)
            
            # 모든 필터 통과
            print(f"✅ 모든 필터 통과: {signal.signal_type} (품질점수: {quality_filter['score']:.1f})")
            return self._create_filter_result(True, "모든 필터 조건을 만족합니다", quality_filter["score"], filter_results)
            
        except Exception as e:
            print(f"❌ 신호 필터링 실패: {e}")
            return self._create_filter_result(False, f"필터링 오류: {str(e)}", 0, {})
        finally:
            session.close()

    def _create_filter_result(
        self, should_send: bool, reason: str, quality_score: float, filter_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """필터링 결과 생성"""
        return {
            "should_send": should_send,
            "reason": reason,
            "quality_score": quality_score,
            "filter_results": filter_results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _merge_settings(self, user_settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """사용자 설정과 기본 설정 병합"""
        settings = self.default_settings.copy()
        if user_settings:
            settings.update(user_settings)
        return settings

    # =================================================================
    # 개별 필터 함수들
    # =================================================================

    def _check_signal_type_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """신호 타입 필터"""
        enabled_types = settings.get("enabled_signal_types", [])
        
        if not enabled_types:  # 빈 리스트면 모든 타입 허용
            return {"passed": True, "reason": "모든 신호 타입 허용"}
        
        if signal.signal_type in enabled_types:
            return {"passed": True, "reason": "허용된 신호 타입"}
        else:
            return {"passed": False, "reason": f"비활성화된 신호 타입: {signal.signal_type}"}

    def _check_quality_score_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """품질 점수 필터"""
        min_score = settings.get("min_quality_score", 70)
        
        # 신호 품질 평가
        quality_result = self.backtesting_service.evaluate_signal_quality(
            signal_type=signal.signal_type,
            symbol=signal.symbol
        )
        
        if "error" in quality_result:
            # 품질 데이터가 없으면 기본 점수 사용
            score = 50.0
        else:
            score = quality_result.get("quality_assessment", {}).get("overall_score", 50.0)
        
        if score >= min_score:
            return {
                "passed": True, 
                "reason": f"품질 점수 충족: {score:.1f} >= {min_score}",
                "score": score
            }
        else:
            return {
                "passed": False, 
                "reason": f"품질 점수 부족: {score:.1f} < {min_score}",
                "score": score
            }

    def _check_success_rate_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """성공률 필터"""
        min_success_rate = settings.get("min_success_rate", 0.6)
        
        # 해당 신호 타입의 과거 성공률 조회
        success_rates = self.outcome_repository.get_success_rate_by_signal_type(
            timeframe_eval="1d", min_samples=5
        )
        
        # 해당 신호 타입의 성공률 찾기
        signal_success_rate = None
        for rate_data in success_rates:
            if rate_data["signal_type"] == signal.signal_type:
                signal_success_rate = rate_data["success_rate"]
                break
        
        if signal_success_rate is None:
            # 과거 데이터가 없으면 통과 (새로운 신호 타입)
            return {"passed": True, "reason": "과거 데이터 없음 (새로운 신호 타입)"}
        
        if signal_success_rate >= min_success_rate:
            return {
                "passed": True, 
                "reason": f"성공률 충족: {signal_success_rate:.1%} >= {min_success_rate:.1%}"
            }
        else:
            return {
                "passed": False, 
                "reason": f"성공률 부족: {signal_success_rate:.1%} < {min_success_rate:.1%}"
            }

    def _check_signal_strength_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """신호 강도 필터"""
        min_strength = settings.get("min_signal_strength", 0.5)
        
        if signal.signal_strength is None:
            # 신호 강도 정보가 없으면 통과
            return {"passed": True, "reason": "신호 강도 정보 없음"}
        
        strength = float(signal.signal_strength)
        
        if strength >= min_strength:
            return {
                "passed": True, 
                "reason": f"신호 강도 충족: {strength:.2f}% >= {min_strength:.2f}%"
            }
        else:
            return {
                "passed": False, 
                "reason": f"신호 강도 부족: {strength:.2f}% < {min_strength:.2f}%"
            }

    def _check_volume_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """거래량 필터"""
        require_volume = settings.get("require_volume_confirmation", True)
        
        if not require_volume:
            return {"passed": True, "reason": "거래량 확인 비활성화"}
        
        if signal.volume is None:
            return {"passed": False, "reason": "거래량 정보 없음"}
        
        # 간단한 거래량 확인 (실제로는 평균 거래량과 비교해야 함)
        volume = signal.volume
        
        # 기본 임계값: 10,000 이상
        min_volume = 10000
        
        if volume >= min_volume:
            return {
                "passed": True, 
                "reason": f"거래량 충족: {volume:,} >= {min_volume:,}"
            }
        else:
            return {
                "passed": False, 
                "reason": f"거래량 부족: {volume:,} < {min_volume:,}"
            }

    def _check_duplicate_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """중복 신호 필터"""
        # 최근 1시간 내 동일한 신호가 있는지 확인
        duplicate_window_minutes = 60
        
        has_duplicate = self.signal_repository.exists_recent_signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            minutes=duplicate_window_minutes
        )
        
        if has_duplicate:
            return {
                "passed": False, 
                "reason": f"최근 {duplicate_window_minutes}분 내 동일 신호 존재"
            }
        else:
            return {"passed": True, "reason": "중복 신호 없음"}

    def _check_market_condition_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """시장 상황 필터"""
        use_market_filter = settings.get("market_condition_filter", True)
        
        if not use_market_filter:
            return {"passed": True, "reason": "시장 상황 필터 비활성화"}
        
        if signal.market_condition is None:
            return {"passed": True, "reason": "시장 상황 정보 없음"}
        
        # 신호 타입과 시장 상황의 적합성 확인
        signal_type = signal.signal_type.lower()
        market_condition = signal.market_condition.lower()
        
        # 상승 신호들
        bullish_signals = ["breakout_up", "golden_cross", "oversold", "bullish", "touch_lower"]
        # 하락 신호들
        bearish_signals = ["breakout_down", "dead_cross", "overbought", "bearish", "touch_upper"]
        
        is_bullish_signal = any(keyword in signal_type for keyword in bullish_signals)
        is_bearish_signal = any(keyword in signal_type for keyword in bearish_signals)
        
        # 적합성 확인
        if is_bullish_signal and market_condition in ["bullish", "sideways"]:
            return {"passed": True, "reason": f"상승 신호가 {market_condition} 시장에 적합"}
        elif is_bearish_signal and market_condition in ["bearish", "sideways"]:
            return {"passed": True, "reason": f"하락 신호가 {market_condition} 시장에 적합"}
        elif not is_bullish_signal and not is_bearish_signal:
            return {"passed": True, "reason": "중립 신호는 모든 시장 상황에 적합"}
        else:
            return {
                "passed": False, 
                "reason": f"신호와 시장 상황 불일치: {signal.signal_type} in {signal.market_condition} market"
            }

    def _check_frequency_limit_filter(self, signal: TechnicalSignal, settings: Dict[str, Any]) -> Dict[str, Any]:
        """알림 빈도 제한 필터"""
        max_per_hour = settings.get("max_signals_per_hour", 3)
        
        # 최근 1시간 내 발송된 알림 개수 확인
        recent_signals = self.signal_repository.find_recent_signals(hours=1, symbol=signal.symbol)
        sent_alerts = [s for s in recent_signals if s.alert_sent]
        
        if len(sent_alerts) >= max_per_hour:
            return {
                "passed": False, 
                "reason": f"시간당 알림 한도 초과: {len(sent_alerts)}/{max_per_hour}"
            }
        else:
            return {
                "passed": True, 
                "reason": f"알림 빈도 적절: {len(sent_alerts)}/{max_per_hour}"
            }

    # =================================================================
    # 설정 관리
    # =================================================================

    def get_default_settings(self) -> Dict[str, Any]:
        """기본 필터링 설정 조회"""
        return self.default_settings.copy()

    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 유효성 검증"""
        errors = []
        warnings = []
        
        # 품질 점수 범위 확인
        min_quality = settings.get("min_quality_score", 70)
        if not 0 <= min_quality <= 100:
            errors.append("min_quality_score는 0~100 사이여야 합니다")
        elif min_quality < 50:
            warnings.append("품질 점수가 너무 낮습니다 (50 미만)")
        
        # 성공률 범위 확인
        min_success = settings.get("min_success_rate", 0.6)
        if not 0 <= min_success <= 1:
            errors.append("min_success_rate는 0~1 사이여야 합니다")
        elif min_success < 0.4:
            warnings.append("성공률 기준이 너무 낮습니다 (40% 미만)")
        
        # 신호 강도 확인
        min_strength = settings.get("min_signal_strength", 0.5)
        if min_strength < 0:
            errors.append("min_signal_strength는 0 이상이어야 합니다")
        elif min_strength > 5:
            warnings.append("신호 강도 기준이 너무 높습니다 (5% 초과)")
        
        # 알림 빈도 확인
        max_per_hour = settings.get("max_signals_per_hour", 3)
        if max_per_hour < 1:
            errors.append("max_signals_per_hour는 1 이상이어야 합니다")
        elif max_per_hour > 10:
            warnings.append("시간당 알림이 너무 많습니다 (10개 초과)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def get_filter_statistics(self, days: int = 7) -> Dict[str, Any]:
        """필터링 통계 조회"""
        session, signal_repo, outcome_repo = self._get_session_and_repositories()
        
        try:
            # 최근 N일간의 신호들 조회
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            all_signals = signal_repo.find_by_date_range(start_date, end_date)
            sent_signals = [s for s in all_signals if s.alert_sent]
            
            # 신호 타입별 통계
            type_stats = {}
            for signal in all_signals:
                signal_type = signal.signal_type
                if signal_type not in type_stats:
                    type_stats[signal_type] = {"total": 0, "sent": 0}
                
                type_stats[signal_type]["total"] += 1
                if signal.alert_sent:
                    type_stats[signal_type]["sent"] += 1
            
            # 필터링 비율 계산
            for signal_type in type_stats:
                stats = type_stats[signal_type]
                stats["filter_rate"] = 1 - (stats["sent"] / stats["total"]) if stats["total"] > 0 else 0
                stats["send_rate"] = stats["sent"] / stats["total"] if stats["total"] > 0 else 0
            
            return {
                "period": {
                    "days": days,
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "summary": {
                    "total_signals": len(all_signals),
                    "sent_signals": len(sent_signals),
                    "filtered_signals": len(all_signals) - len(sent_signals),
                    "overall_filter_rate": 1 - (len(sent_signals) / len(all_signals)) if all_signals else 0,
                    "overall_send_rate": len(sent_signals) / len(all_signals) if all_signals else 0
                },
                "by_signal_type": type_stats,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 필터링 통계 조회 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()