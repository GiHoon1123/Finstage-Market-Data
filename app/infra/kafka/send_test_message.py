# app/infra/kafka/send_test_message.py

from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

TOPIC = "financial.statement.request"

def send_test_request():
    message = {
        "symbol": "GOOGL"
    }

    print("📤 Kafka 테스트 메시지 전송:", message)
    producer.send(TOPIC, message)
    producer.flush()

if __name__ == "__main__":
    send_test_request()
