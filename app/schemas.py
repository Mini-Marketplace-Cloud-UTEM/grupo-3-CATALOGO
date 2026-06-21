from typing import Annotated, Optional, List
from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: Optional[str] = None
    price: float
    stock_visible: Annotated[int, Field(alias="stockVisible")] = 0
    category_id: Annotated[uuid.UUID, Field(alias="categoryId")]
    sku: str
    images: Optional[List[str]] = []


class UpdateProductRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_visible: Annotated[Optional[int], Field(alias="stockVisible")] = None
    status: Optional[str] = None
    images: Optional[List[str]] = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: float
    stockVisible: int
    categoryId: uuid.UUID
    categoryName: Optional[str]
    sku: str
    status: str
    images: Optional[List[str]]
    createdAt: datetime
    updatedAt: datetime


class PaginationMeta(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int
    hasNext: bool
    hasPrev: bool


class ProductListResponse(BaseModel):
    data: List[ProductResponse]
    pagination: PaginationMeta


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlationId: Optional[str] = None
