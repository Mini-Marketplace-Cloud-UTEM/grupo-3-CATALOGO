import hashlib
import json
from typing import Literal, Optional, Tuple, Union

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import IdempotencyRecord

CONFLICT: Literal["CONFLICT"] = "CONFLICT"


def compute_request_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_cached_response(
    db: Session, key: Optional[str], endpoint: str, request_hash: str
) -> Union[Tuple[int, dict], Literal["CONFLICT"], None]:
    """
    Retorna:
    - None: no hay key o no hay registro previo -> seguir con la operacion normal.
    - (status, body): el mismo key se uso antes con los MISMOS datos -> replay seguro.
    - "CONFLICT": el mismo key se uso antes con datos DISTINTOS.
    """
    if not key:
        return None

    record = (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.key == key, IdempotencyRecord.endpoint == endpoint)
        .first()
    )
    if not record:
        return None

    if record.request_hash is not None and record.request_hash != request_hash:
        return CONFLICT

    return record.response_status, record.response_body


def store_response(
    db: Session,
    key: Optional[str],
    endpoint: str,
    status: int,
    body: dict,
    request_hash: str,
) -> None:
    if not key:
        return

    try:
        db.add(
            IdempotencyRecord(
                key=key,
                endpoint=endpoint,
                request_hash=request_hash,
                response_status=status,
                response_body=body,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
