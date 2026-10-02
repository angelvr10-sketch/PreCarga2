-- =============================================
-- Migration 002: campos para regenerar plantillas desde la BD
-- Ejecutar en: https://app.supabase.com/sql
-- Agrega las columnas que hoy solo se escriben en el xlsx generado.
-- =============================================

ALTER TABLE solicitudes
  ADD COLUMN IF NOT EXISTS destinohosp    TEXT,
  ADD COLUMN IF NOT EXISTS elepep         TEXT,
  ADD COLUMN IF NOT EXISTS progpre        TEXT,
  ADD COLUMN IF NOT EXISTS cge            TEXT,
  ADD COLUMN IF NOT EXISTS cta            TEXT,
  ADD COLUMN IF NOT EXISTS pos            TEXT,
  ADD COLUMN IF NOT EXISTS nombre_solicita  TEXT,
  ADD COLUMN IF NOT EXISTS ficha_solicita   TEXT,
  ADD COLUMN IF NOT EXISTS nombre_autoriza  TEXT,
  ADD COLUMN IF NOT EXISTS ficha_autoriza   TEXT,
  ADD COLUMN IF NOT EXISTS razonsocial      TEXT;