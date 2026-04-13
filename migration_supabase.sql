-- =============================================
-- Migration SQL para Supabase (PostgreSQL)
-- Ejecutar en: https://app.supabase.com/sql
-- =============================================

-- Desactivar Row Level Security (RLS) para todas las tablas
-- (la app se encarga de la seguridad)

-- AGREGAR columna descargas_usadas si no existe (para tablas ya creadas)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS descargas_usadas INTEGER NOT NULL DEFAULT 0;

-- Tabla: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id                SERIAL PRIMARY KEY,
    username          TEXT UNIQUE NOT NULL,
    password          TEXT NOT NULL,
    rol               TEXT NOT NULL DEFAULT 'usuario',
    activo            BOOLEAN NOT NULL DEFAULT true,
    descargas_usadas  INTEGER NOT NULL DEFAULT 0,
    creado            TEXT NOT NULL
);
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON usuarios FOR ALL USING (true);

-- Tabla: suscripciones
CREATE TABLE IF NOT EXISTS suscripciones (
    id         SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    expira     TEXT NOT NULL,
    creado     TEXT NOT NULL
);
ALTER TABLE suscripciones ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON suscripciones FOR ALL USING (true);

-- Tabla: sesiones
CREATE TABLE IF NOT EXISTS sesiones (
    token      TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    expira     TEXT NOT NULL
);
ALTER TABLE sesiones ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON sesiones FOR ALL USING (true);

-- Tabla: solicitudes
CREATE TABLE IF NOT EXISTS solicitudes (
    id            SERIAL PRIMARY KEY,
    numero        TEXT UNIQUE NOT NULL,
    compania      TEXT,
    n_personas    INTEGER DEFAULT 0,
    fecha_llegada TEXT,
    transporte    TEXT,
    tipo          TEXT,
    contrato      TEXT,
    activo_a      TEXT,
    activo_s      TEXT,
    tiene_bajas   BOOLEAN DEFAULT false,
    n_bajas       INTEGER DEFAULT 0,
    archivo       TEXT,
    procesado     TEXT NOT NULL
);
ALTER TABLE solicitudes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON solicitudes FOR ALL USING (true);

-- Tabla: personal
CREATE TABLE IF NOT EXISTS personal (
    id           SERIAL PRIMARY KEY,
    solicitud_id INTEGER NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    tipo         TEXT NOT NULL DEFAULT 'sube',
    rfc          TEXT,
    nombre       TEXT,
    libreta      TEXT,
    vigencia     TEXT,
    llegada      TEXT,
    salida       TEXT,
    dias         TEXT,
    transporte   TEXT
);
ALTER TABLE personal ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON personal FOR ALL USING (true);

-- Tabla: pagos_stripe
CREATE TABLE IF NOT EXISTS pagos_stripe (
    id                SERIAL PRIMARY KEY,
    usuario_id        INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    stripe_session_id TEXT UNIQUE,
    stripe_payment_id TEXT,
    estado            TEXT NOT NULL DEFAULT 'pending',
    monto             REAL,
    dias_comprados    INTEGER DEFAULT 7,
    creado            TEXT NOT NULL,
    actualizado       TEXT NOT NULL
);
ALTER TABLE pagos_stripe ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON pagos_stripe FOR ALL USING (true);

-- Indices
CREATE INDEX IF NOT EXISTS idx_sol_numero ON solicitudes(numero);
CREATE INDEX IF NOT EXISTS idx_per_sol ON personal(solicitud_id);
CREATE INDEX IF NOT EXISTS idx_per_tipo ON personal(tipo);
CREATE INDEX IF NOT EXISTS idx_sol_llegada ON solicitudes(fecha_llegada);
CREATE INDEX IF NOT EXISTS idx_stripe_usuario ON pagos_stripe(usuario_id);
CREATE INDEX IF NOT EXISTS idx_stripe_session ON pagos_stripe(stripe_session_id);
CREATE INDEX IF NOT EXISTS idx_stripe_estado ON pagos_stripe(estado);

-- Admin por defecto (password: admin123)
INSERT INTO usuarios (username, password, rol, activo, creado)
SELECT 'admin', sha256('admin123'::bytea), 'admin', true, NOW()::text
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE username = 'admin');

-- Suscripcion de 3650 dias para admin
INSERT INTO suscripciones (usuario_id, expira, creado)
SELECT u.id, (CURRENT_DATE + INTERVAL '3650 days')::text, NOW()::text
FROM usuarios u WHERE u.username = 'admin'
AND NOT EXISTS (SELECT 1 FROM suscripciones WHERE usuario_id = u.id);
