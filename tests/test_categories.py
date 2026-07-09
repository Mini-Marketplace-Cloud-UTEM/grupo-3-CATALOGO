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

CATEGORY_NAME = f"Test-Cat-{uuid.uuid4().hex[:6].upper()}"
CREATED_ID = None


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    yield
    if CREATED_ID:
        client.delete(f"/categories/{CREATED_ID}", headers=HEADERS)


# ── GET /categories ───────────────────────────────────────────────────────────

def test_list_categories():
    res = client.get("/categories?page=1&size=10", headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "pagination" in body
    assert isinstance(body["data"], list)
    p = body["pagination"]
    assert all(k in p for k in ["page", "pageSize", "total", "totalPages", "hasNext", "hasPrev"])


def test_list_categories_invalid_page():
    res = client.get("/categories?page=0", headers=HEADERS)
    assert res.status_code == 422


def test_list_categories_has_seed_data():
    res = client.get("/categories?size=100", headers=HEADERS)
    assert res.status_code == 200
    names = [c["name"] for c in res.json()["data"]]
    assert "Herramientas" in names
    assert "Electrónica" in names


# ── POST /categories ──────────────────────────────────────────────────────────

def test_create_category():
    global CREATED_ID
    res = client.post(
        "/categories",
        json={"name": CATEGORY_NAME},
        headers={**HEADERS, **IDEMPOTENCY},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == CATEGORY_NAME
    assert "id" in data
    CREATED_ID = data["id"]


def test_create_category_duplicate_name():
    res = client.post(
        "/categories",
        json={"name": CATEGORY_NAME},
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert res.status_code == 409
    assert res.json()["code"] == "DUPLICATE_CATEGORY"


# ── GET /categories/{id} ─────────────────────────────────────────────────────

def test_get_category():
    assert CREATED_ID is not None, "test_create_category debe correr primero"
    res = client.get(f"/categories/{CREATED_ID}", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == CREATED_ID
    assert data["name"] == CATEGORY_NAME


def test_get_category_not_found():
    res = client.get(f"/categories/{uuid.uuid4()}", headers=HEADERS)
    assert res.status_code == 404
    assert res.json()["code"] == "CATEGORY_NOT_FOUND"


# ── PUT /categories/{id} ─────────────────────────────────────────────────────

def test_update_category():
    assert CREATED_ID is not None, "test_create_category debe correr primero"
    new_name = f"{CATEGORY_NAME}-UPD"
    res = client.put(
        f"/categories/{CREATED_ID}",
        json={"name": new_name},
        headers={**HEADERS, **IDEMPOTENCY},
    )
    assert res.status_code == 200
    assert res.json()["name"] == new_name


def test_update_category_not_found():
    res = client.put(
        f"/categories/{uuid.uuid4()}",
        json={"name": "No existe"},
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "CATEGORY_NOT_FOUND"


def test_update_category_duplicate_name():
    assert CREATED_ID is not None, "test_create_category debe correr primero"
    res = client.put(
        f"/categories/{CREATED_ID}",
        json={"name": "Herramientas"},
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert res.status_code == 409
    assert res.json()["code"] == "DUPLICATE_CATEGORY"


# ── DELETE /categories/{id} ───────────────────────────────────────────────────

def test_delete_category_with_products():
    # La categoría "Herramientas" tiene productos en el seed — no debe poder eliminarse
    res = client.get("/categories?size=100", headers=HEADERS)
    herramientas = next(
        (c for c in res.json()["data"] if c["name"] == "Herramientas"), None
    )
    assert herramientas is not None
    del_res = client.delete(f"/categories/{herramientas['id']}", headers=HEADERS)
    assert del_res.status_code == 409
    assert del_res.json()["code"] == "CATEGORY_HAS_PRODUCTS"


def test_delete_category():
    assert CREATED_ID is not None, "test_create_category debe correr primero"
    res = client.delete(f"/categories/{CREATED_ID}", headers=HEADERS)
    assert res.status_code == 204


def test_delete_category_not_found():
    res = client.delete(f"/categories/{uuid.uuid4()}", headers=HEADERS)
    assert res.status_code == 404
    assert res.json()["code"] == "CATEGORY_NOT_FOUND"
