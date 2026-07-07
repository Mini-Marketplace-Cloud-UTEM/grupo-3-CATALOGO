import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.database import Base, engine
from app.routes import categories, products, uploads
from app.utils import error_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("catalog")

Base.metadata.create_all(bind=engine)

TAGS = [
    {
        "name": "Products",
        "description": (
            "Operaciones sobre el catálogo de productos. "
            "Permite listar, buscar, crear y actualizar productos. "
            "Todos los listados son **paginados**."
        ),
    },
    {
        "name": "Categories",
        "description": (
            "Operaciones sobre las categorías del catálogo. "
            "Permite listar, crear, actualizar y eliminar categorías. "
            "Una categoría no puede eliminarse si tiene productos activos."
        ),
    },
    {
        "name": "Uploads",
        "description": (
            "Subida de imágenes a Supabase Storage. "
            "Sube primero la imagen con `POST /uploads` para obtener la URL "
            "y luego úsala al crear o actualizar un producto."
        ),
    },
    {
        "name": "Health",
        "description": "Estado del servicio.",
    },
]

app = FastAPI(
    title="Catalog Service — Grupo 3",
    version="1.0.0",
    description="""
## Mini Marketplace Cloud · Grupo 3

Servicio dueño del catálogo de productos. Administra **productos**, **categorías**, **precios** y **stock visible**.

### Flujo para crear un producto con imagen

1. `POST /uploads` → sube la imagen, obtén la URL pública.
2. `POST /products` → crea el producto usando esa URL en el campo `images`.

### Headers recomendados en cada request

| Header | Descripción |
|--------|-------------|
| `X-Request-Id` | UUID único por request |
| `X-Correlation-Id` | UUID para trazabilidad entre servicios |
| `X-Consumer` | Nombre del servicio que consume (ej: `frontend-service`) |
| `Idempotency-Key` | UUID para evitar duplicados (requerido en POST y PUT) |

### Formato de error estándar

```json
{
  "code": "DUPLICATE_SKU",
  "message": "SKU already exists",
  "correlationId": "abc-123"
}
```
""",
    openapi_tags=TAGS,
    contact={
        "name": "Grupo 3 — Catálogo",
        "email": "fcares@utem.cl",
    },
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "list",
        "filter": True,
        "tryItOutEnabled": True,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id", "-")
    request_id = request.headers.get("x-request-id", "-")
    consumer = request.headers.get("x-consumer", "unknown")
    start = time.time()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.time() - start) * 1000)
        logger.error(
            "UNHANDLED ERROR %s %s | %dms | consumer=%s | correlation=%s | error=%s",
            request.method,
            request.url.path,
            duration_ms,
            consumer,
            correlation_id,
            repr(exc),
        )
        raise

    duration_ms = round((time.time() - start) * 1000)
    msg = "%s %s → %s | %dms | consumer=%s | correlation=%s | request=%s"
    args = (
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        consumer,
        correlation_id,
        request_id,
    )

    if response.status_code >= 500:
        logger.error(msg, *args)
    elif response.status_code >= 400:
        logger.warning(msg, *args)
    else:
        logger.info(msg, *args)

    return response


app.include_router(products.router)
app.include_router(categories.router)
app.include_router(uploads.router)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse("index.html")


@app.get("/health", tags=["Health"], summary="Estado del servicio")
def health():
    return {"status": "ok", "service": "catalog-service", "version": "1.0.0"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "ERROR")
        message = detail.get("message", str(detail))
        correlation_id = detail.get(
            "correlationId", request.headers.get("x-correlation-id")
        )
    else:
        code = "ERROR"
        message = str(detail)
        correlation_id = request.headers.get("x-correlation-id")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code, message, exc.status_code, correlation_id),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred",
            500,
            request.headers.get("x-correlation-id"),
        ),
    )
