from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(BigInteger, nullable=False)
    stock_visible = Column(Integer, nullable=False, default=0)
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True
    )
    sku = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    size = Column(String, nullable=False, default="M")
    images = Column(ARRAY(String), default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category = relationship("Category", back_populates="products")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key = Column(String, primary_key=True)
    endpoint = Column(String, primary_key=True)
    request_hash = Column(String, nullable=True)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
