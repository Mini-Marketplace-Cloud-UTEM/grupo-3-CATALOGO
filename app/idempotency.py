from typing import Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import IdempotencyRecord


def get_cached_response(
    db: Session, key: Optional[str], endpoint: str
) -> Optional[Tuple[int, dict]]:
    if not key:
        return None

    record = (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.key == key, IdempotencyRecord.endpoint == endpoint)
        .first()
    )
    if not record:
        return None

    return record.response_status, record.response_body


def store_response(
    db: Session, key: Optional[str], endpoint: str, status: int, body: dict
) -> None:
    if not key:
        return

    try:
        db.add(
            IdempotencyRecord(
                key=key,
                endpoint=endpoint,
                response_status=status,
                response_body=body,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
