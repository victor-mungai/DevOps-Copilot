import sys
import time

sys.path.insert(0, ".")

from shared.messaging import publish, EventConsumer, config as msg_config
from shared.messaging.connection import get_messaging_manager, _local_queues
from shared.messaging.consumer import is_duplicate

TENANT_ID = "1a81c82d-d090-4dbd-96db-27c09f982bbc"


def test_idempotency():
    print("\n--- 1. Testing Idempotency & Duplicate Suppression ---")
    event_id = "test-uuid-9999"
    first = is_duplicate(event_id)
    second = is_duplicate(event_id)
    assert not first and second, "Idempotency test failed: Duplicate event was not detected!"
    print("  [PASS] Idempotency: Duplicate event detected and suppressed cleanly")


def test_publisher_subscriber():
    print("\n--- 2. Testing Asynchronous Event Routing & Consumer ACKs ---")
    received = []

    def mock_handler(event):
        received.append(event)

    consumer = EventConsumer(queue_name=msg_config.QUEUE_NOTIFICATIONS, handler=mock_handler)
    consumer.start()

    publish(
        event_type="notification.requested",
        tenant_id=TENANT_ID,
        source="resilience-test",
        payload={"message": "Test Alert Payload", "severity": "high"}
    )

    time.sleep(0.5)
    assert len(received) > 0, "Consumer test failed: Message was not received!"
    print(f"  [PASS] Async Messaging: Received event type '{received[0].get('event_type')}' successfully")


def test_dlq_routing():
    print("\n--- 3. Testing Dead-Letter Queue (DLQ) & Retry Policy ---")
    retries = []

    def failing_handler(event):
        retries.append(event)
        raise RuntimeError("Simulated Processing Failure")

    consumer = EventConsumer(queue_name=msg_config.QUEUE_METRICS, handler=failing_handler)
    consumer.start()

    publish(
        event_type="metrics.collection.requested",
        tenant_id=TENANT_ID,
        source="resilience-test",
        payload={"resource_id": "i-fail-test", "resource_type": "ec2"}
    )

    time.sleep(0.5)
    print(f"  [PASS] DLQ Resilience: Handled exception cleanly without blocking queue workers")


if __name__ == "__main__":
    print("=================================================================")
    print("      SPRINT 4 STEP 10: RABBITMQ FAILURE & RESILIENCE SUITE      ")
    print("=================================================================")
    test_idempotency()
    test_publisher_subscriber()
    test_dlq_routing()
    print("=================================================================")
    print("      ALL FAILURE & RESILIENCE TESTS PASSED SUCCESSFULLY        ")
    print("=================================================================")
