# Catalog Service — Grupo 3

Microservicio REST dueño del catálogo de productos del Mini Marketplace Cloud.  
Administra productos, categorías, precios y stock visible.

- **Stack:** Python 3.11 · FastAPI · SQLAlchemy · PostgreSQL (Supabase)
- **Deploy:** Render
- **URL:** https://grupo-3-catalogo.onrender.com
- **Swagger:** https://grupo-3-catalogo.onrender.com/docs
- **Contrato OpenAPI:** archivo [`contrato`](contrato)

---

## Arquitectura

### C1 — Contexto del sistema

```mermaid
graph TD
    U([Usuario / Cliente]) -->|Busca y navega catálogo| G1[Grupo 1\nFrontend]
    G1 -->|GET /products\nGET /products/search| CAT[🗂️ Catalog Service\nGrupo 3]
    G4[Grupo 4\nCarro] -->|GET /products/:id| CAT
    G6[Grupo 6\nInventario] -->|PUT /products/:id\nactualiza stockVisible| CAT
    G10[Grupo 10\nReportería] -->|GET /products| CAT
    G2[Grupo 2\nAuth] -->|JWT token\nvalidación admin| CAT
    CAT -->|SQL| DB[(Supabase\nPostgreSQL)]
    CAT -->|Storage| ST[(Supabase\nStorage)]
```

### C2 — Contenedores internos

```mermaid
graph TD
    subgraph "Catalog Service — Render"
        API[FastAPI App\napp/main.py]
        PR[Products Router\napp/routes/products.py]
        CR[Categories Router\napp/routes/categories.py]
        UR[Uploads Router\napp/routes/uploads.py]
        ORM[SQLAlchemy ORM\napp/models.py]
        API --> PR
        API --> CR
        API --> UR
        PR --> ORM
        CR --> ORM
    end
    ORM -->|psycopg2| DB[(PostgreSQL\nSupabase)]
    UR -->|supabase-py| ST[(Storage\nSupabase)]
```

---

## Integraciones

| Grupo | Servicio | Qué consume |
|-------|----------|-------------|
| Grupo 1 | Frontend | `GET /products` · `GET /products/search` |
| Grupo 4 | Carro | `GET /products/{id}` |
| Grupo 6 | Inventario | `PUT /products/{id}` (actualiza `stock_visible`) |
| Grupo 10 | Reportería | `GET /products` |

---

## Endpoints

### Productos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/products` | Listar productos paginados |
| `GET` | `/products/{id}` | Obtener producto por ID |
| `GET` | `/products/search?q=...` | Buscar por texto |
| `POST` | `/products` | Crear producto |
| `PUT` | `/products/{id}` | Actualizar producto |
| `DELETE` | `/products/{id}` | Eliminar producto (soft delete) |

### Categorías

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/categories` | Listar categorías paginadas |
| `GET` | `/categories/{id}` | Obtener categoría por ID |
| `POST` | `/categories` | Crear categoría |
| `PUT` | `/categories/{id}` | Actualizar nombre de categoría |
| `DELETE` | `/categories/{id}` | Eliminar categoría (sin productos activos) |

### Otros

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/uploads` | Subir imagen (retorna URL) |
| `GET` | `/health` | Estado del servicio |

### Headers estándar

```
X-Request-Id: <uuid>
X-Correlation-Id: <uuid>
X-Consumer: <nombre-del-servicio-que-llama>
Idempotency-Key: <uuid>    ← requerido solo en POST y PUT
```

---

## Ejemplos

### GET /products

