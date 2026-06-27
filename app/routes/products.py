import math
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Category, Product
from app.schemas import (
    CreateProductRequest,
    ProductListResponse,
    ProductResponse,
    UpdateProductRequest,
)

router = APIRouter(prefix="/products", tags=["Products"])

_ERROR_RESPONSES = {
    400: {"description": "Solicitud inválida",    "content": {"application/json": {"example": {"code": "INVALID_REQUEST",    "message": "Invalid input",      "correlationId": "abc-123"}}}},
    404: {"description": "Producto no encontrado","content": {"application/json": {"example": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found",  "correlationId": "abc-123"}}}},
    409: {"description": "SKU duplicado",         "content": {"application/json": {"example": {"code": "DUPLICATE_SKU",     "message": "SKU already exists", "correlationId": "abc-123"}}}},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _error(code: str, message: str, correlation_id: Optional[str] = None) -> dict:
    return {
        "code": code,
        "message": message,
        "correlationId": correlation_id,
    }


def _to_dict(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "stockVisible": product.stock_visible,
        "categoryId": product.category_id,
        "categoryName": product.category.name if product.category else None,
        "sku": product.sku,
        "status": product.status,
        "images": product.images or [],
        "createdAt": product.created_at,
        "updatedAt": product.updated_at,
    }


def _generate_sku(name: str, db: Session) -> str:
    prefix = ''.join(c for c in name.upper() if c.isalpha())[:3]
    match = re.search(r'(\d+)\s*[wW]', name)
    mid = f"{match.group(1)}W" if match else f"{prefix}X"
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

@router.get("", response_model=ProductListResponse, summary="Listar productos paginados",
    description="Retorna todos los productos activos del catálogo con paginación.",
    responses={400: _ERROR_RESPONSES[400]})
def list_products(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Productos por página (máx. 100)"),
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
    items, pagination = _paginate(query, page, size)
    return {"data": [_to_dict(p) for p in items], "pagination": pagination}


# ── GET /products/search ──────────────────────────────────────────────────────
# OJO: debe ir ANTES de /{product_id} para que FastAPI no confunda
# la palabra "search" con un UUID.

@router.get("/search", response_model=ProductListResponse, summary="Buscar productos",
    description="Busca por texto en nombre y descripción. Parámetro `q` obligatorio (mín. 2 caracteres).",
    responses={400: _ERROR_RESPONSES[400]})
def search_products(
    q: str = Query(..., min_length=2, description="Texto a buscar"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filtrar por categoría"),
    status: Optional[str] = Query(None, description="Filtrar por estado: ACTIVE, INACTIVE, DELETED"),
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

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status:
        query = query.filter(Product.status == status)
    else:
        query = query.filter(Product.status != "DELETED")

    items, pagination = _paginate(query, page, size)
    return {"data": [_to_dict(p) for p in items], "pagination": pagination}


# ── GET /products/{id} ────────────────────────────────────────────────────────

@router.get("/{product_id}", response_model=ProductResponse, summary="Obtener producto por ID",
    description="Retorna un producto por UUID. Devuelve 404 si no existe o fue eliminado.",
    responses={404: _ERROR_RESPONSES[404]})
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
        return JSONResponse(status_code=404,
            content=_error("PRODUCT_NOT_FOUND", "Product not found", x_correlation_id))

    return _to_dict(product)


# ── POST /products ────────────────────────────────────────────────────────────

@router.post("", response_model=ProductResponse, status_code=201, summary="Crear producto",
    description="Crea un producto. El SKU debe ser único. Sube la imagen primero con `POST /uploads`.",
    responses={400: _ERROR_RESPONSES[400], 409: _ERROR_RESPONSES[409]})
def create_product(
    body: CreateProductRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, description="UUID para evitar duplicados en reintentos"),
    x_correlation_id: Optional[str] = Header(None),
):
    if not db.query(Category).filter(Category.id == body.category_id).first():
        return JSONResponse(status_code=400,
            content=_error("INVALID_REQUEST", "Category not found", x_correlation_id))

    sku = body.sku or _generate_sku(body.name, db)

    if db.query(Product).filter(Product.sku == sku).first():
        return JSONResponse(status_code=409,
            content=_error("DUPLICATE_SKU", "SKU already exists", x_correlation_id))

    product = Product(**body.model_dump(exclude={"sku"}), sku=sku, status="ACTIVE")
    db.add(product)
    db.commit()
    db.refresh(product)

    return _to_dict(product)


# ── PUT /products/{id} ────────────────────────────────────────────────────────

@router.put("/{product_id}", response_model=ProductResponse, summary="Actualizar producto",
    description="Actualiza solo los campos enviados. El Grupo 6 usa esto para actualizar `stockVisible`.",
    responses={400: _ERROR_RESPONSES[400], 404: _ERROR_RESPONSES[404]})
def update_product(
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None),
    x_correlation_id: Optional[str] = Header(None),
):
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id, Product.status != "DELETED")
        .first()
    )

    if not product:
        return JSONResponse(status_code=404,
            content=_error("PRODUCT_NOT_FOUND", "Product not found", x_correlation_id))

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return _to_dict(product)
