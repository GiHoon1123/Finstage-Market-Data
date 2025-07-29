#!/usr/bin/env python3
"""
메시지 내용 디버깅
"""

import os
from dotenv import load_dotenv

# 테스트 환경 설정
os.environ["ENV_MODE"] = "test"
mode = os.getenv("ENV_MODE", "test")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)

print("🔍 메시지 내용 디버깅")

service = DailyComprehensiveReportService()

# 각 분석 모듈별 데이터 수집
backtesting_data = service._get_backtesting_analysis()
pattern_data = service._get_pattern_analysis()
ml_data = service._get_ml_analysis()
insights_data = service._get_investment_insights()

# 리포트 메시지 생성
report_message = service._generate_report_message(
    backtesting_data, pattern_data, ml_data, insights_data
)

print("📝 생성된 메시지:")
print("=" * 50)
print(report_message)
print("=" * 50)
print(f"메시지 길이: {len(report_message)}자")

# HTML 태그 검증
import re

html_tags = re.findall(r"<[^>]*>", report_message)
print(f"\n🏷️ 발견된 HTML 태그들:")
for i, tag in enumerate(html_tags):
    print(f"{i+1}: {tag}")
