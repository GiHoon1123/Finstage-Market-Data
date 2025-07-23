#!/bin/bash
# 테스트 환경 변수를 사용하여 테스트를 실행하는 스크립트

# 현재 디렉토리를 스크립트 위치로 변경
cd "$(dirname "$0")"
cd ..

# 환경 변수 파일 로드
echo "🔧 테스트 환경 변수 로드 중..."
export $(grep -v '^#' .env.test | xargs)
export ENV_MODE=test

# 테스트 유형 확인
TEST_TYPE=${1:-"all"}
echo "🧪 테스트 유형: $TEST_TYPE"

# 테스트 실행
echo "🚀 테스트 실행 중..."
python test_script/test_telegram_alerts.py $TEST_TYPE

echo "✅ 테스트 완료!"