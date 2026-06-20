import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, File, Header, UploadFile
from fastapi.responses import JSONResponse
from supabase import create_client

load_dotenv()

router = APIRouter(prefix="/uploads", tags=["Uploads"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET = "products"

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 5


def _error(status: int, code: str, message: str, correlation_id=None) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "code": code,
        "message": message,
        "correlationId": correlation_id,
    }


@router.post("", summary="Subir imagen de producto",
    description="Sube una imagen a Supabase Storage y retorna la URL pública. Úsala luego en POST /products.")
async def upload_image(
    file: UploadFile = File(...),
    x_correlation_id: str | None = Header(None),
    x_consumer: str | None = Header(None),
):
    # Verificar que las credenciales de Supabase Storage estén configuradas
    if not SUPABASE_URL or not SUPABASE_KEY:
        return JSONResponse(status_code=503, content=_error(
            503, "STORAGE_NOT_CONFIGURED",
            "Faltan SUPABASE_URL o SUPABASE_KEY en las variables de entorno.",
            x_correlation_id,
        ))

    if file.content_type not in ALLOWED_TYPES:
        return JSONResponse(status_code=400, content=_error(
            400, "INVALID_FILE_TYPE",
            f"Solo se permiten JPEG, PNG o WebP. Recibido: {file.content_type}",
            x_correlation_id,
        ))

    content = await file.read()

    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        return JSONResponse(status_code=400, content=_error(
            400, "FILE_TOO_LARGE",
            f"El archivo supera el límite de {MAX_SIZE_MB}MB.",
            x_correlation_id,
        ))

    extension = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    path = f"products/{uuid.uuid4()}.{extension}"

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=content,
        file_options={"content-type": file.content_type},
    )

    public_url = supabase.storage.from_(BUCKET).get_public_url(path)
    return {"url": public_url}
