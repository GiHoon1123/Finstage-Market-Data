#!/usr/bin/env python3
"""
긴급 데이터베이스 연결 풀 문제 해결 스크립트
"""

import time
import gc
from sqlalchemy import create_engine, text
from app.config import MYSQL_URL


def check_mysql_connections():
    """MySQL 연결 상태 확인"""
    try:
        # 임시 엔진 생성 (최소 설정)
        temp_engine = create_engine(
            MYSQL_URL, pool_size=1, max_overflow=0, pool_timeout=10
        )

        with temp_engine.connect() as conn:
            # 현재 연결 수 확인
            result = conn.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
            threads_connected = result.fetchone()[1]

            # 최대 연결 수 확인
            result = conn.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
            max_connections = result.fetchone()[1]

            print(f"현재 연결 수: {threads_connected}")
            print(f"최대 연결 수: {max_connections}")
            print(
                f"연결 사용률: {int(threads_connected)/int(max_connections)*100:.1f}%"
            )

            # 프로세스 리스트 확인
            result = conn.execute(text("SHOW PROCESSLIST"))
            processes = result.fetchall()

            print(f"\n활성 프로세스 수: {len(processes)}")

            # Sleep 상태인 연결들 확인
            sleep_count = sum(1 for p in processes if p[4] == "Sleep")
            print(f"Sleep 상태 연결: {sleep_count}")

        temp_engine.dispose()
        return True

    except Exception as e:
        print(f"MySQL 연결 확인 실패: {e}")
        return False


def force_cleanup_connections():
    """강제로 연결 정리"""
    try:
        # 가비지 컬렉션 강제 실행
        gc.collect()

        # 기존 엔진 정리
        from app.common.infra.database.config.database_config import engine

        engine.dispose()

        print("데이터베이스 연결 풀 정리 완료")
        time.sleep(5)  # 5초 대기

        return True

    except Exception as e:
        print(f"연결 정리 실패: {e}")
        return False


if __name__ == "__main__":
    print("=== 긴급 데이터베이스 연결 상태 확인 ===")

    # 1. 현재 상태 확인
    check_mysql_connections()

    print("\n=== 연결 정리 실행 ===")

    # 2. 강제 정리
    force_cleanup_connections()

    print("\n=== 정리 후 상태 확인 ===")

    # 3. 정리 후 상태 확인
    check_mysql_connections()
