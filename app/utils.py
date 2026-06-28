from datetime import datetime, timezone
from typing import Optional


def error_response(
    code: str,
    message: str,
    status: int,
    correlation_id: Optional[str] = None,
) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "code": code,
        "message": message,
        "correlationId": correlation_id,
    }
