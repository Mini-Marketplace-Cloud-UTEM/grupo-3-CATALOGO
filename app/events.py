import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import broker

logger = logging.getLogger("catalog.events")


def _envelope(event: str, correlation_id: Optional[str], data: dict) -> dict:
    return {
        "event": event,
        "eventId": str(uuid.uuid4()),
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "source": "catalog-service",
        "correlationId": correlation_id,
        "data": data,
    }


async def publish_product_created(
    product_id: uuid.UUID,
    sku: str,
    name: str,
    price: int,
    category_id: uuid.UUID,
    correlation_id: Optional[str],
) -> None:
    await broker.publish(
        "catalog.product.created",
        _envelope(
            "ProductCreated",
            correlation_id,
            {
                "productId": str(product_id),
                "sku": sku,
                "name": name,
                "price": price,
                "categoryId": str(category_id),
            },
        ),
    )


async def publish_product_price_changed(
    product_id: uuid.UUID,
    sku: str,
    old_price: int,
    new_price: int,
    correlation_id: Optional[str],
) -> None:
    await broker.publish(
        "catalog.product.price.changed",
        _envelope(
            "ProductPriceChanged",
            correlation_id,
            {
                "productId": str(product_id),
                "sku": sku,
                "oldPrice": old_price,
                "newPrice": new_price,
            },
        ),
    )


async def publish_product_status_changed(
    product_id: uuid.UUID,
    sku: str,
    old_status: str,
    new_status: str,
    correlation_id: Optional[str],
) -> None:
    await broker.publish(
        "catalog.product.status.changed",
        _envelope(
            "ProductStatusChanged",
            correlation_id,
            {
                "productId": str(product_id),
                "sku": sku,
                "oldStatus": old_status,
                "newStatus": new_status,
            },
        ),
    )
