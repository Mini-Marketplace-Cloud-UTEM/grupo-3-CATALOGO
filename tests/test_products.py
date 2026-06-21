import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

HEADERS = {
    "X-Consumer": "test-suite",
    "X-Correlation-Id": str(uuid.uuid4()),
}

IDEMPOTENCY = {"Idempotency-Key": str(uuid.uuid4())}

SKU_TEST = f"TEST-{uuid.uuid4().hex[:8].upper()}"
CREATED_ID = None


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    yield
    if CREATED_ID:
        client.put(
            f"/products/{CREATED_ID}",
            json={"status": "DELETED"},
            headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
        )


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── GET /products ─────────────────────────────────────────────────────────────

def test_list_products():
    res = client.get("/products?page=1&size=5", headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "pagination" in body
    assert isinstance(body["data"], list)
    p = body["pagination"]
    assert all(k in p for k in ["page", "size", "total", "totalPages", "hasNext", "hasPrev"])


def test_list_products_invalid_page():
    res = client.get("/products?page=0", headers=HEADERS)
    assert res.status_code == 422


# ── GET /products/search ──────────────────────────────────────────────────────

def test_search_products():
    res = client.get("/products/search?q=taladro", headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "pagination" in body


def test_search_too_short():
    res = client.get("/products/search?q=a", headers=HEADERS)
    assert res.status_code == 422


def test_search_missing_q():
    res = client.get("/products/search", headers=HEADERS)
    assert res.status_code == 422


# ── POST /products ────────────────────────────────────────────────────────────

def test_create_product():
    global CREATED_ID
    body = {
        "name": "Producto Test CI",
        "description": "Creado por el test suite",
        "price": 9990,
        "stock_visible": 5,
        "category_id": "550e8400-e29b-41d4-a716-446655440001",
        "sku": SKU_TEST,
    }
    res = client.post("/products", json=body, headers={**HEADERS, **IDEMPOTENCY})
    assert res.status_code == 201
    data = res.json()
    assert data["sku"] == SKU_TEST
    assert data["status"] == "ACTIVE"
    CREATED_ID = data["id"]


def test_create_product_duplicate_sku():
    body = {
        "name": "Duplicado",
        "price": 1000,
        "category_id": "550e8400-e29b-41d4-a716-446655440001",
        "sku": SKU_TEST,
    }
    res = client.post("/products", json=body, headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())})
    assert res.status_code == 409
    assert res.json()["code"] == "DUPLICATE_SKU"


def test_create_product_invalid_category():
    body = {
        "name": "Sin categoría",
        "price": 1000,
        "category_id": str(uuid.uuid4()),
        "sku": f"NO-CAT-{uuid.uuid4().hex[:6].upper()}",
    }
    res = client.post("/products", json=body, headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())})
    assert res.status_code == 400


# ── GET /products/{id} ────────────────────────────────────────────────────────

def test_get_product():
    assert CREATED_ID is not None, "test_create_product debe correr primero"
    res = client.get(f"/products/{CREATED_ID}", headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["id"] == CREATED_ID


def test_get_product_not_found():
    res = client.get(f"/products/{uuid.uuid4()}", headers=HEADERS)
    assert res.status_code == 404
    assert res.json()["code"] == "PRODUCT_NOT_FOUND"


# ── PUT /products/{id} ────────────────────────────────────────────────────────

def test_update_product():
    assert CREATED_ID is not None, "test_create_product debe correr primero"
    body = {"price": 11990, "stock_visible": 3}
    res = client.put(f"/products/{CREATED_ID}", json=body, headers={**HEADERS, **IDEMPOTENCY})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 11990
    assert data["stock_visible"] == 3


def test_update_product_not_found():
    res = client.put(f"/products/{uuid.uuid4()}", json={"price": 1000},
                     headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())})
    assert res.status_code == 404
