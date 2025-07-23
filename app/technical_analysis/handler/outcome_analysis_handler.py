"""
결과 분석 핸들러

라우터와 서비스 사이의 중간 계층으로, 비즈니스 로직을 처리합니다.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.technical_analysis.service.enhanced_outcome_tracking_service import (
    EnhancedOutcomeTrackingService,
)
from app.technical_analysis.service.backtesting_service import BacktestingService
from app.technical_analysis.service.portfolio_backtesting_service import (
    PortfolioBacktestingService,
)
from app.technical_analysis.service.signal_filtering_service import (
    SignalFilteringService,
)


class OutcomeAnalysisHandler:
    """결과 분석 핸들러"""

    def __init__(self):
        self.outcome_tracking_service = EnhancedOutcomeTrackingService()
        self.backtesting_service = BacktestingService()
        self.portfolio_backtesting_service = PortfolioBacktestingService()
        self.signal_filtering_service = SignalFilteringService()

    def get_tracking_summary(self) -> Dict[str, Any]:
        """
        결과 추적 현황 요약 정보를 반환합니다.

        Returns:
            추적 현황 요약 데이터
        """
        try:
            summary = self.outcome_tracking_service.get_tracking_summary()

            return {
                "total_tracked": summary.get("총_추적_개수", 0),
                "completed": summary.get("완료된_추적", 0),
                "pending": summary.get("미완료_추적", 0),
                "completion_rate": summary.get("완료율", 0.0),
            }
        except Exception as e:
            raise Exception(f"추적 요약 조회 실패: {str(e)}")

    def get_pending_outcomes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        진행 중인 결과 추적 목록을 반환합니다.

        Args:
            limit: 조회할 결과 수

        Returns:
            진행 중인 추적 결과 목록
        """
        try:
            session, outcome_repo, signal_repo = (
                self.outcome_tracking_service._get_session_and_repositories()
            )

            from sqlalchemy import text

            query = text(
                """
            SELECT 
                so.id as outcome_id,
                so.signal_id,
                s.signal_type,
                s.symbol,
                s.created_at as signal_time,
                so.price_1h_after,
                so.price_1d_after,
                so.price_1w_after,
                so.price_1m_after
            FROM signal_outcomes so
            JOIN technical_signals s ON so.signal_id = s.id
            WHERE so.is_complete = FALSE
            ORDER BY so.created_at DESC
            LIMIT :limit
            """
            )

            result = session.execute(query, {"limit": limit})
            rows = result.fetchall()

            pending_outcomes = []
            for row in rows:
                (
                    outcome_id,
                    signal_id,
                    signal_type,
                    symbol,
                    signal_time,
                    price_1h,
                    price_1d,
                    price_1w,
                    price_1m,
                ) = row

                # 경과 시간 계산
                now = datetime.now()
                if isinstance(signal_time, str):
                    signal_time = datetime.fromisoformat(
                        signal_time.replace("Z", "+00:00")
                    )
                elif signal_time.tzinfo is None:
                    signal_time = signal_time.replace(tzinfo=None)

                elapsed_hours = (now - signal_time).total_seconds() / 3600

                pending_outcomes.append(
                    {
                        "outcome_id": outcome_id,
                        "signal_id": signal_id,
                        "signal_type": signal_type,
                        "symbol": symbol,
                        "signal_time": signal_time,
                        "elapsed_hours": elapsed_hours,
                        "price_1h_completed": price_1h is not None,
                        "price_1d_completed": price_1d is not None,
                        "price_1w_completed": price_1w is not None,
                        "price_1m_completed": price_1m is not None,
                    }
                )

            session.close()
            return pending_outcomes

        except Exception as e:
            raise Exception(f"진행 중인 추적 조회 실패: {str(e)}")

    def get_performance_by_signal_type(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        신호 유형별 성과를 분석하여 반환합니다.

        Args:
            limit: 조회할 신호 유형 수

        Returns:
            신호 유형별 성과 분석 결과
        """
        try:
            session, outcome_repo, signal_repo = (
                self.outcome_tracking_service._get_session_and_repositories()
            )

            from sqlalchemy import text

            query = text(
                """
            SELECT 
                s.signal_type,
                COUNT(*) as total_signals,
                AVG(so.return_1h) as avg_return_1h,
                AVG(so.return_1d) as avg_return_1d,
                AVG(so.return_1w) as avg_return_1w,
                SUM(CASE WHEN so.return_1h > 0 THEN 1 ELSE 0 END) as positive_1h,
                SUM(CASE WHEN so.return_1d > 0 THEN 1 ELSE 0 END) as positive_1d,
                SUM(CASE WHEN so.return_1w > 0 THEN 1 ELSE 0 END) as positive_1w
            FROM signal_outcomes so
            JOIN technical_signals s ON so.signal_id = s.id
            WHERE so.is_complete = TRUE
            GROUP BY s.signal_type
            ORDER BY avg_return_1d DESC
            LIMIT :limit
            """
            )

            result = session.execute(query, {"limit": limit})
            rows = result.fetchall()

            performances = []
            for row in rows:
                signal_type, total, avg_1h, avg_1d, avg_1w, pos_1h, pos_1d, pos_1w = row

                performances.append(
                    {
                        "signal_type": signal_type,
                        "total_signals": total,
                        "avg_return_1h": float(avg_1h) if avg_1h else None,
                        "avg_return_1d": float(avg_1d) if avg_1d else None,
                        "avg_return_1w": float(avg_1w) if avg_1w else None,
                        "success_rate_1h": pos_1h / total * 100 if total > 0 else 0,
                        "success_rate_1d": pos_1d / total * 100 if total > 0 else 0,
                        "success_rate_1w": pos_1w / total * 100 if total > 0 else 0,
                    }
                )

            session.close()
            return performances

        except Exception as e:
            raise Exception(f"성과 분석 실패: {str(e)}")

    def get_top_performers(
        self, timeframe: str = "1d", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최고 성과를 낸 신호들을 반환합니다.

        Args:
            timeframe: 분석할 시간대 (1h, 1d, 1w)
            limit: 조회할 신호 수

        Returns:
            최고 성과 신호 목록
        """
        try:
            session, outcome_repo, signal_repo = (
                self.outcome_tracking_service._get_session_and_repositories()
            )

            return_column = f"return_{timeframe}"

            from sqlalchemy import text

            query = text(
                f"""
            SELECT 
                s.signal_type,
                s.symbol,
                so.{return_column} as return_value,
                s.created_at,
                s.current_price
            FROM signal_outcomes so
            JOIN technical_signals s ON so.signal_id = s.id
            WHERE so.is_complete = TRUE 
            AND so.{return_column} IS NOT NULL
            ORDER BY so.{return_column} DESC
            LIMIT :limit
            """
            )

            result = session.execute(query, {"limit": limit})
            rows = result.fetchall()

            top_performers = []
            for row in rows:
                signal_type, symbol, return_value, created_at, current_price = row

                top_performers.append(
                    {
                        "signal_type": signal_type,
                        "symbol": symbol,
                        "return_value": float(return_value),
                        "signal_time": created_at,
                        "signal_price": float(current_price) if current_price else None,
                    }
                )

            session.close()
            return top_performers

        except Exception as e:
            raise Exception(f"최고 성과 조회 실패: {str(e)}")

    def run_simple_backtesting(
        self,
        signal_types: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        간단한 백테스팅을 실행합니다.

        Args:
            signal_types: 분석할 신호 유형 목록
            start_date: 분석 시작 날짜
            end_date: 분석 종료 날짜

        Returns:
            백테스팅 결과
        """
        try:
            # 기본 날짜 설정
            if not start_date:
                start_date = datetime.now() - timedelta(days=365)
            if not end_date:
                end_date = datetime.now()

            session, outcome_repo, signal_repo = (
                self.outcome_tracking_service._get_session_and_repositories()
            )

            from sqlalchemy import text

            signal_types_str = "', '".join(signal_types)

            query = text(
                f"""
            SELECT 
                COUNT(*) as total_trades,
                AVG(so.return_1d) as avg_return,
                SUM(CASE WHEN so.return_1d > 0 THEN 1 ELSE 0 END) as winning_trades,
                MAX(so.return_1d) as max_return,
                MIN(so.return_1d) as min_return,
                STDDEV(so.return_1d) as volatility
            FROM signal_outcomes so
            JOIN technical_signals s ON so.signal_id = s.id
            WHERE s.signal_type IN ('{signal_types_str}')
            AND s.created_at BETWEEN :start_date AND :end_date
            AND so.is_complete = TRUE
            AND so.return_1d IS NOT NULL
            """
            )

            result = session.execute(
                query, {"start_date": start_date, "end_date": end_date}
            )
            row = result.fetchone()

            if not row or row[0] == 0:
                raise Exception("해당 조건의 데이터가 없습니다")

            (
                total_trades,
                avg_return,
                winning_trades,
                max_return,
                min_return,
                volatility,
            ) = row

            # 간단한 성과 지표 계산
            win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
            total_return = float(avg_return) * total_trades if avg_return else 0
            annual_return = (
                total_return * (365 / (end_date - start_date).days)
                if (end_date - start_date).days > 0
                else 0
            )
            sharpe_ratio = (
                float(avg_return) / float(volatility)
                if volatility and volatility > 0
                else 0
            )
            max_drawdown = abs(float(min_return)) if min_return else 0

            session.close()

            return {
                "strategy_name": f"Combined_{len(signal_types)}_signals",
                "total_return": total_return,
                "annual_return": annual_return,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "win_rate": win_rate,
                "total_trades": total_trades,
            }

        except Exception as e:
            raise Exception(f"백테스팅 실행 실패: {str(e)}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        실시간 모니터링 대시보드에 필요한 데이터를 반환합니다.

        Returns:
            대시보드 데이터
        """
        try:
            # 추적 요약
            summary = self.outcome_tracking_service.get_tracking_summary()

            # 최근 신호들
            session, outcome_repo, signal_repo = (
                self.outcome_tracking_service._get_session_and_repositories()
            )

            from sqlalchemy import text

            recent_signals_query = text(
                """
            SELECT 
                s.signal_type,
                s.symbol,
                s.current_price,
                s.created_at,
                so.return_1d,
                so.is_complete
            FROM technical_signals s
            LEFT JOIN signal_outcomes so ON s.id = so.signal_id
            ORDER BY s.created_at DESC
            LIMIT 5
            """
            )

            recent_result = session.execute(recent_signals_query)
            recent_signals = []

            for row in recent_result.fetchall():
                signal_type, symbol, price, created_at, return_1d, is_complete = row
                recent_signals.append(
                    {
                        "signal_type": signal_type,
                        "symbol": symbol,
                        "price": float(price) if price else None,
                        "created_at": created_at,
                        "return_1d": float(return_1d) if return_1d else None,
                        "is_complete": is_complete,
                    }
                )

            session.close()

            return {
                "summary": summary,
                "recent_signals": recent_signals,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            raise Exception(f"대시보드 데이터 조회 실패: {str(e)}")

    def manual_update_tracking(self, batch_size: int = 10) -> Dict[str, Any]:
        """
        결과 추적을 수동으로 업데이트합니다.

        Args:
            batch_size: 한 번에 처리할 결과 수

        Returns:
            업데이트 결과
        """
        try:
            result = (
                self.outcome_tracking_service.update_outcomes_with_detailed_logging(
                    hours_old=1
                )
            )

            return {
                "success": True,
                "processed_count": result.get("processed_count", 0),
                "updated_count": result.get("updated_count", 0),
                "message": "수동 업데이트 완료",
            }

        except Exception as e:
            raise Exception(f"수동 업데이트 실패: {str(e)}")
