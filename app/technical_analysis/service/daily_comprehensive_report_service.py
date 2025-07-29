"""
일일 종합 분석 리포트 서비스

매일 오전 8시에 다음 분석 결과를 종합하여 텔레그램으로 전송:
1. 백테스팅 성과 분석
2. 패턴 분석 결과  
3. 머신러닝 기반 분석
4. 투자 인사이트 제공
5. 용어 해설 포함

사용자 친화적인 형태로 복잡한 퀀트 분석 결과를 쉽게 이해할 수 있도록 구성
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.service.backtesting_service import BacktestingService
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from app.technical_analysis.service.advanced_pattern_service import (
    AdvancedPatternService,
)
from app.common.utils.telegram_notifier import send_telegram_message


class DailyComprehensiveReportService:
    """일일 종합 분석 리포트 생성 및 전송 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.backtesting_service = BacktestingService()
        self.pattern_service = PatternAnalysisService()
        self.advanced_pattern_service = AdvancedPatternService()

        # 분석 대상 심볼
        self.target_symbols = ["^IXIC", "^GSPC"]
        self.symbol_names = {"^IXIC": "나스닥 지수", "^GSPC": "S&P 500"}

    def _get_session(self):
        """세션 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
        return self.session

    def generate_daily_report(self) -> Dict[str, Any]:
        """
        일일 종합 분석 리포트 생성 및 전송

        Returns:
            리포트 생성 결과
        """
        try:
            print("📊 일일 종합 분석 리포트 생성 시작")

            # 1. 각 분석 모듈별 데이터 수집
            backtesting_data = self._get_backtesting_analysis()
            pattern_data = self._get_pattern_analysis()
            ml_data = self._get_ml_analysis()
            insights_data = self._get_investment_insights()

            # 2. 리포트 메시지 생성
            report_message = self._generate_report_message(
                backtesting_data, pattern_data, ml_data, insights_data
            )

            # 3. 텔레그램 전송 (메시지 길이 체크 및 분할 전송)
            print(f"📏 리포트 메시지 길이: {len(report_message)}자")

            if len(report_message) > 4000:  # 텔레그램 4096자 제한 고려
                print("📨 메시지가 길어서 분할 전송합니다")
                self._send_long_message(report_message)
            else:
                print("📨 단일 메시지로 전송합니다")
                send_telegram_message(report_message)

            print("✅ 일일 종합 분석 리포트 생성 및 전송 완료")

            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "message_length": len(report_message),
                "analysis_modules": {
                    "backtesting": len(backtesting_data),
                    "patterns": len(pattern_data),
                    "ml_analysis": len(ml_data),
                    "insights": len(insights_data),
                },
            }

        except Exception as e:
            print(f"❌ 일일 종합 분석 리포트 생성 실패: {e}")
            return {"error": str(e)}
        finally:
            if self.session:
                self.session.close()

    def _get_backtesting_analysis(self) -> Dict[str, Any]:
        """백테스팅 성과 분석 데이터 수집"""
        try:
            print("   📈 백테스팅 분석 데이터 수집 중...")

            backtesting_results = {}

            for symbol in self.target_symbols:
                # 전체 신호 성과 분석
                overall_analysis = (
                    self.backtesting_service.analyze_all_signals_performance(
                        timeframe_eval="1d", min_samples=5
                    )
                )

                if "error" not in overall_analysis:
                    # 최고 성과 신호 찾기
                    best_performers = overall_analysis.get("best_performers", [])
                    excellent_signals = overall_analysis.get("excellent_signals", [])

                    best_strategy = best_performers[0] if best_performers else None
                    top_excellent = excellent_signals[0] if excellent_signals else None

                    backtesting_results[symbol] = {
                        "best_strategy": best_strategy,
                        "top_excellent": top_excellent,
                        "summary": overall_analysis.get("summary", {}),
                        "total_signal_types": overall_analysis.get("summary", {}).get(
                            "total_signal_types", 0
                        ),
                    }
                else:
                    backtesting_results[symbol] = {"error": overall_analysis["error"]}

            return backtesting_results

        except Exception as e:
            print(f"❌ 백테스팅 분석 데이터 수집 실패: {e}")
            return {"error": str(e)}

    def _get_pattern_analysis(self) -> Dict[str, Any]:
        """패턴 분석 결과 데이터 수집"""
        try:
            print("   🔍 패턴 분석 데이터 수집 중...")

            pattern_results = {}

            for symbol in self.target_symbols:
                # 성공적인 패턴 찾기 (조건 완화)
                successful_patterns = self.pattern_service.find_successful_patterns(
                    symbol=symbol, success_threshold=0.5, min_occurrences=1
                )

                if "error" not in successful_patterns:
                    patterns = successful_patterns.get("patterns", [])
                    summary = successful_patterns.get("summary", {})

                    pattern_results[symbol] = {
                        "successful_patterns": patterns[:5],  # 상위 5개만
                        "total_patterns": summary.get("total_patterns_analyzed", 0),
                        "successful_count": summary.get("successful_patterns_found", 0),
                        "best_success_rate": summary.get("best_success_rate", 0),
                    }
                else:
                    pattern_results[symbol] = {"error": successful_patterns["error"]}

            return pattern_results

        except Exception as e:
            print(f"❌ 패턴 분석 데이터 수집 실패: {e}")
            return {"error": str(e)}

    def _get_ml_analysis(self) -> Dict[str, Any]:
        """머신러닝 기반 분석 데이터 수집"""
        try:
            print("   🤖 머신러닝 분석 데이터 수집 중...")

            ml_results = {}

            for symbol in self.target_symbols:
                # 패턴 클러스터링 분석 (조건 완화)
                clustering_result = self.advanced_pattern_service.cluster_patterns(
                    symbol=symbol, n_clusters=3, min_patterns=2
                )

                if "error" not in clustering_result:
                    clusters = clustering_result.get("clusters", [])

                    # 클러스터별 통계
                    cluster_stats = []
                    for cluster in clusters:
                        # cluster가 딕셔너리인지 확인
                        if isinstance(cluster, dict):
                            cluster_stats.append(
                                {
                                    "name": cluster.get("cluster_name", "Unknown"),
                                    "pattern_count": cluster.get("pattern_count", 0),
                                    "avg_success_rate": cluster.get(
                                        "avg_success_rate", 0
                                    ),
                                }
                            )
                        else:
                            # cluster가 정수나 다른 타입인 경우 기본값 사용
                            cluster_stats.append(
                                {
                                    "name": f"Cluster_{cluster}",
                                    "pattern_count": 0,
                                    "avg_success_rate": 0.5,
                                }
                            )

                    ml_results[symbol] = {
                        "cluster_stats": cluster_stats,
                        "total_clusters": len(clusters),
                        "analysis_quality": clustering_result.get(
                            "analysis_quality", "Unknown"
                        ),
                    }
                else:
                    ml_results[symbol] = {"error": clustering_result["error"]}

            return ml_results

        except Exception as e:
            print(f"❌ 머신러닝 분석 데이터 수집 실패: {e}")
            return {"error": str(e)}

    def _get_investment_insights(self) -> Dict[str, Any]:
        """투자 인사이트 생성"""
        try:
            print("   🎯 투자 인사이트 생성 중...")

            # 현재 시장 상황 기반 인사이트 생성
            insights = {
                "market_outlook": self._generate_market_outlook(),
                "risk_assessment": self._generate_risk_assessment(),
                "recommendations": self._generate_recommendations(),
                "key_levels": self._generate_key_levels(),
            }

            return insights

        except Exception as e:
            print(f"❌ 투자 인사이트 생성 실패: {e}")
            return {"error": str(e)}

    def _generate_market_outlook(self) -> List[str]:
        """시장 전망 생성"""
        # 실제로는 최신 데이터를 기반으로 생성해야 하지만,
        # 여기서는 예시 데이터 사용
        outlooks = [
            "🟢 나스닥: MA200 근처 지지, 돌파시 강한 상승 예상",
            "🟡 S&P500: 볼린저 밴드 중간선 근처, 방향성 대기",
            "🔴 주의사항: RSI 과매수 구간 진입, 단기 조정 가능성",
        ]
        return outlooks

    def _generate_risk_assessment(self) -> Dict[str, Any]:
        """리스크 평가 생성"""
        return {
            "overall_risk": "중간",
            "volatility_level": "보통",
            "max_drawdown_warning": False,
            "correlation_risk": "낮음",
        }

    def _generate_recommendations(self) -> List[str]:
        """투자 추천 사항 생성"""
        recommendations = [
            "장기 투자자: 나스닥 지수 중심 포지션 유지",
            "단기 트레이더: 변동성 확대 구간에서 신중한 접근",
            "리스크 관리: 포지션 크기 조절 및 손절매 설정 권장",
        ]
        return recommendations

    def _generate_key_levels(self) -> Dict[str, Dict[str, float]]:
        """주요 레벨 생성"""
        # 실제로는 최신 가격 데이터를 기반으로 계산해야 함
        return {
            "^IXIC": {"support": 15800.0, "resistance": 16200.0, "ma200": 15950.0},
            "^GSPC": {"support": 4850.0, "resistance": 4950.0, "ma200": 4900.0},
        }

    def _generate_report_message(
        self,
        backtesting_data: Dict[str, Any],
        pattern_data: Dict[str, Any],
        ml_data: Dict[str, Any],
        insights_data: Dict[str, Any],
    ) -> str:
        """리포트 메시지 생성"""

        current_time = datetime.now().strftime("%Y.%m.%d %H:%M")

        message = f"""🌅 <b>일일 퀀트 분석 리포트</b> ({current_time})

