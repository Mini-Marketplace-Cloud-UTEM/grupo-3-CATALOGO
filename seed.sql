-- Ejecutar en Supabase > SQL Editor

INSERT INTO categories (id, name) VALUES
  ('550e8400-e29b-41d4-a716-446655440001', 'Herramientas'),
  ('550e8400-e29b-41d4-a716-446655440002', 'Electrónica'),
  ('550e8400-e29b-41d4-a716-446655440003', 'Hogar'),
  ('550e8400-e29b-41d4-a716-446655440004', 'Jardín')
ON CONFLICT (id) DO NOTHING;

INSERT INTO products (id, name, description, price, stock_visible, category_id, sku, status, images) VALUES
  (
    '550e8400-e29b-41d4-a716-446655440000',
    'Taladro Eléctrico 700W',
    'Taladro percutor profesional con maletín incluido',
    49990,
    15,
    '550e8400-e29b-41d4-a716-446655440001',
    'TAL-700W-PRO',
    'ACTIVE',
    ARRAY['https://cdn.marketplace.cl/products/taladro.jpg']
  ),
  (
    '660e8400-e29b-41d4-a716-446655440001',
    'Sierra Circular 1200W',
    'Sierra circular portátil con disco incluido',
    69990,
    8,
    '550e8400-e29b-41d4-a716-446655440001',
    'SIE-1200W-PR',
    'ACTIVE',
    ARRAY['https://cdn.marketplace.cl/products/sierra-circular.jpg']
  ),
  (
    '770e8400-e29b-41d4-a716-446655440002',
    'Aspiradora 2000W',
    'Aspiradora de alta potencia con filtro HEPA',
    89990,
    5,
    '550e8400-e29b-41d4-a716-446655440003',
    'ASP-2000W-H',
    'ACTIVE',
    ARRAY[]::text[]
  ),
  (
    '880e8400-e29b-41d4-a716-446655440003',
    'Lijadora Orbital 300W',
    'Lijadora orbital compacta — producto temporalmente sin stock',
    29990,
    0,
    '550e8400-e29b-41d4-a716-446655440001',
    'LIJ-300W-ORB',
    'INACTIVE',
    ARRAY[]::text[]
  )
ON CONFLICT (id) DO NOTHING;
