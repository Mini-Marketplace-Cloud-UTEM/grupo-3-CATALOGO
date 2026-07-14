import math
import re
import uuid
from typing import Literal, Optional

from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session, joinedload

from app.auth import require_admin
from app.database import get_db
from app.events import publish_product_price_changed, publish_product_status_changed
from app.idempotency import (
    CONFLICT,
    compute_request_hash,
    get_cached_response,
    store_response,
)
from app.models import Category, Product
from app.schemas import (
    CreateProductRequest,
    ProductListResponse,
    ProductResponse,
    UpdateProductRequest,
)
from app.utils import error_response

router = APIRouter(prefix="/products", tags=["Products"])

_ERROR_RESPONSES = {
    400: {
        "description": "Solicitud inválida",
        "content": {
            "application/json": {
                "example": {
                    "timestamp": "2026-05-25T10:00:00Z",
                    "status": 400,
                    "code": "INVALID_REQUEST",
                    "message": "Invalid input",
                    "correlationId": "abc-123",
                }
            }
        },
    },
    404: {
        "description": "Producto no encontrado",
        "content": {
            "application/json": {
                "example": {
                    "timestamp": "2026-05-25T10:00:00Z",
                    "status": 404,
                    "code": "PRODUCT_NOT_FOUND",
                    "message": "Product not found",
                    "correlationId": "abc-123",
                }
            }
        },
    },
    409: {
        "description": "SKU duplicado",
        "content": {
            "application/json": {
                "example": {
                    "timestamp": "2026-05-25T10:00:00Z",
                    "status": 409,
                    "code": "DUPLICATE_SKU",
                    "message": "SKU already exists",
                    "correlationId": "abc-123",
                }
            }
        },
    },
}


def _to_dict(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": int(product.price),
        "stockVisible": product.stock_visible,
        "categoryId": product.category_id,
        "categoryName": product.category.name if product.category else None,
        "sku": product.sku,
        "status": product.status,
        "size": product.size,
        "images": product.images or [],
        "createdAt": product.created_at,
        "updatedAt": product.updated_at,
    }


def _generate_sku(name: str, db: Session) -> str:
    prefix = "".join(c for c in name.upper() if c.isalpha())[:3]

    match_w = re.search(r"(\d+)\s*[wW]\b", name)
    match_v = re.search(r"(\d+[,.]?\d*)\s*[vV]\b", name)
    match_n = re.search(r"(\d+)", name)

    if match_w:
        mid = f"{match_w.group(1)}W"
    elif match_v:
        voltage = match_v.group(1).replace(",", "").replace(".", "")
        mid = f"{voltage}V"
    elif match_n:
        mid = match_n.group(1)[:4]
    else:
        words = [w for w in name.upper().split() if len(w) > 2 and w.isalpha()]
        mid = words[0][:3] if len(words) >= 1 else "GEN"

    count = db.query(Product).filter(Product.sku.like(f"{prefix}-%")).count()
    correlative = str(count + 1).zfill(3)
    return f"{prefix}-{mid}-{correlative}"


def _paginate(query, page: int, size: int) -> tuple:
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    total_pages = math.ceil(total / size) if total > 0 else 1

    pagination = {
        "page": page,
        "pageSize": size,
        "total": total,
        "totalPages": total_pages,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
    }
    return items, pagination


# ── GET /products ─────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=ProductListResponse,
    summary="Listar productos paginados",
    description="Retorna todos los productos activos del catálogo con paginación.",
    responses={400: _ERROR_RESPONSES[400]},
)
def list_products(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Productos por página (máx. 100)"),
    categoryId: Optional[uuid.UUID] = Query(None, description="Filtrar por categoría"),
    db: Session = Depends(get_db),
    x_request_id: Optional[str] = Header(None),
    x_correlation_id: Optional[str] = Header(None),
    x_consumer: Optional[str] = Header(None),
):
    query = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.status != "DELETED")
    )
    if categoryId:
        query = query.filter(Product.category_id == categoryId)
    items, pagination = _paginate(query, page, size)
    return {"data": [_to_dict(p) for p in items], "pagination": pagination}


# ── GET /products/search ──────────────────────────────────────────────────────
# OJO: debe ir ANTES de /{product_id} para que FastAPI no confunda
# la palabra "search" con un UUID.


@router.get(
    "/search",
    response_model=ProductListResponse,
    summary="Buscar productos",
    description="Busca por texto en nombre y descripción. Parámetro `q` obligatorio (mín. 2 caracteres).",
    responses={400: _ERROR_RESPONSES[400]},
)
def search_products(
    q: str = Query(..., min_length=2, description="Texto a buscar"),
    categoryId: Optional[uuid.UUID] = Query(None, description="Filtrar por categoría"),
    status: Optional[Literal["ACTIVE", "INACTIVE", "DELETED"]] = Query(
        None, description="Filtrar por estado"
    ),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(None),
):
    query = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.name.ilike(f"%{q}%") | Product.description.ilike(f"%{q}%"))
    )

    if categoryId:
        query = query.filter(Product.category_id == categoryId)
    if status:
        query = query.filter(Product.status == status)
    else:
        query = query.filter(Product.status != "DELETED")

    items, pagination = _paginate(query, page, size)
    return {"data": [_to_dict(p) for p in items], "pagination": pagination}


