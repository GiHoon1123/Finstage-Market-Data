#!/bin/bash
# 테스트 환경 변수를 사용하여 API 테스트를 실행하는 스크립트

# 현재 디렉토리를 스크립트 위치로 변경
cd "$(dirname "$0")"
cd ..

# 환경 변수 파일 로드
echo "🔧 테스트 환경 변수 로드 중..."
export $(grep -v '^#' .env.test | xargs)
export ENV_MODE=test

# API 서버 실행 확인
echo "🔍 API 서버 실행 확인 중..."
if ! curl -s "http://127.0.0.1:8081/api/test/env-check" > /dev/null; then
    echo "❌ API 서버가 실행 중이지 않습니다. 서버를 먼저 실행해주세요."
    exit 1
fi

# 테스트 유형 확인
TEST_TYPE=${1:-"all"}
echo "🧪 테스트 유형: $TEST_TYPE"

# API 테스트 실행
echo "🚀 API 테스트 실행 중..."
case $TEST_TYPE in
    "all")
        curl -X POST "http://127.0.0.1:8081/api/test/telegram-alerts/all"
        ;;
    "ma")
        curl -X POST "http://127.0.0.1:8081/api/test/telegram-alerts/ma-breakout?symbol=^IXIC&ma_period=200&direction=up"
        ;;
    "rsi")
        curl -X POST "http://127.0.0.1:8081/api/test/telegram-alerts/rsi?symbol=^IXIC&signal_type=overbought"
        ;;
    "bollinger")
        curl -X POST "http://127.0.0.1:8081/api/test/telegram-alerts/bollinger?symbol=^IXIC&signal_type=touch_upper"
        ;;
    "cross")
        curl -X POST "http://127.0.0.1:8081/api/test/telegram-alerts/cross?symbol=^IXIC&cross_type=golden"
        ;;
    *)
        echo "❌ 알 수 없는 테스트 유형: $TEST_TYPE"
        echo "사용 가능한 테스트 유형: all, ma, rsi, bollinger, cross"
        exit 1
        ;;
esac

echo "✅ API 테스트 완료!"