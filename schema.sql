-- ============================================================
-- Catalog Service — Grupo 3
-- Schema completo para recrear la base de datos desde cero
-- Ejecutar en Supabase > SQL Editor ANTES del seed.sql
-- ============================================================

-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Tabla: categories ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS categories (
    id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR     NOT NULL UNIQUE
);

-- ── Tabla: products ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS products (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR     NOT NULL,
    description   VARCHAR,
    price         BIGINT      NOT NULL CHECK (price >= 0),
    stock_visible INTEGER     NOT NULL DEFAULT 0 CHECK (stock_visible >= 0),
    category_id   UUID        NOT NULL REFERENCES categories(id),
    sku           VARCHAR     NOT NULL UNIQUE,
    status        VARCHAR     NOT NULL DEFAULT 'ACTIVE'
                              CHECK (status IN ('ACTIVE', 'INACTIVE', 'DELETED')),
    images        TEXT[]      NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Índices ──────────────────────────────────────────────────

-- Filtro de status en todos los listados
CREATE INDEX IF NOT EXISTS idx_products_status
    ON products (status);

-- FK y filtro por categoría en search
CREATE INDEX IF NOT EXISTS idx_products_category_id
    ON products (category_id);

-- Búsqueda por texto (ILIKE) en name
CREATE INDEX IF NOT EXISTS idx_products_name
    ON products USING gin (name gin_trgm_ops);

-- ── Trigger: updated_at automático ───────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Tabla: idempotency_records ───────────────────────────────
-- Cachea la respuesta de un POST por Idempotency-Key + endpoint,
-- para que un reintento con la misma key devuelva el resultado
-- original en vez de crear un duplicado.

CREATE TABLE IF NOT EXISTS idempotency_records (
    key             VARCHAR     NOT NULL,
    endpoint        VARCHAR     NOT NULL,
    request_hash    VARCHAR,
    response_status INTEGER     NOT NULL,
    response_body   JSONB       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (key, endpoint)
);