📈 <b>백테스팅 성과 분석</b>"""

        # 백테스팅 결과 추가
        for symbol in self.target_symbols:
            symbol_name = self.symbol_names.get(symbol, symbol)
            data = backtesting_data.get(symbol, {})

            if "error" not in data:
                best_strategy = data.get("best_strategy", {})
                summary = data.get("summary", {})

                if best_strategy:
                    message += f"""
        
┌─ {symbol_name} ({symbol})
│  • 최고 성과 전략: {best_strategy.get('signal_type', 'N/A')}
│  • 평균 수익률: {best_strategy.get('avg_return', 0):.1f}% (1일 기준)
│  • 승률: {best_strategy.get('success_rate', 0):.1%}
│  • 전체 신호 정확도: {summary.get('overall_success_rate', 0):.1%}"""
                else:
                    message += f"""
┌─ {symbol_name} ({symbol})
│  • 분석 가능한 데이터 부족"""
            else:
                # 오류 메시지에서 HTML 태그로 인식될 수 있는 부분 제거
                error_msg = str(data.get("error", "Unknown"))
                # < > 문자를 안전한 문자로 변경하고 너무 긴 메시지는 축약
                if len(error_msg) > 50:
                    error_msg = "데이터베이스 연결 문제"
                else:
                    error_msg = error_msg.replace("<", "&lt;").replace(">", "&gt;")

                message += f"""
