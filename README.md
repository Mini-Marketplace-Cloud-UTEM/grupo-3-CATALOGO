# Catalog Service — Grupo 3

Microservicio REST dueño del catálogo de productos del Mini Marketplace Cloud.  
Administra productos, categorías, precios y stock visible.

- **Stack:** Python 3.11 · FastAPI · SQLAlchemy · PostgreSQL (Supabase)
- **Deploy:** Render
- **Swagger:** `<URL>/docs`
- **Contrato OpenAPI:** archivo [`contrato`](contrato)

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

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/products` | Listar productos paginados |
| `GET` | `/products/{id}` | Obtener producto por ID |
| `GET` | `/products/search?q=...` | Buscar por texto |
| `POST` | `/products` | Crear producto |
| `PUT` | `/products/{id}` | Actualizar producto |
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
      "stock_visible": 15,
      "category_id": "550e8400-e29b-41d4-a716-446655440001",
      "category_name": "Herramientas",
      "sku": "TAL-700W-PRO",
      "status": "ACTIVE",
      "images": ["https://cdn.marketplace.cl/products/taladro.jpg"],
      "created_at": "2026-05-01T10:00:00Z",
      "updated_at": "2026-05-20T08:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
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
| `category_id` | uuid | No | — |
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
  "timestamp": "2026-06-20T10:00:00Z",
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
  "stock_visible": 8,
  "category_id": "550e8400-e29b-41d4-a716-446655440001",
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
{ "stock_visible": 6 }
```

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
  "timestamp": "2026-06-20T10:00:00Z",
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
| 409 | `DUPLICATE_SKU` | SKU ya registrado |
| 500 | `INTERNAL_SERVER_ERROR` | Error inesperado del servidor |

---

## Modelo de datos

```
products
├── id             UUID  PK
├── name           TEXT  NOT NULL
├── description    TEXT
├── price          NUMERIC(10,2)  NOT NULL
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

Categorías disponibles (cargadas con `seed.sql`):

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

### Paso 3 — Cargar datos iniciales

En Supabase → **SQL Editor**, ejecutar el contenido de [`seed.sql`](seed.sql).  
Esto crea las tablas `categories` y `products` con datos de ejemplo.

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
├── app/
│   ├── main.py           # FastAPI app, CORS, tags Swagger
│   ├── database.py       # Conexión SQLAlchemy → Supabase
│   ├── models.py         # Tablas Product y Category
│   ├── schemas.py        # Esquemas Pydantic request/response
│   └── routes/
│       ├── products.py   # Endpoints del catálogo
│       └── uploads.py    # Endpoint de subida de imágenes
├── contrato              # Especificación OpenAPI 3.0.3
├── index.html            # Mini frontend de prueba
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
5. Deploy — cada push a `main` redeploya automáticamente

---

## Mock con Prism

Para que otros grupos puedan integrar mientras el servicio está en desarrollo:

```bash
npm install -g @stoplight/prism-cli
prism mock contrato
# disponible en http://127.0.0.1:4010
```
