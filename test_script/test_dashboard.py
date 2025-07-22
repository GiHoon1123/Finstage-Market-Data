#!/usr/bin/env python3
"""
대시보드 테스트 (한 번만 실행)
"""

import os
import sys

# 환경 변수 설정
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "finstage_dev"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitoring_dashboard import get_dashboard_data, display_dashboard
from app.technical_analysis.service.enhanced_outcome_tracking_service import (
    EnhancedOutcomeTrackingService,
)


def main():
    print("🧪 대시보드 테스트")

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결
        session, _, _ = service._get_session_and_repositories()

        # 데이터 가져오기
        data = get_dashboard_data(session)

        # 대시보드 표시
        display_dashboard(data)

        # 세션 정리
        session.close()

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
