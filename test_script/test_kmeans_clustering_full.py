#!/usr/bin/env python3
"""
K-means 클러스터링 테스트 스크립트

목적: 기존 일봉 데이터를 활용하여 K-means 클러스터링까지 전체 파이프라인 테스트

프로세스:
1. 데이터 현황 확인 (일봉 데이터 상태 체크)
2. 기술적 신호 생성 (RSI, MA, MACD 등의 신호 계산 및 저장)
3. 패턴 발견 (신호들의 조합 패턴 찾기 및 저장)
4. K-means 클러스터링 실행 (패턴들을 그룹화)
5. 결과 확인 (생성된 데이터 검증)

실행 방법:
    python clustering_test.py

주의사항:
- MySQL 서버가 실행 중이어야 함
- 환경변수(.env.dev)가 올바르게 설정되어야 함
- 처리 시간이 오래 걸릴 수 있음 (10년치 데이터 처리)
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경 설정
mode = os.getenv("ENV_MODE", "dev")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 60)
    print(f"🔄 {title}")
    print("=" * 60)


def print_step(step_num: int, title: str):
    """단계별 제목 출력"""
    print(f"\n📋 {step_num}단계: {title}")
    print("-" * 40)


def step1_check_data_status():
    """
    1단계: 데이터 현황 확인
    - 일봉 데이터 존재 여부 및 개수 확인
    - 기술적 신호 데이터 현황 확인
    - 패턴 데이터 현황 확인
    """
    print_step(1, "데이터 현황 확인")

    try:
        from app.common.infra.database.config.database_config import SessionLocal
        from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
        from app.technical_analysis.infra.model.entity.technical_signals import (
            TechnicalSignal,
        )
        from app.technical_analysis.infra.model.entity.signal_patterns import (
            SignalPattern,
        )
        from sqlalchemy import func

        session = SessionLocal()

        # 1-1. 일봉 데이터 확인
        print("📊 일봉 데이터 현황:")
        nasdaq_count = (
            session.query(DailyPrice).filter(DailyPrice.symbol == "^IXIC").count()
        )
        sp500_count = (
            session.query(DailyPrice).filter(DailyPrice.symbol == "^GSPC").count()
        )

        print(f"  - 나스닥(^IXIC): {nasdaq_count:,}개")
        print(f"  - S&P500(^GSPC): {sp500_count:,}개")

        if nasdaq_count > 0 and sp500_count > 0:
            # 데이터 기간 확인
            earliest = (
                session.query(func.min(DailyPrice.date))
                .filter(DailyPrice.symbol.in_(["^IXIC", "^GSPC"]))
                .scalar()
            )
            latest = (
                session.query(func.max(DailyPrice.date))
                .filter(DailyPrice.symbol.in_(["^IXIC", "^GSPC"]))
                .scalar()
            )
            print(f"  - 데이터 기간: {earliest} ~ {latest}")
            print("  ✅ 일봉 데이터 충분함")
        else:
            print("  ❌ 일봉 데이터 부족")
            return False

        # 1-2. 기술적 신호 데이터 확인
        print("\n🔍 기술적 신호 현황:")
        signal_count = session.query(TechnicalSignal).count()
        nasdaq_signals = (
            session.query(TechnicalSignal)
            .filter(TechnicalSignal.symbol == "^IXIC")
            .count()
        )
        sp500_signals = (
            session.query(TechnicalSignal)
            .filter(TechnicalSignal.symbol == "^GSPC")
            .count()
        )

        print(f"  - 전체 신호: {signal_count:,}개")
        print(f"  - 나스닥 신호: {nasdaq_signals:,}개")
        print(f"  - S&P500 신호: {sp500_signals:,}개")

        if signal_count > 0:
            # 신호 타입별 분포
            signal_types = (
                session.query(
                    TechnicalSignal.signal_type, func.count(TechnicalSignal.id)
                )
                .group_by(TechnicalSignal.signal_type)
                .all()
            )

            print("  - 신호 타입별 분포:")
            for signal_type, count in signal_types[:5]:  # 상위 5개만
                print(f"    * {signal_type}: {count}개")
            print("  ✅ 기술적 신호 데이터 존재")
        else:
            print("  ❌ 기술적 신호 데이터 없음 (생성 필요)")

        # 1-3. 패턴 데이터 확인
        print("\n🧩 패턴 데이터 현황:")
        pattern_count = session.query(SignalPattern).count()
        nasdaq_patterns = (
            session.query(SignalPattern).filter(SignalPattern.symbol == "^IXIC").count()
        )
        sp500_patterns = (
            session.query(SignalPattern).filter(SignalPattern.symbol == "^GSPC").count()
        )

        print(f"  - 전체 패턴: {pattern_count:,}개")
        print(f"  - 나스닥 패턴: {nasdaq_patterns:,}개")
        print(f"  - S&P500 패턴: {sp500_patterns:,}개")

        if pattern_count > 0:
            print("  ✅ 패턴 데이터 존재")
        else:
            print("  ❌ 패턴 데이터 없음 (생성 필요)")

        session.close()

        return {
            "daily_data": nasdaq_count > 0 and sp500_count > 0,
            "signals": signal_count > 0,
            "patterns": pattern_count > 0,
            "signal_count": signal_count,
            "pattern_count": pattern_count,
        }

    except Exception as e:
        print(f"❌ 데이터 현황 확인 실패: {e}")
        return False


def step2_generate_signals():
    """
    2단계: 기술적 신호 생성
    - 일봉 데이터로부터 RSI, MA, MACD, 볼린저밴드 등의 신호 계산
    - 계산된 신호들을 technical_signals 테이블에 저장
    """
    print_step(2, "기술적 신호 생성")

    try:
        from app.technical_analysis.service.signal_generator_service import (
            SignalGeneratorService,
        )

        print("🔄 신호 생성 서비스 초기화...")
        service = SignalGeneratorService()

        # 전체 기간에 대해 신호 생성 (10년치)
        end_date = datetime.now().date()
        start_date = datetime(2015, 1, 1).date()  # 2015년부터

        print(f"📅 신호 생성 기간: {start_date} ~ {end_date}")
        print("⏳ 신호 생성 중... (시간이 오래 걸릴 수 있습니다)")

        result = service.generate_all_signals(
            symbols=["^IXIC", "^GSPC"], start_date=start_date, end_date=end_date
        )

        if "error" in result:
            print(f"❌ 신호 생성 실패: {result['error']}")
            return False
        else:
            print("✅ 신호 생성 완료!")
            summary = result.get("summary", {})
            print(f"  - 총 신호: {summary.get('total_signals', 0):,}개")
            print(f"  - 저장된 신호: {summary.get('total_saved', 0):,}개")

            # 심볼별 상세 정보
            for symbol, data in result.get("results", {}).items():
                print(f"\n  📈 {symbol}:")
                print(f"    - 저장된 신호: {data.get('saved_signals', 0):,}개")

                breakdown = data.get("signal_breakdown", {})
                if breakdown:
                    print("    - 신호 타입별:")
                    for signal_type, count in breakdown.items():
                        print(f"      * {signal_type}: {count}개")

            return True

    except Exception as e:
        print(f"❌ 신호 생성 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def step3_discover_patterns():
    """
    3단계: 패턴 발견
    - 생성된 기술적 신호들로부터 조합 패턴 발견
    - 발견된 패턴들을 signal_patterns 테이블에 저장
    """
    print_step(3, "패턴 발견")

    try:
        from app.technical_analysis.service.pattern_analysis_service import (
            PatternAnalysisService,
        )

        print("🔄 패턴 분석 서비스 초기화...")
        service = PatternAnalysisService()

        total_patterns = 0

        # 각 심볼별로 패턴 발견
        for symbol in ["^IXIC", "^GSPC"]:
            print(f"\n📊 {symbol} 패턴 분석 중...")

            result = service.discover_patterns(symbol=symbol, timeframe="1day")

            if "error" in result:
                print(f"  ❌ {symbol} 패턴 발견 실패: {result['error']}")
            else:
                pattern_count = result.get("total_patterns", 0)
                saved_count = result.get("saved_patterns", 0)
                total_patterns += saved_count

                print(f"  ✅ {symbol} 패턴 발견 완료:")
                print(f"    - 발견된 패턴: {pattern_count}개")
                print(f"    - 저장된 패턴: {saved_count}개")

                # 패턴 예시 출력
                patterns = result.get("patterns", [])
                if patterns:
                    print("    - 패턴 예시:")
                    for i, pattern in enumerate(patterns[:3]):  # 상위 3개만
                        pattern_name = pattern.get("name", "Unknown")
                        occurrences = pattern.get("occurrences", 0)
                        print(f"      {i+1}. {pattern_name} ({occurrences}회 발생)")

        print(f"\n✅ 전체 패턴 발견 완료: 총 {total_patterns}개 패턴 저장")
        return total_patterns > 0

    except Exception as e:
        print(f"❌ 패턴 발견 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def step4_run_clustering():
    """
    4단계: K-means 클러스터링 실행 및 저장
    - 발견된 패턴들을 K-means 알고리즘으로 클러스터링
    - 유사한 패턴들을 그룹화하여 분석
    - 클러스터링 결과를 DB에 저장
    """
    print_step(4, "K-means 클러스터링 실행 및 저장")

    try:
        from app.technical_analysis.service.advanced_pattern_service import (
            AdvancedPatternService,
        )
        from app.technical_analysis.infra.model.entity.pattern_clusters import (
            PatternCluster,
        )
        from app.technical_analysis.infra.model.repository.pattern_cluster_repository import (
            PatternClusterRepository,
        )
        from app.common.infra.database.config.database_config import SessionLocal
        import json

        print("🔄 고급 패턴 분석 서비스 초기화...")
        service = AdvancedPatternService()

        # DB 세션 생성
        session = SessionLocal()
        cluster_repo = PatternClusterRepository(session)

        total_saved_clusters = 0

        # 각 심볼별로 클러스터링 실행
        for symbol in ["^IXIC", "^GSPC"]:
            print(f"\n🧠 {symbol} 클러스터링 중...")

            result = service.cluster_patterns(
                symbol=symbol,
                n_clusters=6,  # 6개 그룹으로 분류
                min_patterns=5,  # 최소 5개 패턴 필요
            )

            if "error" in result:
                print(f"  ❌ {symbol} 클러스터링 실패: {result['error']}")
                continue

            total_patterns = result.get("total_patterns", 0)
            clustered_patterns = result.get("clustered_patterns", 0)
            n_clusters = result.get("n_clusters", 0)

            print(f"  ✅ {symbol} 클러스터링 완료:")
            print(f"    - 전체 패턴: {total_patterns}개")
            print(f"    - 클러스터링된 패턴: {clustered_patterns}개")
            print(f"    - 생성된 클러스터: {n_clusters}개")

            # 클러스터링 결과를 DB에 저장
            print(f"  💾 {symbol} 클러스터링 결과 저장 중...")
            clusters_to_save = []

            # 클러스터별 정보 출력 및 저장 준비
            clusters = result.get("clusters", [])
            if clusters:
                print("    - 클러스터 정보:")
                for i, cluster_data in enumerate(clusters):
                    # 클러스터 데이터가 딕셔너리인지 확인
                    if isinstance(cluster_data, dict):
                        cluster_id = cluster_data.get("cluster_id", i)
                        cluster_name = cluster_data.get("cluster_name", f"클러스터_{i}")
                        pattern_count = cluster_data.get("pattern_count", 0)
                        avg_success_rate = cluster_data.get("avg_success_rate", 0)
                        characteristics = cluster_data.get("characteristics", {})
                        patterns = cluster_data.get("patterns", [])
                    else:
                        # 클러스터 데이터가 예상과 다른 형태인 경우 기본값 사용
                        print(
                            f"      ⚠️ 클러스터 {i} 데이터 형태 이상: {type(cluster_data)}"
                        )
                        cluster_id = i
                        cluster_name = f"클러스터_{i}"
                        pattern_count = 0
                        avg_success_rate = 0.5
                        characteristics = {}
                        patterns = []

                    print(
                        f"      * {cluster_name}: {pattern_count}개 패턴 (성공률: {avg_success_rate:.1%})"
                    )

                    # PatternCluster 엔티티 생성
                    cluster_entity = PatternCluster(
                        symbol=symbol,
                        cluster_id=cluster_id,
                        cluster_name=cluster_name,
                        timeframe="1day",
                        pattern_count=pattern_count,
                        avg_success_rate=avg_success_rate * 100,  # 0.68 -> 68.0
                        avg_confidence_score=characteristics.get("avg_confidence", 0),
                        avg_duration_hours=characteristics.get("avg_duration", 0),
                        bullish_tendency=characteristics.get("bullish_tendency", 0),
                        bearish_tendency=characteristics.get("bearish_tendency", 0),
                        dominant_signal_types=json.dumps(
                            characteristics.get("dominant_signals", [])
                        ),
                        clustering_algorithm="kmeans",
                        n_clusters_total=n_clusters,
                        clustering_quality_score=result.get("analysis_quality", 0),
                        representative_patterns=json.dumps(
                            [p.get("id") for p in patterns[:5]]
                        ),
                        pattern_examples=json.dumps(
                            {
                                "main_patterns": [
                                    p.get("name", "Unknown") for p in patterns[:3]
                                ],
                                "cluster_description": f"{cluster_name} - {pattern_count}개 패턴",
                            }
                        ),
                        clustered_at=datetime.now(),
                    )

                    clusters_to_save.append(cluster_entity)

                    # 대표 패턴들 출력
                    if patterns:
                        print("        - 대표 패턴:")
                        for pattern in patterns[:2]:  # 상위 2개만
                            pattern_name = pattern.get("name", "Unknown")
                            print(f"          · {pattern_name}")

            # 배치로 저장
            if clusters_to_save:
                try:
                    saved_clusters = cluster_repo.save_all(clusters_to_save)
                    total_saved_clusters += len(saved_clusters)
                    print(
                        f"    ✅ {symbol}: {len(saved_clusters)}개 클러스터 저장 완료"
                    )
                except Exception as e:
                    print(f"    ❌ {symbol} 클러스터 저장 실패: {e}")

        session.close()

        print(f"\n✅ K-means 클러스터링 및 저장 완료!")
        print(f"  📊 총 저장된 클러스터: {total_saved_clusters}개")
        return total_saved_clusters > 0

    except Exception as e:
        print(f"❌ 클러스터링 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def step5_verify_results():
    """
    5단계: 결과 확인
    - 생성된 모든 데이터의 최종 상태 확인
    - 일일 리포트에서 사용할 수 있는 상태인지 검증
    """
    print_step(5, "결과 확인 및 검증")

    try:
        from app.common.infra.database.config.database_config import SessionLocal
        from app.technical_analysis.infra.model.entity.technical_signals import (
            TechnicalSignal,
        )
        from app.technical_analysis.infra.model.entity.signal_patterns import (
            SignalPattern,
        )
        from sqlalchemy import func

        session = SessionLocal()

        # 5-1. 기술적 신호 최종 확인
        print("🔍 기술적 신호 최종 상태:")
        total_signals = session.query(TechnicalSignal).count()
        nasdaq_signals = (
            session.query(TechnicalSignal)
            .filter(TechnicalSignal.symbol == "^IXIC")
            .count()
        )
        sp500_signals = (
            session.query(TechnicalSignal)
            .filter(TechnicalSignal.symbol == "^GSPC")
            .count()
        )

        print(f"  - 전체 신호: {total_signals:,}개")
        print(f"  - 나스닥 신호: {nasdaq_signals:,}개")
        print(f"  - S&P500 신호: {sp500_signals:,}개")

        # 5-2. 패턴 최종 확인
        print("\n🧩 패턴 최종 상태:")
        total_patterns = session.query(SignalPattern).count()
        nasdaq_patterns = (
            session.query(SignalPattern).filter(SignalPattern.symbol == "^IXIC").count()
        )
        sp500_patterns = (
            session.query(SignalPattern).filter(SignalPattern.symbol == "^GSPC").count()
        )

        print(f"  - 전체 패턴: {total_patterns:,}개")
        print(f"  - 나스닥 패턴: {nasdaq_patterns:,}개")
        print(f"  - S&P500 패턴: {sp500_patterns:,}개")

        # 5-3. 클러스터링 결과 확인
        print("\n🧠 클러스터링 결과 상태:")
        from app.technical_analysis.infra.model.entity.pattern_clusters import (
            PatternCluster,
        )

        total_clusters = session.query(PatternCluster).count()
        nasdaq_clusters = (
            session.query(PatternCluster)
            .filter(PatternCluster.symbol == "^IXIC")
            .count()
        )
        sp500_clusters = (
            session.query(PatternCluster)
            .filter(PatternCluster.symbol == "^GSPC")
            .count()
        )

        print(f"  - 전체 클러스터: {total_clusters:,}개")
        print(f"  - 나스닥 클러스터: {nasdaq_clusters:,}개")
        print(f"  - S&P500 클러스터: {sp500_clusters:,}개")

        clustering_ready = total_patterns >= 10 and total_clusters > 0

        if clustering_ready:
            print("  ✅ 클러스터링 실행 완료")
            print("  ✅ 일일 리포트에서 실제 ML 결과 사용 가능")

            # 클러스터링 품질 확인
            if total_clusters > 0:
                avg_quality = session.query(
                    func.avg(PatternCluster.clustering_quality_score)
                ).scalar()
                if avg_quality:
                    print(f"  📊 평균 클러스터링 품질: {avg_quality:.1f}/100")
        else:
            if total_patterns < 10:
                print("  ❌ 패턴 수 부족 (최소 10개 필요)")
            if total_clusters == 0:
                print("  ❌ 클러스터링 결과 없음")

        # 5-4. 일일 리포트 테스트
        print("\n📊 일일 리포트 ML 분석 테스트:")
        try:
            from app.technical_analysis.service.daily_comprehensive_report_service import (
                DailyComprehensiveReportService,
            )

            report_service = DailyComprehensiveReportService()
            ml_result = report_service._get_ml_analysis()

            if "error" not in ml_result:
                print("  ✅ ML 분석 모듈 정상 작동")
                print(f"    - 클러스터 그룹: {ml_result.get('cluster_groups', 0)}개")
                print(f"    - 상승 패턴: {ml_result.get('bullish_patterns', 0)}개")
                print(f"    - 하락 패턴: {ml_result.get('bearish_patterns', 0)}개")
                print(f"    - 중립 패턴: {ml_result.get('neutral_patterns', 0)}개")
            else:
                print(f"  ❌ ML 분석 모듈 오류: {ml_result.get('error', 'Unknown')}")

        except Exception as e:
            print(f"  ❌ 일일 리포트 테스트 실패: {e}")

        session.close()

        return {
            "signals": total_signals,
            "patterns": total_patterns,
            "clusters": total_clusters,
            "clustering_ready": clustering_ready,
        }

    except Exception as e:
        print(f"❌ 결과 확인 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    print_header("K-means 클러스터링 테스트 시작")

    start_time = datetime.now()
    print(f"🕐 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1단계: 데이터 현황 확인
        data_status = step1_check_data_status()
        if not data_status:
            print("\n❌ 데이터 현황 확인 실패로 중단")
            return

        # 2단계: 기술적 신호 생성 (필요한 경우에만)
        if not data_status.get("signals", False):
            print("\n🔄 기술적 신호가 없어서 생성을 시작합니다...")
            if not step2_generate_signals():
                print("\n❌ 신호 생성 실패로 중단")
                return
        else:
            print(
                f"\n✅ 기술적 신호가 이미 존재합니다 ({data_status.get('signal_count', 0)}개)"
            )

        # 3단계: 패턴 발견 (필요한 경우에만)
        if not data_status.get("patterns", False):
            print("\n🔄 패턴이 없어서 발견을 시작합니다...")
            if not step3_discover_patterns():
                print("\n❌ 패턴 발견 실패로 중단")
                return
        else:
            print(
                f"\n✅ 패턴이 이미 존재합니다 ({data_status.get('pattern_count', 0)}개)"
            )

        # 4단계: K-means 클러스터링 실행
        if not step4_run_clustering():
            print("\n❌ 클러스터링 실패")
            return

        # 5단계: 결과 확인
        final_results = step5_verify_results()

        # 최종 결과 출력
        end_time = datetime.now()
        duration = end_time - start_time

        print_header("테스트 완료")
        print(f"🕐 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 총 소요 시간: {duration}")

        if final_results:
            print(f"\n📊 최종 결과:")
            print(f"  - 기술적 신호: {final_results.get('signals', 0):,}개")
            print(f"  - 패턴: {final_results.get('patterns', 0):,}개")
            print(f"  - 클러스터: {final_results.get('clusters', 0):,}개")
            print(
                f"  - 클러스터링 준비: {'✅ 완료' if final_results.get('clustering_ready', False) else '❌ 미완료'}"
            )

            if final_results.get("clustering_ready", False):
                print(
                    f"\n🎉 성공! 이제 일일 리포트에서 실제 K-means 결과를 볼 수 있습니다!"
                )
                print(f"📱 텔레그램 리포트에서 실제 머신러닝 분석 결과가 표시됩니다.")
            else:
                print(f"\n⚠️ 클러스터링 준비가 완료되지 않았습니다.")

    except KeyboardInterrupt:
        print(f"\n\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
