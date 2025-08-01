#!/usr/bin/env python3
"""
과거 신호 패턴 분석 스크립트

이 스크립트는 기존에 저장된 모든 기술적 신호들을 분석하여
패턴을 발견하고 signal_patterns 테이블에 저장합니다.

실행 방법:
    python scripts/historical_pattern_analysis.py

주요 기능:
1. 과거 모든 신호 데이터 조회
2. 순차적/동시 패턴 발견
3. 패턴 성과 분석
4. signal_patterns 테이블에 저장
5. 머신러닝 클러스터링을 위한 데이터 준비
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from sqlalchemy import text

# 엔티티 임포트 (순환 참조 해결을 위해 패키지에서 임포트)
from app.technical_analysis.infra.model.entity import TechnicalSignal, SignalPattern


class HistoricalPatternAnalyzer:
    """과거 신호 패턴 분석기"""

    def __init__(self):
        self.session = SessionLocal()
        self.pattern_service = PatternAnalysisService()

    def __del__(self):
        """소멸자에서 세션 정리"""
        if hasattr(self, "session") and self.session:
            self.session.close()

    def analyze_all_historical_patterns(self) -> Dict[str, Any]:
        """모든 과거 신호의 패턴 분석"""
        print("🚀 과거 신호 패턴 분석 시작")
        print("=" * 60)

        results = {
            "total_patterns_found": 0,
            "symbols_analyzed": [],
            "analysis_summary": {},
            "errors": [],
        }

        try:
            # 1. 분석 대상 심볼 확인
            symbols = self._get_available_symbols()
            print(f"📊 분석 대상 심볼: {len(symbols)}개")
            for symbol in symbols:
                print(f"   - {symbol}")

            # 2. 심볼별 패턴 분석
            for symbol in symbols:
                try:
                    print(f"\n🔍 {symbol} 패턴 분석 시작...")
                    symbol_result = self._analyze_symbol_patterns(symbol)

                    results["symbols_analyzed"].append(symbol)
                    results["analysis_summary"][symbol] = symbol_result
                    results["total_patterns_found"] += symbol_result.get(
                        "patterns_created", 0
                    )

                    print(
                        f"✅ {symbol} 분석 완료: {symbol_result.get('patterns_created', 0)}개 패턴 발견"
                    )

                except Exception as e:
                    error_msg = f"{symbol} 분석 실패: {str(e)}"
                    print(f"❌ {error_msg}")
                    results["errors"].append(error_msg)

            # 3. 전체 결과 요약
            self._print_final_summary(results)

            return results

        except Exception as e:
            print(f"❌ 전체 분석 실패: {e}")
            results["errors"].append(f"전체 분석 실패: {str(e)}")
            return results

    def _get_available_symbols(self) -> List[str]:
        """분석 가능한 심볼 목록 조회"""
        try:
            # 신호가 있는 심볼들만 조회 (raw SQL 사용)
            result = self.session.execute(
                text(
                    "SELECT DISTINCT symbol FROM technical_signals WHERE symbol IS NOT NULL"
                )
            )
            symbols = [row[0] for row in result.fetchall()]
            return symbols if symbols else ["^IXIC", "^GSPC"]
        except Exception as e:
            print(f"⚠️ 심볼 조회 실패, 기본 심볼 사용: {e}")
            return ["^IXIC", "^GSPC"]

    def _analyze_symbol_patterns(self, symbol: str) -> Dict[str, Any]:
        """특정 심볼의 패턴 분석"""
        result = {
            "symbol": symbol,
            "signal_count": 0,
            "patterns_created": 0,
            "analysis_period": None,
            "pattern_types": {},
        }

        try:
            # 1. 해당 심볼의 신호 개수 확인 (raw SQL 사용)
            count_result = self.session.execute(
                text("SELECT COUNT(*) FROM technical_signals WHERE symbol = :symbol"),
                {"symbol": symbol},
            )
            signal_count = count_result.scalar()
            result["signal_count"] = signal_count

            if signal_count == 0:
                print(f"   ⚠️ {symbol}: 분석할 신호가 없음")
                return result

            # 2. 분석 기간 확인
            date_range = self._get_signal_date_range(symbol)
            result["analysis_period"] = date_range
            print(f"   📅 분석 기간: {date_range['start']} ~ {date_range['end']}")
            print(f"   📊 총 신호 수: {signal_count}개")

            # 3. 패턴 발견 실행
            pattern_result = self.pattern_service.discover_patterns(
                symbol=symbol, timeframe="1day"
            )

            if "error" in pattern_result:
                print(f"   ❌ 패턴 발견 실패: {pattern_result['error']}")
                return result

            # 4. 결과 정리
            result["patterns_created"] = pattern_result.get("total_patterns", 0)
            result["pattern_types"] = pattern_result.get("pattern_breakdown", {})

            return result

        except Exception as e:
            print(f"   ❌ {symbol} 패턴 분석 중 오류: {e}")
            return result

    def _get_signal_date_range(self, symbol: str) -> Dict[str, str]:
        """신호 데이터의 날짜 범위 조회"""
        try:
            # raw SQL 사용
            date_result = self.session.execute(
                text(
                    """
                    SELECT 
                        MIN(triggered_at) as start_date,
                        MAX(triggered_at) as end_date
                    FROM technical_signals 
                    WHERE symbol = :symbol
                """
                ),
                {"symbol": symbol},
            )

            row = date_result.fetchone()
            if row and row[0] and row[1]:
                return {
                    "start": row[0].strftime("%Y-%m-%d"),
                    "end": row[1].strftime("%Y-%m-%d"),
                }
            else:
                return {"start": "N/A", "end": "N/A"}
        except Exception as e:
            return {"start": "N/A", "end": "N/A"}

    def _print_final_summary(self, results: Dict[str, Any]):
        """최종 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("🎉 과거 신호 패턴 분석 완료!")
        print("=" * 60)

        print(f"📊 분석 결과:")
        print(f"   - 분석된 심볼: {len(results['symbols_analyzed'])}개")
        print(f"   - 발견된 패턴: {results['total_patterns_found']}개")
        print(f"   - 오류 발생: {len(results['errors'])}개")

        if results["symbols_analyzed"]:
            print(f"\n📈 심볼별 상세 결과:")
            for symbol in results["symbols_analyzed"]:
                summary = results["analysis_summary"][symbol]
                print(
                    f"   - {symbol}: {summary['signal_count']}개 신호 → {summary['patterns_created']}개 패턴"
                )

        if results["errors"]:
            print(f"\n❌ 발생한 오류들:")
            for error in results["errors"]:
                print(f"   - {error}")

        print(f"\n✅ 이제 머신러닝 클러스터링에 사용할 패턴 데이터가 준비되었습니다!")

    def cleanup_old_patterns(self, days_old: int = 90):
        """오래된 패턴 데이터 정리 (선택사항)"""
        print(f"🧹 {days_old}일 이상 된 패턴 데이터 정리 중...")
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # raw SQL 사용
            result = self.session.execute(
                text("DELETE FROM signal_patterns WHERE created_at < :cutoff_date"),
                {"cutoff_date": cutoff_date},
            )
            deleted_count = result.rowcount

            self.session.commit()
            print(f"✅ {deleted_count}개의 오래된 패턴 삭제 완료")

        except Exception as e:
            print(f"❌ 패턴 정리 실패: {e}")
            self.session.rollback()


def main():
    """메인 실행 함수"""
    print("🔍 과거 신호 패턴 분석 스크립트 시작")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        analyzer = HistoricalPatternAnalyzer()

        # 선택사항: 오래된 패턴 정리 (주석 해제하면 실행)
        # analyzer.cleanup_old_patterns(days_old=90)

        # 과거 패턴 분석 실행
        results = analyzer.analyze_all_historical_patterns()

        # 성공 여부에 따른 종료 코드
        if results["total_patterns_found"] > 0:
            print(
                f"\n🎯 스크립트 실행 성공! {results['total_patterns_found']}개 패턴 생성됨"
            )
            sys.exit(0)
        else:
            print(f"\n⚠️ 패턴이 생성되지 않았습니다. 신호 데이터를 확인해주세요.")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n⏹️ 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 스크립트 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