```http
GET /products?page=1&size=20
X-Consumer: frontend-service
```

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Taladro Eléctrico 700W",
      "description": "Taladro percutor profesional",
      "price": 49990,
      "stockVisible": 15,
      "categoryId": "550e8400-e29b-41d4-a716-446655440001",
      "categoryName": "Herramientas",
      "sku": "TAL-700W-PRO",
      "status": "ACTIVE",
      "images": ["https://cdn.marketplace.cl/products/taladro.jpg"],
      "createdAt": "2026-05-01T10:00:00Z",
      "updatedAt": "2026-05-20T08:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 1,
    "totalPages": 1,
    "hasNext": false,
    "hasPrev": false
  }
}
```

### GET /products/search

```http
GET /products/search?q=taladro&page=1&size=10
X-Consumer: frontend-service
```

| Parámetro | Tipo | Requerido | Default |
|-----------|------|-----------|---------|
| `q` | string (mín. 2 chars) | Sí | — |
| `categoryId` | uuid | No | — |
| `status` | `ACTIVE` · `INACTIVE` · `DELETED` | No | excluye `DELETED` |
| `page` | integer | No | 1 |
| `size` | integer (máx. 100) | No | 10 |

Respuesta: misma estructura paginada que `GET /products`.

### GET /products/{id}

```http
GET /products/550e8400-e29b-41d4-a716-446655440000
X-Consumer: cart-service
```

**404 — producto no encontrado:**
```json
{
  "timestamp": "2026-06-27T10:00:00Z",
  "status": 404,
  "code": "PRODUCT_NOT_FOUND",
  "message": "Product not found",
  "correlationId": "abc-123"
}
```

### POST /products

```http
POST /products
Content-Type: application/json
Idempotency-Key: 9e1a9b0f-5e56-40bd-9b0f-0f2e2c8c0101
X-Consumer: admin-panel
```

```json
{
  "name": "Sierra Circular 1200W",
  "description": "Sierra circular portátil con disco incluido",
  "price": 69990,
  "stockVisible": 8,
  "categoryId": "550e8400-e29b-41d4-a716-446655440001",
  "sku": "SIE-1200W-PR",
  "images": ["https://cdn.marketplace.cl/products/sierra.jpg"]
}
```

**201 — creado** · **409 — SKU duplicado** · **400 — categoría no existe**

### PUT /products/{id}

Solo se modifican los campos enviados. El resto queda igual.

```http
PUT /products/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json
Idempotency-Key: 9e1a9b0f-5e56-40bd-9b0f-0f2e2c8c0102
X-Consumer: inventory-service
```

```json
{ "stockVisible": 6 }
```

### DELETE /products/{id}

```http
DELETE /products/550e8400-e29b-41d4-a716-446655440000
X-Consumer: admin-panel
```

Soft delete: el producto queda con `status: DELETED` y deja de aparecer en listados y búsquedas.

**204 — eliminado** · **404 — no existe**

### GET /categories

```http
GET /categories?page=1&size=20
X-Consumer: frontend-service
```

```json
{
  "data": [
    { "id": "550e8400-e29b-41d4-a716-446655440002", "name": "Electrónica" },
    { "id": "550e8400-e29b-41d4-a716-446655440001", "name": "Herramientas" }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 4,
    "totalPages": 1,
    "hasNext": false,
    "hasPrev": false
  }
}
```

### POST /categories

```http
POST /categories
Content-Type: application/json
Idempotency-Key: 9e1a9b0f-5e56-40bd-9b0f-0f2e2c8c0201
X-Consumer: admin-panel
```

```json
{ "name": "Deportes" }
```

**201 — creada** · **409 — nombre duplicado**

### PUT /categories/{id}

Solo se modifica el nombre. El resto de productos asociados no se afecta.

```http
PUT /categories/550e8400-e29b-41d4-a716-446655440001
Content-Type: application/json
Idempotency-Key: 9e1a9b0f-5e56-40bd-9b0f-0f2e2c8c0202
X-Consumer: admin-panel
```

```json
{ "name": "Herramientas y Maquinaria" }
```

**200 — actualizada** · **404 — no existe** · **409 — nombre duplicado**

### DELETE /categories/{id}

```http
DELETE /categories/{id}
X-Consumer: admin-panel
```

**204 — eliminada** · **404 — no existe** · **409 — tiene productos activos**

---

### POST /uploads

Sube una imagen y retorna la URL pública para usar en `POST /products`.

```http
POST /uploads
Content-Type: multipart/form-data
X-Consumer: admin-panel

