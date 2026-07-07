import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.idempotency import get_cached_response, store_response
from app.models import Category, Product
from app.schemas import (
    CategoryListResponse,
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)
from app.utils import error_response

router = APIRouter(prefix="/categories", tags=["Categories"])

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
        "description": "Categoría no encontrada",
        "content": {
            "application/json": {
                "example": {
                    "timestamp": "2026-05-25T10:00:00Z",
                    "status": 404,
                    "code": "CATEGORY_NOT_FOUND",
                    "message": "Category not found",
                    "correlationId": "abc-123",
                }
            }
        },
    },
    409: {
        "description": "Nombre duplicado",
        "content": {
            "application/json": {
                "example": {
                    "timestamp": "2026-05-25T10:00:00Z",
                    "status": 409,
                    "code": "DUPLICATE_CATEGORY",
                    "message": "Category name already exists",
                    "correlationId": "abc-123",
                }
            }
        },
    },
    422: {
        "description": "Categoría con productos",
        "content": {
            "application/json": {
                "example": {
                    "timestamp": "2026-05-25T10:00:00Z",
                    "status": 409,
                    "code": "CATEGORY_HAS_PRODUCTS",
                    "message": "Cannot delete category with active products",
                    "correlationId": "abc-123",
                }
            }
        },
    },
}


def _to_dict(category: Category) -> dict:
    return {"id": category.id, "name": category.name}


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


# ── GET /categories ───────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=CategoryListResponse,
    summary="Listar categorías paginadas",
    description="Retorna todas las categorías disponibles en el catálogo.",
    responses={400: _ERROR_RESPONSES[400]},
)
def list_categories(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Categorías por página (máx. 100)"),
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(None),
):
    query = db.query(Category).order_by(Category.name)
    items, pagination = _paginate(query, page, size)
    return {"data": [_to_dict(c) for c in items], "pagination": pagination}


# ── GET /categories/{id} ─────────────────────────────────────────────────────


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Obtener categoría por ID",
    description="Retorna una categoría por su UUID.",
    responses={404: _ERROR_RESPONSES[404]},
)
def get_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(None),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "CATEGORY_NOT_FOUND", "Category not found", 404, x_correlation_id
            ),
        )
    return _to_dict(category)


# ── POST /categories ──────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=201,
    summary="Crear categoría",
    description="Crea una nueva categoría. El nombre debe ser único.",
    responses={409: _ERROR_RESPONSES[409]},
)
def create_category(
    body: CreateCategoryRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    idempotency_key: Optional[str] = Header(
        None, description="UUID para evitar duplicados en reintentos"
    ),
    x_correlation_id: Optional[str] = Header(None),
):
    endpoint = "POST /categories"

    if not idempotency_key:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "INVALID_REQUEST", "Idempotency-Key header is required", 400, x_correlation_id
            ),
        )

    cached = get_cached_response(db, idempotency_key, endpoint)
    if cached:
        status, body_cached = cached
        return JSONResponse(status_code=status, content=body_cached)

    if db.query(Category).filter(Category.name == body.name).first():
        content = error_response(
            "DUPLICATE_CATEGORY",
            "Category name already exists",
            409,
            x_correlation_id,
        )
        store_response(db, idempotency_key, endpoint, 409, content)
        return JSONResponse(status_code=409, content=content)

    category = Category(name=body.name)
    db.add(category)
    db.commit()
    db.refresh(category)

    content = jsonable_encoder(_to_dict(category))
    store_response(db, idempotency_key, endpoint, 201, content)
    return content


# ── PUT /categories/{id} ─────────────────────────────────────────────────────


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Actualizar categoría",
    description="Actualiza el nombre de una categoría existente.",
    responses={404: _ERROR_RESPONSES[404], 409: _ERROR_RESPONSES[409]},
)
def update_category(
    category_id: uuid.UUID,
    body: UpdateCategoryRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    idempotency_key: Optional[str] = Header(None),
    x_correlation_id: Optional[str] = Header(None),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "CATEGORY_NOT_FOUND", "Category not found", 404, x_correlation_id
            ),
        )

    if body.name is not None:
        conflict = (
            db.query(Category)
            .filter(Category.name == body.name, Category.id != category_id)
            .first()
        )
        if conflict:
            return JSONResponse(
                status_code=409,
                content=error_response(
                    "DUPLICATE_CATEGORY",
                    "Category name already exists",
                    409,
                    x_correlation_id,
                ),
            )
        category.name = body.name

    db.commit()
    db.refresh(category)
    return _to_dict(category)


# ── DELETE /categories/{id} ───────────────────────────────────────────────────


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Eliminar categoría",
    description="Elimina una categoría. Falla si tiene productos activos asociados.",
    responses={
        404: _ERROR_RESPONSES[404],
        409: _ERROR_RESPONSES[409],
        422: _ERROR_RESPONSES[422],
    },
)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    x_correlation_id: Optional[str] = Header(None),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "CATEGORY_NOT_FOUND", "Category not found", 404, x_correlation_id
            ),
        )

    has_products = (
        db.query(Product)
        .filter(Product.category_id == category_id, Product.status != "DELETED")
        .first()
    )
    if has_products:
        return JSONResponse(
            status_code=409,
            content=error_response(
                "CATEGORY_HAS_PRODUCTS",
                "Cannot delete a category that has active products",
                409,
                x_correlation_id,
            ),
        )

    db.delete(category)
    db.commit()
    return Response(status_code=204)
