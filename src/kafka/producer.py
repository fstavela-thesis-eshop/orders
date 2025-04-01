import logging
from json import dumps
from os import getenv
from typing import Any
from uuid import UUID

from confluent_kafka import KafkaError
from confluent_kafka import Message
from confluent_kafka import Producer

from schemas.order_schemas import OrderEvent
from schemas.order_schemas import OrderResponse

logger = logging.getLogger(__name__)

ORDERS_TOPIC = getenv("KAFKA_ORDERS_TOPIC", "orders")


producer_conf = {"bootstrap.servers": getenv("KAFKA_SERVER", "localhost:9092")}

producer = Producer(producer_conf)


def _convert_uuids_to_str(data: dict[str, Any]) -> dict[str, Any]:
    for key, value in data.items():
        if isinstance(value, UUID):
            data[key] = str(value)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, UUID):
                    data[key][i] = str(item)
                elif isinstance(item, dict):
                    data[key][i] = _convert_uuids_to_str(item)
        elif isinstance(value, dict):
            data[key] = _convert_uuids_to_str(value)
    return data


def _log_event_delivery(err: KafkaError, msg: Message) -> None:
    if err is not None:
        logger.error(f"Kafka event delivery failed: {err}")
    else:
        logger.warning(
            f"Kafka event produced:\nTopic: {msg.topic()}; "
            f"Partition: {msg.partition()}; Offset: {msg.offset()}\n"
            f"Key: {msg.key()}; Message: {msg.value()}"
        )


def _produce_event(topic: str, key: str, event: dict[str, Any]) -> None:
    producer.produce(
        topic, dumps(event).encode("utf-8"), key=key, callback=_log_event_delivery
    )
    producer.flush()


def _produce_order_event(order_event: OrderEvent) -> None:
    event = _convert_uuids_to_str(order_event.model_dump())
    _produce_event(ORDERS_TOPIC, str(order_event.customer_id), event)


def produce_new_order_event(order_response: OrderResponse) -> None:
    order_event = OrderEvent.model_validate(
        dict(order_response.model_dump(), message="New order created")
    )
    _produce_order_event(order_event)


def produce_updated_order_status_event(order_response: OrderResponse) -> None:
    order_event = OrderEvent.model_validate(
        dict(
            order_response.model_dump(),
            message=f"Order status updated: {order_response.status.value}",
        )
    )
    _produce_order_event(order_event)


def produce_cancelled_order_event(order_response: OrderResponse) -> None:
    order_event = OrderEvent.model_validate(
        dict(order_response.model_dump(), message="Order cancelled")
    )
    _produce_order_event(order_event)
