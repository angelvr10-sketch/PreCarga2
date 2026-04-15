-- ============================================
-- Migración: Verificación por Email
-- Fecha: 2026-04-14
-- Descripción: Agrega tablas para verificación
-- de email y rate limiting de registros
-- ============================================

-- Tabla para códigos de verificación pendientes
CREATE TABLE IF NOT EXISTS verificaciones_pendientes (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    codigo VARCHAR(6) NOT NULL,
    expira TIMESTAMP WITH TIME ZONE NOT NULL,
    ip VARCHAR(45),  -- Soporte para IPv6
    creado TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (email)
);

-- Índices para verificaciones_pendientes
CREATE INDEX IF NOT EXISTS idx_verif_email ON verificaciones_pendientes(email);
CREATE INDEX IF NOT EXISTS idx_verif_expira ON verificaciones_pendientes(expira);

-- Tabla para rate limiting de registros
CREATE TABLE IF NOT EXISTS rate_limit_registros (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,  -- Soporte para IPv6
    creado TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para rate_limit_registros
CREATE INDEX IF NOT EXISTS idx_rate_ip ON rate_limit_registros(ip);
CREATE INDEX IF NOT EXISTS idx_rate_creado ON rate_limit_registros(creado);

-- Modificar tabla usuarios para agregar campos de email
-- Nota: Esto asume que la tabla ya existe
-- Si tienes usuarios existentes, ejecuta esto con cuidado
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'usuarios' AND column_name = 'email'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN email VARCHAR(255);
        ALTER TABLE usuarios ADD COLUMN email_verificado BOOLEAN DEFAULT FALSE;
    END IF;
END
$$;

-- Comentarios
COMMENT ON TABLE verificaciones_pendientes IS 'Almacena códigos temporales de verificación para registro';
COMMENT ON TABLE rate_limit_registros IS 'Registra intentos de registro para rate limiting';

-- Permisos (ajustar según tu configuración)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON verificaciones_pendientes TO anon;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rate_limit_registros TO anon;
