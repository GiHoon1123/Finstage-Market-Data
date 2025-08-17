#!/usr/bin/env python3
"""
슬로우 쿼리 모니터링 테스트 스크립트

슬로우 쿼리 모니터링 시스템이 제대로 작동하는지 확인합니다.
"""

import sys
import os
import asyncio
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.common.infra.database.services.slow_query_service import slow_query_service
from app.common.infra.database.monitoring.query_monitor import query_monitor
from app.common.infra.database.config.database_config import SessionLocal, engine
from app.common.infra.database.models.slow_query_log import SlowQueryLog
from sqlalchemy import text, func


def check_slow_query_table():
    """슬로우 쿼리 테이블 상태 확인"""
    print("=== 슬로우 쿼리 테이블 상태 확인 ===")
    
    session = SessionLocal()
    try:
        # 테이블 존재 확인
        result = session.execute(text("SHOW TABLES LIKE 'slow_query_logs'"))
        tables = result.fetchall()
        
        if not tables:
            print("❌ slow_query_logs 테이블이 존재하지 않습니다.")
            return False
        
        print("✅ slow_query_logs 테이블이 존재합니다.")
        
        # 테이블 구조 확인
        result = session.execute(text("DESCRIBE slow_query_logs"))
        columns = result.fetchall()
        
        print(f"📋 테이블 컬럼 수: {len(columns)}")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        # 데이터 개수 확인
        count = session.query(func.count(SlowQueryLog.id)).scalar()
        print(f"📊 저장된 슬로우 쿼리 수: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테이블 확인 실패: {str(e)}")
        return False
    finally:
        session.close()


def check_query_monitor_status():
    """쿼리 모니터 상태 확인"""
    print("\n=== 쿼리 모니터 상태 확인 ===")
    
    try:
        # 모니터링 설정 활성화
        query_monitor.setup_monitoring(engine)
        print("✅ 쿼리 모니터링이 활성화되었습니다.")
        
        # 모니터링 설정 확인
        print(f"🔧 슬로우 쿼리 임계값: {query_monitor.slow_query_threshold}초")
        print(f"📈 추적 중인 쿼리 수: {len(query_monitor.query_metrics)}")
        print(f"🐌 메모리 내 슬로우 쿼리 수: {len(query_monitor.slow_queries)}")
        
        # 성능 요약 확인
        summary = query_monitor.get_performance_summary()
        print(f"📊 전체 쿼리 수: {summary['summary']['total_queries']}")
        print(f"🐌 슬로우 쿼리 수: {summary['summary']['slow_queries']}")
        print(f"📈 평균 쿼리 시간: {summary['summary']['avg_query_time']:.3f}초")
        
        return True
        
    except Exception as e:
        print(f"❌ 모니터 상태 확인 실패: {str(e)}")
        return False


async def test_slow_query_detection():
    """슬로우 쿼리 감지 테스트"""
    print("\n=== 슬로우 쿼리 감지 테스트 ===")
    
    try:
        # 의도적으로 느린 쿼리 실행
        session = SessionLocal()
        
        # 1. SLEEP을 사용한 느린 쿼리
        print("1. SLEEP 쿼리 실행 중...")
        start_time = time.time()
        result = session.execute(text("SELECT SLEEP(2)"))
        result.fetchall()
        duration = time.time() - start_time
        print(f"   실행 시간: {duration:.3f}초")
        
        # 2. 복잡한 조인 쿼리
        print("2. 복잡한 조인 쿼리 실행 중...")
        start_time = time.time()
        result = session.execute(text("""
            SELECT c.*, ct.*, cs.* 
            FROM contents c 
            LEFT JOIN content_translations ct ON c.id = ct.content_id 
            LEFT JOIN content_sentiments cs ON c.id = cs.content_id 
            WHERE c.symbol IN ('AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN')
        """))
        result.fetchall()
        duration = time.time() - start_time
        print(f"   실행 시간: {duration:.3f}초")
        
        # 3. 대량 데이터 조회
        print("3. 대량 데이터 조회 중...")
        start_time = time.time()
        result = session.execute(text("""
            SELECT * FROM contents 
            WHERE crawled_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY crawled_at DESC
        """))
        result.fetchall()
        duration = time.time() - start_time
        print(f"   실행 시간: {duration:.3f}초")
        
        session.close()
        
        # 잠시 대기 (배치 저장 대기)
        print("⏳ 배치 저장 대기 중...")
        await asyncio.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"❌ 슬로우 쿼리 테스트 실패: {str(e)}")
        return False