# ── GET /products/{id} ────────────────────────────────────────────────────────


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Obtener producto por ID",
    description="Retorna un producto por UUID. Devuelve 404 si no existe o fue eliminado.",
    responses={404: _ERROR_RESPONSES[404]},
)
def get_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(None),
):
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id, Product.status != "DELETED")
        .first()
    )

    if not product:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "PRODUCT_NOT_FOUND", "Product not found", 404, x_correlation_id
            ),
        )

    return _to_dict(product)


# ── POST /products ────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ProductResponse,
    status_code=201,
    summary="Crear producto",
    description=(
        "Crea un producto. El SKU debe ser único. Sube la imagen primero con `POST /uploads`. "
        "`stockVisible` siempre inicia en 0: lo administra Grupo 6 (Inventario) vía `PUT /products/{id}`."
    ),
    responses={400: _ERROR_RESPONSES[400], 409: _ERROR_RESPONSES[409]},
)
def create_product(
    body: CreateProductRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    idempotency_key: Optional[str] = Header(
        None, description="UUID para evitar duplicados en reintentos"
    ),
    x_correlation_id: Optional[str] = Header(None),
):
    endpoint = "POST /products"

    if not idempotency_key:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "INVALID_REQUEST",
                "Idempotency-Key header is required",
                400,
                x_correlation_id,
            ),
        )

    request_hash = compute_request_hash(body.model_dump())
    cached = get_cached_response(db, idempotency_key, endpoint, request_hash)
    if cached == CONFLICT:
        return JSONResponse(
            status_code=409,
            content=error_response(
                "IDEMPOTENCY_KEY_CONFLICT",
                "Esta Idempotency-Key ya se usó con datos diferentes. Usa una key distinta para esta operación.",
                409,
                x_correlation_id,
            ),
        )
    if cached:
        status, body_cached = cached
        return JSONResponse(status_code=status, content=body_cached)

    if not db.query(Category).filter(Category.id == body.category_id).first():
        content = error_response(
            "INVALID_REQUEST", "Category not found", 400, x_correlation_id
        )
        store_response(db, idempotency_key, endpoint, 400, content, request_hash)
        return JSONResponse(status_code=400, content=content)

    sku = body.sku or _generate_sku(body.name, db)

    if db.query(Product).filter(Product.sku == sku).first():
        content = error_response(
            "DUPLICATE_SKU", "SKU already exists", 409, x_correlation_id
        )
        store_response(db, idempotency_key, endpoint, 409, content, request_hash)
        return JSONResponse(status_code=409, content=content)

    product = Product(**body.model_dump(exclude={"sku"}), sku=sku, status="ACTIVE")
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        content = error_response(
            "DUPLICATE_SKU", "SKU already exists", 409, x_correlation_id
        )
        store_response(db, idempotency_key, endpoint, 409, content, request_hash)
        return JSONResponse(status_code=409, content=content)
    db.refresh(product)

    content = jsonable_encoder(_to_dict(product))
    store_response(db, idempotency_key, endpoint, 201, content, request_hash)
    return content


# ── PUT /products/{id} ────────────────────────────────────────────────────────


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar producto",
    description="Actualiza solo los campos enviados. El Grupo 6 usa esto para actualizar `stockVisible`.",
    responses={400: _ERROR_RESPONSES[400], 404: _ERROR_RESPONSES[404]},
)
def update_product(
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    x_correlation_id: Optional[str] = Header(None),
):
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id, Product.status != "DELETED")
        .first()
    )

    if not product:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "PRODUCT_NOT_FOUND", "Product not found", 404, x_correlation_id
            ),
        )

    updates = body.model_dump(exclude_none=True)
    old_price = product.price
    old_status = product.status

    for field, value in updates.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    if "price" in updates and product.price != old_price:
        background_tasks.add_task(
            publish_product_price_changed,
            product_id=product.id,
            sku=product.sku,
            old_price=old_price,
            new_price=product.price,
            correlation_id=x_correlation_id,
        )

    if "status" in updates and product.status != old_status:
        background_tasks.add_task(
            publish_product_status_changed,
            product_id=product.id,
            sku=product.sku,
            old_status=old_status,
            new_status=product.status,
            correlation_id=x_correlation_id,
        )

    return _to_dict(product)


# ── DELETE /products/{id} ─────────────────────────────────────────────────────


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Eliminar producto",
    description="Soft delete: marca el producto como DELETED. Deja de aparecer en listados y búsquedas.",
    responses={404: _ERROR_RESPONSES[404]},
)
def delete_product(
    product_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    x_correlation_id: Optional[str] = Header(None),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.status != "DELETED")
        .first()
    )

    if not product:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "PRODUCT_NOT_FOUND", "Product not found", 404, x_correlation_id
            ),
        )

    old_status = product.status
    product.status = "DELETED"
    db.commit()

    background_tasks.add_task(
        publish_product_status_changed,
        product_id=product.id,
        sku=product.sku,
        old_status=old_status,
        new_status="DELETED",
        correlation_id=x_correlation_id,
    )

    return Response(status_code=204)