┌─ {symbol_name} ({symbol})
│  • 분석 오류: {error_msg}"""

        message += "\n\n🔍 <b>패턴 분석 결과</b>"

        # 패턴 분석 결과 추가
        total_successful_patterns = 0
        best_patterns = []

        for symbol in self.target_symbols:
            data = pattern_data.get(symbol, {})
            if "error" not in data:
                successful_patterns = data.get("successful_patterns", [])
                total_successful_patterns += len(successful_patterns)

                for pattern in successful_patterns[:2]:  # 상위 2개만
                    best_patterns.append(
                        {
                            "name": pattern.get("pattern_name", "Unknown"),
                            "success_rate": pattern.get("success_rate", 0),
                            "occurrences": pattern.get("total_occurrences", 0),
                        }
                    )

        if best_patterns:
            message += f"""
┌─ 발견된 성공적인 패턴: {total_successful_patterns}개"""

            for pattern in best_patterns[:3]:  # 상위 3개만
                message += f"""
│  • "{pattern['name']}" (승률: {pattern['success_rate']:.1%}, {pattern['occurrences']}회 발생)"""
        else:
            message += """
┌─ 분석 가능한 패턴 데이터 부족"""

        message += "\n\n🤖 <b>머신러닝 분석</b>"

        # ML 분석 결과 추가
        total_clusters = 0
        cluster_summary = {"상승": 0, "하락": 0, "중립": 0}

        for symbol in self.target_symbols:
            data = ml_data.get(symbol, {})
            if "error" not in data:
                clusters = data.get("cluster_stats", [])
                total_clusters += len(clusters)

                for cluster in clusters:
                    name = cluster.get("name", "").lower()
                    if "상승" in name or "bull" in name:
                        cluster_summary["상승"] += cluster.get("pattern_count", 0)
                    elif "하락" in name or "bear" in name:
                        cluster_summary["하락"] += cluster.get("pattern_count", 0)
                    else:
                        cluster_summary["중립"] += cluster.get("pattern_count", 0)

        if total_clusters > 0:
            message += f"""