def check_slow_query_logs():
    """슬로우 쿼리 로그 확인"""
    print("\n=== 슬로우 쿼리 로그 확인 ===")
    
    session = SessionLocal()
    try:
        # 최근 슬로우 쿼리 조회
        recent_logs = session.query(SlowQueryLog).order_by(
            SlowQueryLog.execution_timestamp.desc()
        ).limit(10).all()
        
        if not recent_logs:
            print("❌ 저장된 슬로우 쿼리 로그가 없습니다.")
            return False
        
        print(f"✅ 최근 {len(recent_logs)}개의 슬로우 쿼리 로그를 찾았습니다.\n")
        
        for i, log in enumerate(recent_logs, 1):
            print(f"{i}. 쿼리 해시: {log.query_hash}")
            print(f"   실행 시간: {log.duration:.3f}초")
            print(f"   쿼리 타입: {log.operation_type}")
            print(f"   테이블: {log.table_names}")
            print(f"   실행 시각: {log.execution_timestamp}")
            print(f"   원본 쿼리: {log.original_query[:100]}..." if log.original_query else "   원본 쿼리: 없음")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 슬로우 쿼리 로그 확인 실패: {str(e)}")
        return False
    finally:
        session.close()


async def test_slow_query_service():
    """슬로우 쿼리 서비스 테스트"""
    print("\n=== 슬로우 쿼리 서비스 테스트 ===")
    
    try:
        # 테스트 데이터로 슬로우 쿼리 저장
        test_data = {
            "query_hash": "test_hash_001",
            "query_template": "SELECT * FROM test_table WHERE id = ?",
            "original_query": "SELECT * FROM test_table WHERE id = 123",
            "duration": 3.5,
            "affected_rows": 1,
            "table_names": ["test_table"],
            "operation_type": "SELECT",
            "execution_timestamp": "2024-01-01 12:00:00"
        }
        
        success = await slow_query_service.save_slow_query(**test_data)
        
        if success:
            print("✅ 테스트 슬로우 쿼리 저장 성공")
        else:
            print("❌ 테스트 슬로우 쿼리 저장 실패")
        
        # 배치 저장 강제 실행
        await slow_query_service._flush_batch()
        print("✅ 배치 저장 완료")
        
        return success
        
    except Exception as e:
        print(f"❌ 슬로우 쿼리 서비스 테스트 실패: {str(e)}")
        return False


async def main():
    """메인 테스트 함수"""
    print("슬로우 쿼리 모니터링 테스트를 시작합니다...\n")
    
    # 1. 테이블 상태 확인
    table_exists = check_slow_query_table()
    
    # 2. 쿼리 모니터 상태 확인
    monitor_ok = check_query_monitor_status()
    
    # 3. 슬로우 쿼리 감지 테스트
    detection_ok = await test_slow_query_detection()
    
    # 4. 슬로우 쿼리 로그 확인
    logs_ok = check_slow_query_logs()
    
    # 5. 서비스 테스트
    service_ok = await test_slow_query_service()
    
    # 최종 결과
    print("\n=== 테스트 결과 요약 ===")
    print(f"테이블 존재: {'✅' if table_exists else '❌'}")
    print(f"모니터 상태: {'✅' if monitor_ok else '❌'}")
    print(f"감지 기능: {'✅' if detection_ok else '❌'}")
    print(f"로그 저장: {'✅' if logs_ok else '❌'}")
    print(f"서비스 기능: {'✅' if service_ok else '❌'}")
    
    if all([table_exists, monitor_ok, detection_ok, logs_ok, service_ok]):
        print("\n🎉 모든 테스트가 성공했습니다!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 문제를 확인해주세요.")


if __name__ == "__main__":
    asyncio.run(main())
