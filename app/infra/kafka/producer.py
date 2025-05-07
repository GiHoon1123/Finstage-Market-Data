# app/infra/kafka/producer.py

from kafka import KafkaProducer
import json

RESULT_TOPIC = "financial.statement.result"

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def send_result_message(success: bool, symbol: str = None, reason: str = None):
    message = {
        "success": success,
        "symbol": symbol,
        "reason": reason
    }

    producer.send(RESULT_TOPIC, message)
    producer.flush()
    print("📤 결과 전송:", message)
