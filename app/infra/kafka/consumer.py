from kafka import KafkaConsumer
import json
from app.infra.db.db import SessionLocal
from app.services.financial_service import FinancialService
from app.infra.kafka.producer import send_result_message

TOPIC = "financial.statement.request"

def consume_financial_requests():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers="localhost:9092",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="financial-statement-group",
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    print("📥 Kafka Consumer 시작...")

    for message in consumer:
        payload = message.value
        symbol = payload.get("symbol")

        if not symbol:
            prin("❌ 유효하지 않은 요청:", payload)
            continue

        print(f"➡️ 처리 시작: {symbol}")

        db = SessionLocal()
        service = FinancialService(db)

        # 심볼 유효성 검증
        verified = service.search_symbol(symbol)
        if not verified:
            print(f"❌ 심볼 검증 실패: {symbol}")
            send_result_message(symbol=symbol, success=False, reason="Invalid symbol")
            db.close()
            continue

        # DB에 이미 있으면 저장 생략
        if service.load_statements(symbol):
            print(f"🔄 이미 저장된 심볼({symbol}), 저장 생략")
            db.commit()  # ✅ rollback 로그 방지를 위해 commit 추가
            send_result_message(symbol=symbol, success=True)
            db.close()
            continue

        # API 호출 및 저장
        data = service.get_financial_statements(symbol)
        if not data:
            print(f"❌ 재무제표 조회 실패: {symbol}")
            send_result_message(symbol=symbol, success=False, reason="Failed to fetch financial statements")
            db.close()
            continue

        success = service.save_statements_to_db(symbol, data)
        if success:
            print(f"✅ 저장 성공: {symbol}")
            send_result_message(symbol=symbol, success=True)
        else:
            print(f"❌ 저장 실패: {symbol}")
            send_result_message(symbol=symbol, success=False, reason="Database save failed")

        db.close()

if __name__ == "__main__":
    consume_financial_requests()
