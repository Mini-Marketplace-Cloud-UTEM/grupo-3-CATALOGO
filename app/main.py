from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime, timezone

from app.database import Base, engine
from app.routes import products, uploads

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
  "timestamp": "2026-06-20T10:00:00Z",
  "status": 409,
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

app.include_router(products.router)
app.include_router(uploads.router)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse("index.html")


@app.get("/health", tags=["Health"], summary="Estado del servicio")
def health():
    return {"status": "ok", "service": "catalog-service", "version": "1.0.0"}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": 500,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "correlationId": request.headers.get("x-correlation-id"),
        },
    )
