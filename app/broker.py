import json
import logging
import os
from typing import Any, Callable, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractRobustConnection

logger = logging.getLogger("catalog.broker")

CLOUDAMQP_URL: str = os.getenv("CLOUDAMQP_URL", "")
EXCHANGE_NAME: str = os.getenv("CLOUDAMQP_EXCHANGE", "marketplace.events")

_connection: Optional[AbstractRobustConnection] = None
_exchange: Optional[aio_pika.abc.AbstractExchange] = None


async def connect() -> None:
    global _connection, _exchange
    if not CLOUDAMQP_URL:
        logger.warning("CLOUDAMQP_URL no configurada — eventos solo en log")
        return
    try:
        _connection = await aio_pika.connect_robust(CLOUDAMQP_URL)
        channel = await _connection.channel()
        _exchange = await channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        logger.info("Broker conectado exchange=%s", EXCHANGE_NAME)
    except Exception as exc:
        logger.error("Error conectando al broker: %s", repr(exc))


async def disconnect() -> None:
    global _connection
    if _connection:
        await _connection.close()
        _connection = None
        logger.info("Broker desconectado")


async def publish(routing_key: str, payload: dict) -> None:
    logger.info("EVENT %s %s", routing_key, payload)
    if _exchange is None:
        return
    try:
        await _exchange.publish(
            Message(
                body=json.dumps(payload, default=str).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )
        logger.info("EVENT SENT routing_key=%s", routing_key)
    except Exception as exc:
        logger.error("Error publicando evento %s: %s", routing_key, repr(exc))


async def start_consumer(
    routing_key: str,
    queue_name: str,
    handler: Callable[[Any], Any],
) -> None:
    """Suscribe una cola al exchange y empieza a consumir mensajes."""
    if _connection is None:
        logger.warning("Broker no conectado — no se puede suscribir a %s", routing_key)
        return
    channel = await _connection.channel()
    await channel.set_qos(prefetch_count=10)
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.bind(exchange, routing_key=routing_key)
    await queue.consume(handler)
    logger.info("Consumidor activo queue=%s routing_key=%s", queue_name, routing_key)