file: <archivo .jpg/.png/.webp — máx. 5MB>
```

```json
{ "url": "https://[proyecto].supabase.co/storage/v1/object/public/products/products/uuid.jpg" }
```

---

## Errores estándar

Todos los errores siguen el mismo formato:

```json
{
  "timestamp": "2026-05-25T10:00:00Z",
  "status": 409,
  "code": "DUPLICATE_SKU",
  "message": "SKU already exists",
  "correlationId": "abc-123"
}
```

| Status | Code | Cuándo ocurre |
|--------|------|---------------|
| 400 | `INVALID_REQUEST` | Parámetros inválidos o categoría inexistente |
| 404 | `PRODUCT_NOT_FOUND` | Producto no existe o fue eliminado |
| 404 | `CATEGORY_NOT_FOUND` | Categoría no existe |
| 409 | `DUPLICATE_SKU` | SKU ya registrado |
| 409 | `DUPLICATE_CATEGORY` | Nombre de categoría ya existe |
| 409 | `CATEGORY_HAS_PRODUCTS` | No se puede eliminar categoría con productos activos |
| 500 | `INTERNAL_SERVER_ERROR` | Error inesperado del servidor |
| 502 | `STORAGE_ERROR` | Fallo al subir imagen a Supabase Storage |

---

## Modelo de datos

```
products
├── id             UUID  PK
├── name           TEXT  NOT NULL
├── description    TEXT
├── price          BIGINT  NOT NULL  -- entero en CLP (ej: 49990)
├── stock_visible  INTEGER  DEFAULT 0
├── category_id    UUID  FK → categories.id
├── sku            TEXT  UNIQUE NOT NULL
├── status         TEXT  DEFAULT 'ACTIVE'   -- ACTIVE | INACTIVE | DELETED
├── images         TEXT[]
├── created_at     TIMESTAMPTZ  DEFAULT NOW()
└── updated_at     TIMESTAMPTZ  DEFAULT NOW()

categories
├── id   UUID  PK
└── name TEXT  UNIQUE NOT NULL
```

### Productos demo para pruebas de integración

Productos con UUIDs fijos disponibles en la nube para que otros grupos puedan probar sin crear datos:

| UUID | Nombre | Status | Uso sugerido |
|------|--------|--------|-------------|
| `550e8400-e29b-41d4-a716-446655440000` | Taladro Eléctrico 700W | `ACTIVE` | Flujo normal — agregar al carrito, consultar precio |
| `660e8400-e29b-41d4-a716-446655440001` | Sierra Circular 1200W | `ACTIVE` | Segundo producto activo para pruebas de listado |
| `880e8400-e29b-41d4-a716-446655440003` | Lijadora Orbital 300W | `INACTIVE` | Probar rechazo en carrito (producto no disponible) |
| `00000000-0000-0000-0000-000000000000` | — | No existe | Probar respuesta 404 `PRODUCT_NOT_FOUND` |

### Categorías disponibles (cargadas con `seed.sql`):

| ID | Nombre |
|----|--------|
| `550e8400-e29b-41d4-a716-446655440001` | Herramientas |
| `550e8400-e29b-41d4-a716-446655440002` | Electrónica |
| `550e8400-e29b-41d4-a716-446655440003` | Hogar |
| `550e8400-e29b-41d4-a716-446655440004` | Jardín |

---

## Instalación local

**Requisitos:** Python 3.11+ · Cuenta gratuita en [supabase.com](https://supabase.com)

### Paso 1 — Clonar e instalar

```bash
git clone https://github.com/<org>/grupo-3-CATALOGO.git
cd grupo-3-CATALOGO

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### Paso 2 — Configurar Supabase