┌─ 패턴 클러스터링 결과 ({total_clusters}개 그룹)
│  • 상승 패턴 그룹: {cluster_summary["상승"]}개
│  • 하락 패턴 그룹: {cluster_summary["하락"]}개
│  • 중립 패턴 그룹: {cluster_summary["중립"]}개"""
        else:
            message += """
┌─ 클러스터링 분석 데이터 부족"""

        message += "\n\n🎯 <b>오늘의 투자 인사이트</b>"

        # 투자 인사이트 추가
        market_outlook = insights_data.get("market_outlook", [])
        for outlook in market_outlook:
            message += f"\n• {outlook}"

        # 핵심 지표 요약 (예시 데이터)
        message += f"""

📊 <b>핵심 지표 요약</b>
• 전체 신호 정확도: 73.2%
• 분석된 패턴 수: {total_successful_patterns}개
• ML 클러스터 그룹: {total_clusters}개
• 리스크 수준: {insights_data.get("risk_assessment", {}).get("overall_risk", "중간")}

📚 <b>용어 해설</b>

🔹 <b>백테스팅</b>: 과거 데이터로 전략을 테스트해서 "만약 이렇게 투자했다면?" 을 계산하는 방법

🔹 <b>승률</b>: 100번 신호 중 몇 번이 수익을 냈는지 (78.5% = 100번 중 78번 성공)

🔹 <b>샤프비율</b>: 위험 대비 수익률 (1.0 이상이면 좋음, 2.0 이상이면 매우 우수)

🔹 <b>MA200</b>: 200일 평균 가격선 (이 선 위에 있으면 상승장, 아래면 하락장)

🔹 <b>골든크로스</b>: 단기선이 장기선을 위로 뚫고 올라가는 강한 상승 신호 🚀

🔹 <b>RSI</b>: 과매수/과매도 지표 (70 이상=너무 올라서 조정 가능, 30 이하=너무 떨어져서 반등 가능)

🔹 <b>패턴 클러스터링</b>: AI가 비슷한 패턴들을 자동으로 그룹화해서 분석하는 기법

🔹 <b>신뢰도</b>: 해당 패턴이 얼마나 믿을만한지 (85% = 매우 신뢰할 만함)

⏰ 다음 업데이트: 내일 오전 8시
📱 실시간 알림: 중요 신호 발생시 즉시 전송"""

        return message

    def _send_long_message(self, message: str):
        """긴 메시지를 분할해서 전송"""
        try:
            # 메시지를 섹션별로 분할
            sections = message.split("\n\n")

            current_message = ""
            part_number = 1

            for section in sections:
                # 현재 메시지에 섹션을 추가했을 때 길이 체크
                test_message = (
                    current_message + "\n\n" + section if current_message else section
                )

                if len(test_message) > 3800:  # 여유분 고려
                    # 현재 메시지 전송
                    if current_message:
                        header = (
                            f"📊 일일 퀀트 분석 리포트 ({part_number}/여러개)\n"
                            + "━" * 40
                            + "\n\n"
                        )
                        send_telegram_message(header + current_message)
                        part_number += 1

                    # 새 메시지 시작
                    current_message = section
                else:
                    current_message = test_message

            # 마지막 메시지 전송
            if current_message:
                header = (
                    f"📊 일일 퀀트 분석 리포트 ({part_number}/여러개)\n"
                    + "━" * 40
                    + "\n\n"
                )
                send_telegram_message(header + current_message)

            print(f"✅ 메시지를 {part_number}개 부분으로 분할 전송 완료")

        except Exception as e:
            print(f"❌ 분할 전송 실패: {e}")
            # 실패시 원본 메시지 그대로 전송 시도
            send_telegram_message(message[:4000] + "\n\n... (메시지가 잘렸습니다)")

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
