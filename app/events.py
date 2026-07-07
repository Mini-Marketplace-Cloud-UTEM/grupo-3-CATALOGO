import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("catalog.events")

_SUBSCRIBERS = [
    url.strip() for url in os.getenv("EVENT_SUBSCRIBERS", "").split(",") if url.strip()
]


async def _dispatch(event: dict) -> None:
    logger.info("EVENT PUBLISHED %s %s", event["event"], event)

    if not _SUBSCRIBERS:
        return

    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in _SUBSCRIBERS:
            try:
                response = await client.post(
                    url, json=event, headers={"X-Consumer": "catalog-service"}
                )
                logger.info(
                    "EVENT DELIVERED subscriber=%s status=%d", url, response.status_code
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "EVENT DELIVERY FAILED subscriber=%s error=%s", url, repr(exc)
                )


async def publish_product_price_changed(
    product_id: uuid.UUID,
    sku: str,
    old_price: int,
    new_price: int,
    correlation_id: Optional[str],
) -> None:
    await _dispatch(
        {
            "event": "ProductPriceChanged",
            "eventId": str(uuid.uuid4()),
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "correlationId": correlation_id,
            "data": {
                "productId": str(product_id),
                "sku": sku,
                "oldPrice": old_price,
                "newPrice": new_price,
            },
        }
    )


async def publish_product_status_changed(
    product_id: uuid.UUID,
    sku: str,
    old_status: str,
    new_status: str,
    correlation_id: Optional[str],
) -> None:
    await _dispatch(
        {
            "event": "ProductStatusChanged",
            "eventId": str(uuid.uuid4()),
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "correlationId": correlation_id,
            "data": {
                "productId": str(product_id),
                "sku": sku,
                "oldStatus": old_status,
                "newStatus": new_status,
            },
        }
    )