Crear un proyecto en [supabase.com](https://supabase.com) y obtener:

| Variable | Dónde encontrarla |
|----------|------------------|
| `DATABASE_URL` | Project Settings → Database → **Connection Pooling → Transaction** → copiar URI (puerto 6543) |
| `SUPABASE_URL` | Project Settings → API → **Project URL** |
| `SUPABASE_KEY` | Project Settings → API → **anon public** |

```bash
cp .env.example .env
# Abrir .env y pegar los tres valores
```

### Paso 3 — Crear tablas y cargar datos iniciales

En Supabase → **SQL Editor**, ejecutar en orden:

1. [`schema.sql`](schema.sql) — crea las tablas, índices y constraints
2. [`seed.sql`](seed.sql) — inserta categorías y productos de ejemplo

### Paso 4 — (Opcional) Bucket para imágenes

Para usar `POST /uploads`:
1. Supabase → **Storage** → **New bucket**
2. Nombre: `products` · marcar **Public bucket** → crear

### Paso 5 — Levantar el servidor

```bash
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

> Si falta alguna variable de entorno, el servidor muestra un mensaje claro indicando cuál falta.

---

## Variables de entorno

```env
# Supabase > Project Settings > Database > Connection Pooling > Transaction > URI
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require

# Supabase > Project Settings > API
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_KEY=[anon-public-key]
```

---

## Estructura del repositorio

```
grupo-3-CATALOGO/
├── .github/
│   └── workflows/
│       ├── ci.yml        # Lint + tests + cobertura
│       ├── security.yml  # CVEs + análisis de seguridad
│       └── deploy.yml    # Deploy automático a Render
├── app/
│   ├── main.py           # FastAPI app, CORS, tags Swagger
│   ├── database.py       # Conexión SQLAlchemy → Supabase
│   ├── models.py         # Tablas Product y Category
│   ├── schemas.py        # Esquemas Pydantic request/response
│   └── routes/
│       ├── products.py   # Endpoints del catálogo de productos
│       ├── categories.py # Endpoints de categorías
│       └── uploads.py    # Endpoint de subida de imágenes
├── tests/
│   ├── test_products.py  # Tests funcionales de productos
│   └── test_categories.py # Tests funcionales de categorías
├── contrato              # Especificación OpenAPI 3.0.3
├── index.html            # Mini frontend de prueba
├── schema.sql            # DDL: CREATE TABLE + índices + constraints
├── seed.sql              # Datos iniciales para Supabase
├── requirements.txt      # Dependencias Python
├── Procfile              # Comando de inicio para Render
├── .env.example          # Plantilla de variables de entorno
└── README.md
```

---

## Deploy en Render

1. Subir el código a GitHub (sin el `.env`)
2. Ir a [render.com](https://render.com) → **New Web Service** → conectar el repo
3. Configurar:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Agregar las 3 variables de entorno (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`)
5. Copiar el **Deploy Hook URL** desde Render → Settings → Deploy Hook y agregarlo como secret `RENDER_DEPLOY_HOOK_URL` en GitHub

Cada push a `main` dispara el deploy automáticamente vía GitHub Actions.

---

## CI/CD

El repositorio cuenta con 3 pipelines en `.github/workflows/`:

| Workflow | Trigger | Qué hace |
|----------|---------|----------|
| `ci.yml` | Push/PR en todas las ramas | Lint (ruff) + formato + tests + cobertura mínima 60% |
| `security.yml` | Push/PR a `main` y `develop` | Escaneo de CVEs en dependencias (pip-audit) + análisis de código inseguro (bandit) |
| `deploy.yml` | Push a `main` | Deploy automático a Render vía Deploy Hook |

### Secrets requeridos en GitHub

| Secret | Descripción |
|--------|-------------|
| `DATABASE_URL` | URI de conexión a Supabase (Transaction pooler) |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_KEY` | Clave anon pública de Supabase |
| `RENDER_DEPLOY_HOOK_URL` | Deploy Hook de Render para trigger automático |

---

## Mock con Prism

Para que otros grupos puedan integrar mientras el servicio está en desarrollo:

```bash
npm install -g @stoplight/prism-cli
prism mock contrato
# disponible en http://127.0.0.1:4010
```
