import os
from typing import Optional

import httpx
from fastapi import Header, HTTPException

AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL", "https://grupo2-identidadusuario.onrender.com"
)
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"


async def require_admin(
    authorization: Optional[str] = Header(None),
    x_correlation_id: Optional[str] = Header(None),
):
    if not AUTH_ENABLED:
        return {"id": "test", "roles": ["admin"]}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Se requiere token de autenticación (Authorization: Bearer <token>)",
                "correlationId": x_correlation_id,
            },
        )

    token = authorization.removeprefix("Bearer ")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AUTH_SERVICE_UNAVAILABLE",
                "message": "No se pudo contactar el servicio de autenticación",
                "correlationId": x_correlation_id,
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Token ausente o inválido",
                "correlationId": x_correlation_id,
            },
        )

    data = response.json()
    roles = data.get("user", {}).get("roles", [])

    if "admin" not in roles:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Se requiere rol de administrador",
                "correlationId": x_correlation_id,
            },
        )

    return data.get("user")
