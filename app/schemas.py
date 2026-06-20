from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class CreateProductRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_visible: int = 0
    category_id: uuid.UUID
    sku: str
    images: Optional[List[str]] = []


class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_visible: Optional[int] = None
    status: Optional[str] = None
    images: Optional[List[str]] = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: float
    stock_visible: int
    category_id: uuid.UUID
    category_name: Optional[str]
    sku: str
    status: str
    images: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    page: int
    size: int
    total: int
    totalPages: int
    hasNext: bool
    hasPrev: bool


class ProductListResponse(BaseModel):
    data: List[ProductResponse]
    pagination: PaginationMeta


class ErrorResponse(BaseModel):
    timestamp: str
    status: int
    code: str
    message: str
    correlationId: Optional[str] = None
