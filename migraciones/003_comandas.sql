-- ============================================================================
-- 003_comandas.sql — Indices y RPC para el modulo de comandas.
--
-- Ejecutar en el SQL Editor de Supabase.
--
-- Es la migracion que hace posible `upsert_masivo` en core/comandas/repository.py.
-- Sin la parte 1, el endpoint POST /api/comandas/importar responde 409 y no
-- guarda nada. Los dos proyectos comparten esta base, asi que la migracion es
-- ADITIVA: no toca ninguna tabla que precarga2 ya use.
--
-- ── ESTADO 2026-10-06 ────────────────────────────────────────────────────────
-- Verificado antes de activar los CREATE: la consulta de duplicados
--
--     SELECT folio, subido_por, fecha_registro, COUNT(*) AS veces
--     FROM comandas
--     GROUP BY folio,	subido_por, fecha_registro
--     HAVING COUNT(*) > 1;
--
-- devuelve "No rows returned": NO hay duplicados. Crear el indice unico es
-- seguro y no puede fallar por conflicto de datos.
--
-- Todo el archivo usa IF NOT EXISTS, asi que se puede correr mas de una vez.
-- ============================================================================


-- ────────────────────────────────────────────────────────────────
-- 1. EL INDICE UNICO (folio, subido_por, fecha_registro)
--
-- La app de Streamlit hacia upsert con
-- `on_conflict="folio,subido_por,fecha_registro"` (app.py:414), pero eso solo
-- funciona si ese indice unico EXISTE en la base. PostgREST responde 409 si no.
--
-- Las tres columnas van en el indice a proposito: con dos (folio, fecha) el
-- folio de un usuario pisaria el de otro, porque los folios se numeran por
-- destino, no por persona.
-- ────────────────────────────────────────────────────────────────

CREATE UNIQUE INDEX IF NOT EXISTS uq_comandas_folio_usuario_fecha
    ON comandas (folio, subido_por, fecha_registro);


-- ────────────────────────────────────────────────────────────────
-- 2. Indices de lectura
--
-- El patron real de lectura del dashboard es: "las comandas de ESTE usuario en
-- ESTA fecha". La app de Streamlit no tenia indice y por eso hacia
-- `select fecha_registro` de toda la tabla en cada rerun, dos veces.
-- ────────────────────────────────────────────────────────────────

-- El indice que importa para la pantalla principal.
CREATE INDEX IF NOT EXISTS idx_comandas_usuario_fecha
    ON comandas (subido_por, fecha_registro DESC);

-- Para la descarga individual (folio dentro de una fecha).
-- Nota: el indice unico de la parte 1 ya cubre (folio, ...), asi que este es
-- redundante. Se deja porque ayuda cuando se busca un folio sin saber la fecha,
-- que es el caso del boton de descarga individual. Ocupa poco.
CREATE INDEX IF NOT EXISTS idx_comandas_folio
    ON comandas (folio);


-- ────────────────────────────────────────────────────────────────
-- 3. RPC: fechas con datos, de una vez
--
-- La funcion hace el DISTINCT en Postgres y devuelve solo una columna. La
-- alternativa sin RPC es traer todas las filas y deduplicar en Python, que es
-- justo lo que hacia la app de Streamlit.
--
-- `repository.fechas_disponibles` intenta esta RPC y, si no existe, cae al
-- otro metodo. Se puede aplicar esta migracion en cualquier momento; el codigo
-- ya funciona con las dos.
--
-- SECURITY DEFINER: la tabla tiene RLS abierto (ver mas abajo), asi que la
-- funcion podria ejecutarse con los permisos de quien la llama. Con DEFINER
-- corre como el dueno, que es lo unico que garantiza que el filtro por usuario
-- se aplique siempre y no se pueda saltar.
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION comandas_fechas_usuario(p_usuario text)
RETURNS TABLE (fecha_registro text)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT DISTINCT c.fecha_registro
    FROM comandas c
    WHERE lower(c.subido_por) = lower(p_usuario)
      AND c.fecha_registro IS NOT NULL
    ORDER BY 1 DESC;
$$;


-- ────────────────────────────────────────────────────────────────
-- 4. Chequeo final
-- ────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF to_regclass('public.comandas') IS NULL THEN
        RAISE NOTICE 'La tabla comandas no existe. Nada que revisar.';
    ELSE
        RAISE NOTICE 'Tabla comandas: % filas',
            (SELECT COUNT(*) FROM comandas);
        RAISE NOTICE 'Usuarios distintos: %',
            (SELECT COUNT(DISTINCT subido_por) FROM comandas);
        RAISE NOTICE 'Rango de fechas: % a %',
            (SELECT MIN(fecha_registro) FROM comandas),
            (SELECT MAX(fecha_registro) FROM comandas);
        RAISE NOTICE 'RPC disponible: %',
            (SELECT COUNT(*) > 0 FROM pg_proc WHERE proname = 'comandas_fechas_usuario');
    END IF;
END $$;


-- ============================================================================
-- NOTA SOBRE RLS (NO SE TOCA EN ESTA MIGRACION)
--
-- En precarga2/migration_supabase.sql todas las tablas tienen
-- `CREATE POLICY "Allow all" ... USING (true)`. Eso deja pasar a CUALQUIER
-- rol, incluida la anon key, que es una credencial publica: con ella se podrian
-- leer todos los usuarios y sus hashes de contrasena.
--
-- Hoy el riesgo esta acotado porque:
--   - el backend usa SUPABASE_SERVICE_ROLE_KEY (core/supabase_db.py:24-37);
--   - la anon key nunca sale del backend.
--
-- Y se mantiene asi al absorber comandas: la anon key desaparece de este flujo,
-- porque el frontend nunca habla con Supabase; todo pasa por FastAPI, que valida
-- la cookie de sesion y aplica el filtro por usuario en codigo.
--
-- Activar RLS restrictivo sobre `comandas` es un paso POSTERIOR y aparte: hay
-- que definir primero las reglas FOR SELECT, porque sin ellas los SELECT de los
-- dos backends empiezan a devolver [] en silencio, que es el fallo mas dificil
-- de detectar en una app asi.
-- ============================================================================
