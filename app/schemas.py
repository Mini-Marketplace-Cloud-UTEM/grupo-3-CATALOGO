from typing import Annotated, Optional, List, Literal
from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

SizeEnum = Literal["XS", "S", "M", "L", "XL", "XXL"]


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: Optional[str] = None
    price: Annotated[int, Field(gt=0)]
    category_id: Annotated[uuid.UUID, Field(alias="categoryId")]
    sku: Optional[str] = None
    size: SizeEnum
    images: List[str] = Field(default_factory=list)


class UpdateProductRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    description: Optional[str] = None
    price: Annotated[Optional[int], Field(gt=0)] = None
    stock_visible: Annotated[Optional[int], Field(alias="stockVisible", ge=0)] = None
    status: Optional[Literal["ACTIVE", "INACTIVE", "DELETED"]] = None
    size: Optional[SizeEnum] = None
    images: Optional[List[str]] = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: int
    stockVisible: int
    categoryId: uuid.UUID
    categoryName: Optional[str]
    sku: str
    status: Literal["ACTIVE", "INACTIVE", "DELETED"]
    size: SizeEnum
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
    timestamp: datetime
    status: int
    code: str
    message: str
    correlationId: Optional[str] = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str


class CreateCategoryRequest(BaseModel):
    name: str


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = None


class CategoryListResponse(BaseModel):
    data: List[CategoryResponse]
    pagination: PaginationMeta
