# Plan de migración: ComandasPro (Streamlit) → precarga2 (FastAPI + TanStack + PWA)

Fecha: 2026-10-06
Alcance: eliminar `C:\Users\Admin\Desktop\comandas` (Streamlit, 1,613 líneas) y absorber
su functionality como módulo nativo de `precarga2`, expuesto en `/comandas`.

---

## 0. Diagnóstico: qué hay realmente que migrar

### 0.1 Inventario de `app.py` (1,613 líneas, archivo único)

| Bloque | Líneas | Naturaleza | Destino |
|---|---|---|---|
| Bootstrap Supabase + `st.stop()` | 25–40 | Streamlit-coupled | **Fuera** — usar `core/supabase_db.py` |
| Auth (`_verificar`, bcrypt) | 56–138 | Reemplazado por sesión precarga2 | **Fuera** (se conserva el dato, no el código) |
| CSS tema claro/oscuro | 153–329 | Streamlit `data-testid` | **Fuera** — usar Tailwind + `next-themes` equivalente |
| Logos base64 embebidos | 333–335 | **Código muerto** (ver 0.3) | **Fuera** |
| `ComandaApp.parse_pdf` | 419–555 | Regex, fecha ES, título, observaciones | `core/comandas/parser.py` — **port 1:1** |
| `calcular_estadisticas` | 557–588 | Agregaciones | `core/comandas/stats.py` — **port 1:1** |
| `_dibujar_header_machote` | 603–668 | reportlab, coordenadas | `core/comandas/pdf/comanda.py` — **port 1:1** |
| `_dibujar_tabla_datos` | 671–695 | reportlab | ídem |
| `_dibujar_tablas_utensilios` | 697–735 | reportlab | ídem |
| `_dibujar_bloque_firmas_estandar` | 737–758 | reportlab | ídem |
| `_dibujar_comanda_en_canvas` | 762–803 | reportlab | ídem |
| `_dibujar_comanda_mortera_en_canvas` | 821–918 | reportlab, 6 firmas extra | ídem |
| `generar_vales_pdf_bytes` | 936–1122 | reportlab, 10 vales/pág | `core/comandas/pdf/vales.py` |
| `generar_reporte_estadistico_bytes` | 1124–1387 | reportlab, donut+barras+tabla | `core/comandas/pdf/estadistico.py` |
| `_load_from_db` / `_save_to_db` | 349–416 | `ilike(subido_por)` + upsert | `core/comandas/repository.py` |
| UI: navbar, KPI, gráficas, tabla, filtros | 1438–1797 | Streamlit widgets | `frontend/src/routes/comandas.tsx` |

**Balance:** ~1,000 líneas de lógica de negocio y PDF (port directo, sin reescritura) +
~600 líneas de UI Streamlit (se reemplaza) + ~13 líneas de bootstrap/auth (se descarta).

### 0.2 Bugs y deuda detectados (con línea)

| # | Severidad | Ubicación | Problema |
|---|---|---|---|
| B1 | **Alta** | 1698–1728 | Los 4 `st.download_button(data=...)` **generan los 4 PDFs completos en cada rerun**, aunque el usuario nunca haga clic. Con 60 comandas son ~200 páginas reportlab renderizadas por interacción. |
| B2 | **Alta** | 531–549 | Un upsert HTTP por comanda dentro del loop. Un PDF de 60 comandas = 60 round-trips a PostgREST. |
| B3 | **Alta** | 1414–1416, 1521, 1538 | `_load_from_db()` y `get_available_dates()` se ejecutan en cada rerun. `get_available_dates` **trae todas las filas** (sin filtro de fecha) y se llama **dos veces** (líneas 1521 y 1538). |
| B4 | **Media** | 433, 1575 | `strftime("%B")` devuelve el mes en inglés si el servidor no tiene locale `es_MX`. El PDF y el caption muestran `OCTOBRE`/`October` de forma inconsistente. La línea 358–362 sí lo hace bien con arrays ES. |
| B5 | **Media** | 148 vs `AGENTS.md` | El código compara `rol == "usuario"`; el doc dice `operador`. Vocabulario de roles divergente entre código, doc y BD. |
| B6 | **Media** | 151, 1779 vs 1731 | `CAN_DOWNLOAD` incluye `lector` y la línea 1779 **sí** le da el PDF individual, pero el comentario de 1731 y `AGENTS.md` dicen que lector no descarga. Contradicción no resuelta. |
| B7 | **Media** | todo | **Cero tests.** ~1,000 líneas de regex y coordenadas reportlab sin ninguna red de seguridad. Es el riesgo #1 de la migración. |
| B8 | **Baja** | 591–601 | `_logo_koltov_bytes()` es código muerto: devuelve `None` siempre, con un literal base64 truncado. |
| B9 | **Baja** | 334–335 | `_LOGO_KOLTOV_B64` / `_LOGO_SHAT_B64`: ~4 KB de base64 embebidos en el `.py`, **nunca usados**. El PDF dibuja los textos "KOL TOV"/"SHAT" (609–615). |
| B10 | **Baja** | 99 | Fragmento de CSS corrupto: una cadena Python `"    .lw{...}\n"` inyectada dentro del bloque `<style>` por un escape mal hecho. |
| B11 | **Baja** | imports | `hmac`, `json` sin uso; `hashlib` solo usado por `_hash()` (línea 59) que a su vez está muerta. |
| B12 | **Media** | esquema | `fecha_registro` es `TEXT`, no `DATE`. Ordena lexicográficamente (funciona con ISO) pero impide rangos limpios y no indexa bien. |
| B13 | **Media** | 29–30 | El cliente usa la **anon key** de Supabase. Con las políticas `USING (true)` que hay en `precarga2/migration_supabase.sql`, esa clave concede lectura de `usuarios` **incluidos los hashes bcrypt**. |

### 0.3 Lo que `precarga2` ya resuelve (no rehacer)

- **Backend**: FastAPI 0.141.1 + uvicorn, 2 workers, GZip, Dockerfile 2 etapas, deploy en Fly.io (`fly.toml`, `min_machines_running = 0`).
- **Auth**: login email/password → cookie `httponly` `session` → tabla `sesiones` → `usuarios`. Helper listo: `core.auth.get_current_user(request)` devuelve el dict del usuario. **24 h de expiración.**
- **Acceso a Supabase**: `core/supabase_db.py` ya tiene cliente httpx persistente (keep-alive, 20 conexiones), reintentos (3), timeout 30 s y `_get/_post/_patch/_delete`. Se usa **service_role**, nunca anon (documentado en 24–37).
- **Frontend**: React 19 + Vite 6 + TanStack Router 1.90 + TanStack Query 5.60 + TanStack Table + TanStack Form + Recharts 3 + Tailwind 3 + Radix + lucide-react.
- **UI kit**: `button, card, table, dialog, badge, input, label, select, dropdown-menu, avatar, toast, separator, tooltip` ya existen en `frontend/src/components/ui/`.
- **Cliente API**: `frontend/src/lib/api.ts` con `credentials:'include'`, timeouts (30 s / 180 s upload) y `ApiError` tipado.
- **PWA**: `sw.js` escrito a mano y bien documentado (network-first en navegación, cache-first en `/assets/` con hash, **`/api/` nunca se cachea**), `manifest.webmanifest` con `shortcuts`, hook `useActualizacion` para el aviso de versión nueva.
- **Layout**: `AppLayout` + `Sidebar` con `navItems` tipado (`RouteTo`).

> **Conclusión estratégica: esto NO es una migración greenfield.** No se crea una segunda app
> FastAPI ni un `base: '/precarga2'` en Vite. Se **añade un módulo** a precarga2.
> El auth es literalmente el mismo: entrar a `/comandas` es entrar a `/dashboard`.

---

## 1. Decisiones pendientes (bloquean F0)

### D1 — Ruta: `/comandas` vs `/precarga2/comandas`
**Recomendación: `/comandas`.** Todas las rutas actuales son `/dashboard`, `/procesar`,
`/altas`… con `scope: "/"`. Meter una sola sección bajo un prefijo `/precarga2` rompe la
convención y obliga a tocar `basepath` de TanStack Router, `base` de Vite, `scope`/`start_url`
del manifest y las rutas de `PRECACHE` del service worker.

> Si el prefijo `/precarga2` es **obligatorio** (gateway que sirve varias apps), el cambio es
> mecánico pero hay que aplicarlo en 5 sitios: `createRouter({ basepath })`,
> `vite.config.ts → base`, `manifest.webmanifest → id/scope/start_url`,
> `sw.js → PRECACHE`, y los `<Link>` absolutos. Se documenta como F6-bis.

### D2 — Rol `lector`: ¿existe en precarga2?
`usuarios.rol` en precarga2 es `admin | usuario`. ComandasPro necesita `lector`.
`_serialize_user` solo mira `rol == 'admin'`, así que un `lector` **degrada limpiamente**
a usuario normal en precarga2. **No hay migración de usuarios.**
Falta confirmar: ¿existen usuarios precarga2 que deban ser `lector` en comandas?
(Si sí, cambiar el `rol` de esa fila es un UPDATE de una columna, nada más.)

### D3 — ¿Las descargas de comandas consumen cuota?
`core.auth.puede_descargar` descuenta contra `MAX_DESCARGAS_GRATIS = 30` y `contar_descarga`
incrementa `usuarios.descargas_usadas`. Si los PDF de comandas cuentan, un usuario agota
las 30 en ~5 clics.
**Recomendación: NO contarlas en la primera versión** (o contador separado `descargas_comandas`).
Decidir antes de F4.

### D4 — ¿Comandas es sección de todos los usuarios precarga2 o de un subconjunto?
Hoy `comandas.subido_por = usuarios.username` y el filtro es `ilike(subido_por, username)`.
Se mantiene el aislamiento por usuario (ya confirmado). Falta decidir si algún rol
precarga2 **no** debe ver la sección (ej. usuarios de prueba). Si aplica, se filtra `navItems`
por rol.

### D5 — Rol `lector`: qué reportes puede generar

`lector` es un valor posible de `usuarios.rol`, aunque hoy nadie lo tiene (los roles reales son
`admin` y `usuario`). Quedó decidido que:

- `admin` y `usuario` pueden generar **los cuatro** reportes en bloque
  (`ROLES_REPORTE_COMPLETO`).
- `lector` **no**: solo el estadístico y el PDF de una comanda suelta (`ROLES_LECTURA`).
  El dashboard y las tarjetas sí los ve.

La app de Streamlit era contradictoria aquí (daba el PDF individual al lector aunque el comentario
de `app.py:1731` decía que no); en precarga2 queda decidido y escrito.

**Trampa asociada:** `/api/auth/me` expone `rol` además de `admin`. Con solo el booleano `admin` no
hay forma de distinguir `usuario` de `lector`, y tratar a los usuarios normales como lectores les
oculta tres de los cuatro botones aunque el backend se los permita. Ya pasó. Lo fija
`tests/test_consistencia_roles.py`.

### D6 — ¿De dónde sale el "barco" de una comanda? (decidido 2026-10-06)

**Las comandas NO tienen dimensión de barco.** Comprobado sobre las 5,545 filas de la tabla:

| Dato | Resultado |
|---|---|
| Columnas de `comandas` | `id, folio, subida_por, datos, updated_at, fecha_registro` |
| `datos.destino` distintos | **92** (POL-A, ABKATUN A, YKN, KU-A, ZAAP-C…) |
| Filas que mencionan RPX | **0** |
| Filas que mencionan CPZ | **0** |
| `datos.transporte` | AEREO 2356 · GANGWAY 2203 · MARÍTIMO 984 · CANASTILLA 2 |

RPX y CPZ en el dashboard salen de `solicitudes.destinohosp` (`routers/api_data.py:95`), que es
otra tabla con otro vocabulario: **los dos no se cruzan**. La app de Streamlit tampoco tenía
noción de barco.

**Decisión del usuario:** por ahora el barco se deduce de **quién subió la comanda**:

| Usuario | Barco |
|---|---|
| `erika` | RPX |
| `PabloDG` | RPX |
| `LuisE` | CPZ |

Vive en `BARCO_POR_USUARIO` (`core/comandas/serie.py`), normalizado a minúsculas porque
`usuarios` tiene `PabloDG`/`LuisE` y `comandas.subido_por` guarda siempre `erika`/`luise`.

**Consecuencias asumidas:**

- Es un **marcador, no un dato**. Si los reportes algún día traen el barco, se cambia ahí.
- Un usuario fuera del mapa **no** se asigna por defecto: sus comandas van a `sin_asignar` y el
  frontend avisa. Silenciosamente dumping al barco equivocado sería peor que decir "no sé".
- `PabloDG` tiene 0 comandas hoy, pero si sube un reporte entra como RPX sin tocar nada.
- **CPZ dejó de subir el 2026-09-11** (dato real). En el periodo de 30 días su serie sale plana en
  cero al final. No es un fallo de la gráfica.

### D7 — La tarjeta de total de comandas es global (decidido 2026-10-06)

`total_comandas` cuenta **todos** los usuarios y todo el histórico (5,545), igual que
`total_solicitudes` o `total_movimientos`. Consecuencia: `/api/comandas/serie` es la **única
lectura del router que no pasa por `clave_de_usuario`**. Devuelve solo conteos por fecha y barco,
nunca contenido de comandas. El riesgo está escrito en `repository.serie_diaria_barcos`.

### D8 — Altas Generadas y Bajas Procesadas pausadas, no borradas (2026-10-06)

Las dos tarjetas del dashboard se comentaron a pedido del usuario para dejarle el lugar a
**Total Comandas**. Se conservan las líneas comentadas en `statCards` y `DashboardStats` sigue
traendo los dos campos, así que volver a activarlas es descomentar dos líneas. Lo fija
`tests/test_serie.py::TestTarjetasDelDashboard`.

---

## 2. Fases de trabajo

### F0 — Decisiones y baseline (0.5 día)
1. Cerrar D1–D4.
2. Congelar el alcance: capturar **5 PDFs reales representativos** (semana normal, semana con
   morteras, PDF sin fecha en el texto, PDF con observables largos, PDF con nombre de compañía
   acentuado) en `precarga2/tests/fixtures/`. Son el golden set de todo lo demás.
3. Capturar los 4 PDFs de salida actuales de la app Streamlit en producción para una
   comparación byte-a-byte visual post-migración.
4. Snapshot de la BD: `select count(*), min(fecha_registro), max(fecha_registro) from comandas;`
   y `select count(*) from comandas group by subido_por;`

**Salida:** decisiones escritas, fixtures en disco, baseline de conteos.

> **ESTADO 2026-10-06: F0 GOLDEN SET CERRADO.** Los 3 PDF de
> `Descargas/ComandaAlimentos*.pdf` son los **reportes de ENTRADA**: los que sube
> un usuario y de los que la app extrae las comandas. Es el caso de uso principal
> del parser. Copiados a `tests/fixtures/` (ignorado por git: son documentos
> operativos).
>
> Números congelados (2026-10-06), que `test_fixtures_reales.py` verifica:
> 18 comandas / 295 PAX (2026-07-03), 48 / 412 (2026-08-14), 47 / 449 (2026-09-01).
> **113 comandas leídas de PDFs reales.**
>
> **Forma real del reporte** (esto es lo que los tests ahora fijan):
> tabla con columnas `NO. COM. / HORARIO / DEPARTAMENTO-COMPAÑÍA / DESTINO /
> No. PAX / TRANSPORTE / MENU 1 / MENU 2 / CUSTODIO / OBSERVACIONES`, **un campo
> por línea**, y un pie con la fecha en minúsculas y con acentos
> (`viernes, 3 de julio de 2026`), el proyecto y el contrato. El parser saca la
> fecha y el título de ese pie.
>
> **Aprendizajes que cambian el plan:**
> 1. Los destinos son cortos y con sufijo: `KU-A`, `YKN`, `MALOOB-B`, `AYATSIL-D`,
>    `ZAAP-C`, `EK-A`. Los 16 están en `DESTINO_PATTERN`, con un test
>    parametrizado por destino: si la plataforma usa uno nuevo, ese test falla y
>    avisa. Es la red sobre el punto más frágil del sistema.
> 2. **`PAX` y `MENU 1` no siempre coinciden**: JUL026 tiene pax 125 / menu1 126,
>    SEP014 tiene pax 04 / menu1 05. Por eso el código fuerza `menu_1 = pax`
>    (app.py:543). No es arbitrario: está justificado por los datos reales.
> > **GOLDEN DE SALIDA (nuevo, 2026-10-06).**
> `Descargas/Todas_las_Comandas_REFORMA PEMEX.pdf` son las **30 páginas** del
> machote que produjo la app el 2026-10-06 (REFORMA PEMEX, miércoles 7 de octubre
> de 2026, 295 PAX). Copiado a `tests/fixtures/Todas_las_Comandas_REFORMA_PEMEX.pdf`.
>
> Este es el golden más fuerte del proyecto: compara la **generación** contra la
> salida real de la app con datos reales. `scripts/comparar_golden.py` deduce las
> 30 comandas de la geometría del PDF (columna x de cada campo) y las vuelve a
> dibujar; luego compara **posición y texto de cada línea**. No es una
> comparación de texto: si una línea de firma se mueve medio milímetro, falla.
>
> **Resultado: 30/30 páginas con geometría idéntica.** En `tests/test_golden_salida.py`.
>
> **Bug que este golden destapó y que yo había introducido:** yo normalizaba el
> día de la semana quitando acentos (`MIÉRCOLES` → `MIERCOLES`). El golden
> imprime `MIÉRCOLES, 7 DE OCTUBRE DE 2026`, y `app.py:358` confirma que el
> original lleva acento en `MIÉRCOLES` y `SÁBADO`. Helvetica de reportlab los
> dibuja sin problema, así que mi "normalización" cambiaba el papel firmado.
> Mis tests no lo detectaron porque usaba `MARTES`, que no lleva acento.
> Corregido en `core/comandas/fecha.py`; `_sin_acentos` se eliminó (los meses en
> español nunca llevan acento, no hacía falta).
>
> Aprendizado técnico: reportlab dibuja las tablas de `platypus` bajo una CTM, así
> que las coordenadas del `tm` del visor de pypdf son **locales** a esa matriz.
> Hay que aplicar la CTM para obtener la posición real en la página.

### F1 — Extracción pura del dominio (1 día, sin FastAPI ni Streamlit)
Objetivo: que el código de negocio corra **sin importar streamlit**.

1. Crear `precarga2/core/comandas/` con `__init__.py`.
2. `core/comandas/fecha.py` — helpers de fecha en español, **corrige B4**:
   `DIAS_ES`, `MESES_ES`, `fecha_largo_es(date) -> "LUNES, 13 DE MAYO DE 2026"`,
   `fecha_corta_es(fecha_pdf) -> "13/05/2026"`. Sin `strftime("%B")` en ningún lado.
   Reemplaza el bloque 358–362 y el 966–980 de `app.py`.
3. `core/comandas/parser.py` — port literal de `parse_pdf` (419–555):
   - `DESTINO_PATTERN` como constante de módulo (468–487).
   - `extraer_fecha_texto(text) -> (str, str|None)` — regex 431 + normalización 436–460.
   - `extraer_titulo(text) -> str` — regex 465.
   - `extraer_observaciones(text) -> dict[folio, str]` — regex_obs 490–515.
   - `parse_comandas(text) -> list[Comanda]` — regex 517–526 + armado 536–547.
   - `extraer_texto_pdf(file_bytes) -> str` — pypdf 421–427 (`re.sub` de las 426–427).
   - **Sin `st.error`**: cada función lanza `ValueError` tipada. El router la traduce a JSON.
   - `parse_pdf(file_bytes) -> ResultadoParse` con `{comandas, fecha_texto, fecha_iso, titulo}`.
   > Nota: el bloque 548–551 (`comandas_dict` merge) es comportamiento de sesión y **no**
   > pertenece al parser; en la API cada upload es un upsert por folio y el merge es de la BD.
4. `core/comandas/stats.py` — port de `calcular_estadisticas` (557–588), sin `if not comandas`.
5. `core/comandas/pdf/comanda.py` — port de los 6 métodos reportlab (591–918).
   **Copia las coordenadas al milímetro.** Firmas: `col1 = width*0.27`, `col2 = width*0.73`,
   `firma_sep = 30`, `firma_ancho = 200`, `bloque_top = y_recibe - 35`.
   La función nunca necesita `self` → pasar `fecha_texto` y `titulo` como argumentos.
   `footer = "Angel Valenzuela Romero © 2026"` como constante.
6. `core/comandas/pdf/vales.py` — port de 936–1122. `rows = 5` (10 vales/página),
   `margin_x = 28`, `margin_y = 18`, `gap_vales = 4`, `pad = 8`.
7. `core/comandas/pdf/estadistico.py` — port de 1124–1387, incluida la paginación manual
   de la tabla de compañías (1360–1384) y el `tbl._height` (atributo privado de reportlab:
   sustituir por `tbl.wrapOn` + `tbl._height` o `getattr(tbl, '_height', 0)` protegido).
8. `core/comandas/repository.py` — **corrige B2 y B3**:
   - `listar(usuario, fecha_iso) -> list[dict]`
   - `fechas_disponibles(usuario) -> list[str]` — vía RPC `comandas_fechas_usuario(text)`
     (DISTINCT) en vez de traer N filas. Si no se puede crear la RPC, filtrar en PostgREST
     con `select=fecha_registro` + `order=fecha_registro.desc` + paginar.
   - `upsert_masivo(usuario, fecha_iso, comandas) -> dict` — **un solo** POST a
     `/rest/v1/comandas?on_conflict=folio,subido_por,fecha_registro` con el array completo.
   - `borrar(usuario, fecha_iso, folio) -> bool`
   - `diagnostico()` — para el expander de soporte (1524–1534), **solo admin**.
   - Todos con `subido_por = usuario["username"].strip().lower()` — **normalización
     obligatoria** porque hoy el login precarga2 acepta email *o* username, y `subido_por`
     guarda siempre el username.
9. `requirements.txt`: agregar `pypdf==6.1.4` y `reportlab==4.4.4`.
   **NO** agregar `supabase` ni `pandas` — `core/supabase_db.py` ya cubre el acceso y las
   agregaciones son dicts. **NO** agregar `bcrypt` (ya está, 5.0.0) — lo reutiliza `core.auth`.

**Salida:** `python -c "from core.comandas.parser import parse_pdf"` funciona en un REPL
sin FastAPI. Los PDFs generados son visualmente idénticos a los de Streamlit.

> **ESTADO 2026-10-06: F1 COMPLETADA Y VERIFICADA.** El port produce los 5 PDF
> idénticos a los de la app original (`scripts/comparar_pdf.py`, 5/5) y el parser
> coincide comanda por comanda (`scripts/comparar_parser.py`). Nota: `pypdf` real
> es **6.19.0**, no 6.1.4 (esa versión no existe). Los destinos válidos van SIN
> espacios: `PAPALOAPAN`, no `PAPA LOAPAN` — ver F2 abajo.

### F2 — Tests golden (1 día, antes de tocar la API)
Sin este paso los fases siguientes son un vuelo a ciegas sobre 1,000 líneas.

`precarga2/tests/` con `pytest` + `pytest-asyncio` (agregar a `requirements.txt` solo dev).

1. `test_parser.py` — por cada fixture:
   - nº de comandas detectadas (valor esperado congelado en F0).
   - `fecha_iso` y `titulo`.
   - folios extraídos, ordenados.
   - para 2 comandas: `compania`, `destino`, `pax`, `transporte`, `menu_1`, `menu_2`,
     `tipo` (MORTERA/VIANDA), `observaciones`.
   - casos borde: PDF sin fecha → `fecha_iso == hoy`; observables > 95 chars; tilde en compañía.
2. `test_stats.py` — totales, `por_destino`, `por_destino_grafico` (abrev `G`/`M`/`(C)`),
   `por_compania`, `por_transporte` contra valores calculados a mano.
3. `test_pdf.py` — por cada generador:
   - `len(PdfReader(bytes).pages) == esperado` (1 comanda=1; 12 comandas=12; 11 vales=2 páginas).
   - el texto extraído contiene `RECIBE ALIMENTOS`, `ENTREGA UTENSILIOS`, el folio.
   - en modo MORTERA, aparecen las 6 etiquetas (`ELABORÓ` … `OPERADOR RESPONSABLE`).
   - el reporte estadístico con 30+ compañías produce >1 página (cubre la paginación de 1360).
4. `test_pdf_equivalente.py` — golden binario: compara el PDF generado con el capturado en
   F0 con `pdftotext -layout` normalizado. Si no hay diferencia de texto → port correcto.

**Salida:** suite verde. **GATE: no se avanza sin esto verde.**

> **ESTADO 2026-10-06: F2 COMPLETADA — 145 tests verdes.** Suite en `tests/` con
> `pytest`. Incluye `test_comparar_original.py`, que corre la clase `ComandaApp`
> de la app vieja y compara PDF y parseo contra el módulo nuevo; se salta solo si
> `comandas/app.py` no está en la máquina. Y `test_fixtures_reales.py`, que
> corre el pipeline completo sobre los 3 PDF de la plataforma.
> `pytest`, `streamlit`, `pandas`, `plotly` y `supabase` van en
> `requirements-dev.txt`, NO en `requirements.txt` (el servidor no los necesita).
>
> **Bug real de F1 corregido:** `_sin_acentos` se aplicaba antes de `.upper()`, así
> que solo quitaba acentos mayúsculos y `miércoles` salía `MIÉRCOLES`. Lo atrapó
> el test `test_extrae_sin_acento_en_el_dia`. Ver `core/comandas/fecha.py`.
>
> **Bug encontrado por los PDF reales:** el detector de folios perdidos usaba
> `[A-Z]{3}\d+`, que matchea dentro de `MENU1-VIANDA` y reportaba una comanda
> perdida llamada `ENU1` que no existe. Ahora exige la forma completa folio +
> hora (`_RE_FOLIO_CANDATOS`). Falso positivo, no affects datos, pero habría
> hechocry “faltan comandas” en la UI todos los días.

### F3 — Endpoints FastAPI (1 día)
`precarga2/routers/api_comandas.py`, `router = APIRouter(prefix="/api/comandas")`.

Todos con dependencia explícita:
```python
def _usuario(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "No autenticado")
    return user
```

| Método | Ruta | Rol | Notas |
|---|---|---|---|
| GET | `/fechas` | todos | `["2026-10-06", …]` desc. Cache-Control `private, max-age=30` |
| GET | `/` | todos | `?fecha=YYYY-MM-DD` (default hoy) → `{comandas, fecha_texto, titulo, fecha_iso}` |
| GET | `/estadisticas` | todos | `?fecha=` → payload de `stats.py` (el dashboard hace 1 fetch, no 3) |
| POST | `/importar` | todos | multipart `file`. Valida `.pdf`, **tope 20 MB**,Magic bytes `%PDF`. `await file.read()`, `parse_pdf`, `upsert_masivo`. Devuelve `{ok, fecha, insertadas, actualizadas, total_pax, advertencias}` |
| GET | `/reporte/estadistico` | todos | PDF inline, `Content-Disposition: attachment` |
| GET | `/reporte/todas` | admin+operador | PDF |
| GET | `/reporte/mortera` | admin+operador | PDF |
| GET | `/reporte/vales` | admin+operador | PDF |
| GET | `/reporte/{folio}` | todos (ver D2) | PDF |
| GET | `/diagnostico` | admin | reemplaza el expander |

Reglas transversales:
- **Permisos por rol**: `admin | usuario` → todos los reportes; `lector` → solo
  `estadistico` (corrige B6 de forma explícita, no por accidente).
- **Tope de descarga**: aplicar `puede_descargar` + `contar_descarga` según D3.
- `run_in_threadpool` para `parse_pdf` y para los 5 generadores de PDF: son CPU-bound
  (reportlab es Python puro) y bloquearían el event loop con `--workers 2`.
- `PDF_BYTES = Response(content=pdf, media_type="application/pdf",
  headers={"Content-Disposition": f'attachment; filename="{nombre}"',
           "Cache-Control": "private, no-store"})` — `no-store` porque el SW nunca
  cachea `/api/` pero el navegador sí podría cachear un attachment.
- Registrar en `main.py`: `app.include_router(api_comandas.router)` **antes** del catch-all
  de la SPA (línea 130), junto a los demás `include_router` (119–123).

**Salida:** los 10 endpoints responden correctamente vía `curl` con cookie de sesión.

> **ESTADO 2026-10-06: F3 COMPLETADA.** Decisiones cerradas: **D1 = `/comandas`**
> (sin prefijo `/precarga2`) y **D3 = sí descuentan descarga** (cada PDF de
> comandas cuenta una, igual que los de precarga2).
>
> Archivos nuevos:
> - `core/comandas/repository.py` — única capa que toca la BD.
> - `routers/api_comandas.py` — los 10 endpoints, registrado en `main.py:124`.
> - `migraciones/003_comandas.sql` — índices + RPC, **más el bloqueante de abajo**.
> - `tests/test_api_comandas.py` — 51 tests de la capa HTTP.
>
> **Bugs de la app Streamlit corregidos aquí:**
> - **B2**: un upsert por lotes en vez de un POST por comanda. El test
>   `test_importa_reporte_real` comprueba `almacen.escrituras == 1` con 18
>   comandas: un viaje, no 18.
> - **B3**: `fechas_disponibles` usa la RPC `comandas_fechas_usuario` (DISTINCT en
>   Postgres). Sin RPC cae a traer solo la columna de fecha. La app traía la fila
>   entera y se quedaba con el set completo, dos veces por rerun.
> - **B6 (roles)**: `lector` puede ver el dashboard, el estadístico y el PDF
>   individual; no puede generar reportes en bloque. Queda escrito en el código y
>   con 8 tests.
>
> **BLOQUEANTE REAL, no detectado antes:** `migraciones/003_comandas.sql` empieza
> con un `RAISE NOTICE` que **solo avisa**, sin crear nada, porque falta confirmar
> si el índice único `(folio, subido_por, fecha_registro)` existe. `app.py:414`
> hace upsert con ese `on_conflict`, así que si el índice no está, **el import
> devuelve 409 y no guarda nada**. El archivo trae la consulta para listar
> duplicados y el `CREATE UNIQUE INDEX` comentado: hay que correr el bloque 1b y
> decidir con el equipo antes de crearlo. Es lo único que impide que F4 arranque
> contra datos reales.

### F4 — Capa de datos en el frontend (0.5 día)
1. `frontend/src/lib/comandas.ts` — cliente tipado sobre el `api` existente:
   `fechas()`, `listar(fecha)`, `estadisticas(fecha)`, `importar(file)`,
   `urlReporte(tipo, fecha, folio?)` (los reportes se abren con `<a href>` normal: la cookie
   `session` viaja igual y no se pierde el `credentials:'include'`).
2. `frontend/src/types/comandas.ts`:
```ts
export type TipoComanda = 'MORTERA' | 'VIANDA'
export interface Comanda {
  comanda: string; horario: string; compania: string; destino: string
  pax: number; transporte: string; menu_1: number; menu_2: number
  tipo: TipoComanda; observaciones: string
}
export interface Estadisticas {
  total_comandas: number; total_alimentos: number
  total_menu1: number; total_menu2: number; total_mortera: number
  por_destino: Record<string, number>
  por_destino_grafico: Record<string, number>
  por_compania: Record<string, number>
  por_transporte: Record<string, number>
}
```
3. Hooks TanStack Query en `frontend/src/hooks/use-comandas.ts`:
   `useFechas()`, `useComandas(fecha)`, `useEstadisticas(fecha)`, `useImportar()`.
   `queryKey: ['comandas', 'fechas']` / `['comandas', 'lista', fecha]` /
   `['comandas', 'stats', fecha]`. `staleTime` 60 s (hereda el default de `main.tsx`).
   `invalidateQueries` de las 3 claves tras importar.

### F5 — La página `/comandas` (2 días)
Una sola ruta, un solo archivo de página + componentes. Estructura de arriba abajo:

1. `frontend/src/components/comandas/header-comandas.tsx` — título, rol, selector de fecha.
   El selector **no** es un calendario: es un `<Select>` con `useFechas()` + un botón
   "Hoy". Motivo: las fechas disponibles ya son una lista corta y exacta; un date-picker
   obligaría a un fetch para cada día que el usuario cliquea.
2. `dropzone.tsx` — react-dropzone o `<input type=file>` estilado. Acepta arrastre y clic.
   Barra de progreso durante `/importar` (180 s de timeout, ver `api.ts:6`).
   Usa `toast` para éxito/error.
3. `kpi-grid.tsx` — 6 tarjetas: Comandas, Total PAX, Menú 1, Menú 2, Morteras, Viandas.
   Colores y emojis idénticos a `app.py:1588–1595`.
4. `chart-destino.tsx` — Recharts `PieChart` con `innerRadius` (donut, `hole=0.45`),
   colores de la paleta de `app.py:1629–1631`, `#64748b` para `"AÉREOS"`.
5. `chart-transporte.tsx` — Recharts `BarChart` horizontal, `text` interior con
   `{pax}  ({pct}%)`.
6. `tablas-lateral.tsx` — `PAX por Destino` y `PAX por Compañía` como dos `Table`
   ordenadas desc (equivalen a los `st.dataframe` de 1616 y 1622).
7. `tabla-comandas.tsx` — **TanStack Table** (`@tanstack/react-table` ya instalado):
   columnas Folio, Horario, Compañía, Destino, PAX, Transporte, Menú 1, Menú 2, Tipo.
   - `ColumnDef` + `getCoreRowModel` + `getSortedRowModel` + `getFilteredRowModel`.
   - Orden por columna (el `sortable-header.tsx` ya existe).
   - Búsqueda global con `globalFilter` sobre folio/destino/compañía (equivale a 1746–1756).
   - `<Table>` con `sticky header`, `max-h-[420px] overflow-auto` y `scroll-mt` para el
     header del layout. Badge de color para `MORTERA`/`VIANDA`.
   - Click en fila → `Dialog` con el detalle completo (incl. `observaciones`, que hoy **no
     se puede ver en la UI de Streamlit**) y botón de descargar el PDF individual.
8. `reportes.tsx` — 4 botones + el individual. **Navegación por `<a href>`**, no
   `fetch` + blob: menos código y el navegador gestiona la descarga.
   Visibles según el rol (D2).
9. `alertas-vacio.tsx` — replica los estados `st.warning`/`st.info` de 1573, 1583, 1730,
   1789 (fecha sin datos, sin PDF, sin resultados de búsqueda).

**Cablear en la app existente:**
- `router.tsx`: `const Comandas = lazy(() => import('@/routes/comandas'))` + `createRoute`
  con `getParentRoute: () => protectedLayout`, `path: '/comandas'`, dentro de
  `protectedLayout.addChildren([...])`. Hereda el guard `beforeLoad` → **protegida gratis**.
- `sidebar.tsx`: agregar `'/comandas'` al union type `RouteTo` y a `navItems`
  (`{ to: '/comandas', label: 'Comandas', icon: UtensilsCrossed }`), lucide ya está.

**Salida:** `/comandas` funcional equivalente a la app Streamlit, con autenticación y layout
compartidos.

> **ESTADO 2026-10-06: F5 COMPLETADA.** Archivos nuevos:
> `frontend/src/routes/comandas.tsx` y `frontend/src/components/comandas/{tabla-comandas,
> kpi-grid, graficas, tabla-pax, dropzone, botones-reporte}.tsx`.
> Registrada en `router.tsx` (dentro de `protectedLayout`, hereda el guard) y en
> `sidebar.tsx`. `tsc --force` en 0 y `vite build` en 5.2 s; la ruta sale como chunk
> aparte de 17.9 kB gzip, lazy.
>
> **Decisiones que se apartan de la app Streamlit, a propósito:**
> 1. **La fecha es un `<select>` con la lista de `fechas_disponibles`, no un
>    calendario.** Las fechas con datos son pocas y exactas; un calendario obliga
>    a adivinar y luego a un fetch por cada día que se cliquea para acabar con
>    "no hay datos" la mitad de las veces.
> 2. **Las descargas no son `<a href>`.** Los endpoints responden **402 con JSON**
>    sin cuota; con `<a href>` el navegador navegaría a ese JSON. Se reusa
>    `descargar()` de `lib/solicitudes.ts`, al que solo se le añadió
>    `application/pdf` a `TIPOS_ARCHIVO`.
> 3. **`useEstadisticas` es un endpoint, no un `useMemo`.** El backend ya suma;
>    recalcular en el navegador sería tirar el cálculo.
> 4. **Se agregan cosas que la app no tenía:** orden por columna, y un diálogo con
>    el detalle de cada comanda (las observaciones no se veían en pantalla, solo
>    se imprimían).
>
> **Verificado contra Supabase real** (`scripts/e2e_lectura.py` y
> `scripts/verificar_datos_pantalla.py`): `erika` tiene 71 fechas, 3,140
> comandas; la del 2026-10-07 tiene 40 comandas y 429 PAX, y los cuatro
> agregados cuadran con el total. **5,544 comandas en la tabla.**
>
> **Hallazgo con datos reales:** `usuarios` tiene `PabloDG`, `LuisE` y
> `Usuario de Prueba` con MAYÚSCAS, mientras que `comandas.subido_por` solo
> tiene `erika` en minúsculas. Eso confirma que las lecturas con `ilike` son
> obligatorias: con `eq.`, un usuario cuyo nombre lleve mayúsculas no vería su
> historial.
>
> **Un bug real que solo apareció contra la base de verdad:**
> `filters=filtos` en vez de `filters=filtros` en `repository.listar`. Los tests
> de `api_comandas.py` no lo cazaban porque sustituyen el repository por dobles.
> Corregido, y `tests/test_repository.py` (29 tests) ejercita ahora el módulo
> real: es el que hubiera atrapado ese error de dedo.

### F6 — PWA y pulido (0.5 día)
1. `manifest.webmanifest`: añadir shortcut
   `{ "name": "Comandas", "short_name": "Comandas", "url": "/comandas" }` a `shortcuts`.
   **No** tocar `scope`/`start_url` (ver D1).
2. `sw.js`: subir `VERSION` de `'v3'` a `'v4'` (**obligatorio**, si no los caches viejos
   sobreviven con contenido de la versión anterior — comentario explícito en la línea 24–26)
   y añadir `/comandas` al array `PRECACHE`. No tocar las estrategias: la regla de la línea
   91 (`/api/` nunca se cachea) ya cubre los endpoints de comandas, y es exactamente la
   garantía que necesita un reporte con datos de otro usuario.
3. `changelog.ts` / `changelog-modal.tsx`: entrada de la versión.
4. Responsive: la página es de uso mayoritariamente móvil (es un PWA en plataforma).
   Grid de KPIs `grid-cols-2 md:grid-cols-3 xl:grid-cols-6`; gráficas apiladas bajo `lg`.
5. `SidebarProvider` ya resuelve el drawer móvil; no hay que hacer nada.

> **ESTADO 2026-10-06: F6 COMPLETADA.** Tres cambios:
>
> 1. **`manifest.webmanifest`**: shortcut `Comandas -> /comandas`. `scope` y
>    `start_url` NO se tocan (siguen en `/` y `/dashboard`): una ruta nueva no
>    cambia la identidad de la PWA ya instalada.
> 2. **`sw.js`: `VERSION` de `v3` a `v4`,** y `/comandas` al precache.
> 3. **`changelog.ts`: `VERSION` a `0.7`** con la entrada del módulo, para que el
>    modal de novedades se lo muestre una vez a quien ya tiene la PWA instalada.
>
> **Las ESTRATEGIAS del service worker no se tocaron, y esa es la parte
> importante.** La regla de `sw.js:91` (`url.pathname.startsWith('/api/')` →
> directo a la red) ya cubre `/api/comandas/*` sin tocar nada: es exactamente la
> garantía que necesita un reporte con datos de otro usuario.
>
> **Corrección a este plan:** el paso 2 decía "añadir `/comandas` a `PRECACHE`"
> como si aportara algo. No lo hace. La regla de navegación hace
> `fetch(request).catch(() => caches.match('/'))` — el plan B es **siempre** `/`,
> nunca la ruta pedida — así que sin esa entrada, entrar a `/comandas` sin
> conexión funciona igual. Se dejó puesta por simetría con `/dashboard`, y el
> comentario en `sw.js` lo dice para que nadie asuma una garantía que no existe.
>
> La rotación `v3` → `v4` sí sirve, pero por otro motivo: cada despliegue
> genera assets con hash nuevo y la cache de `/assets/` guarda **toda URL que se
> ha pedido alguna vez**. Los nombres viejos nunca más se piden, así que se
> acumulan solos; rotar `VERSION` los purga en `activate`.
>
> **Responsive verificado** (`scripts/verificar_layout.py`): las 8 clases de
> breakpoint existen en el CSS compilado y no hay ningún grid de 3+ columnas sin
> breakpoint. En navegador, **cero overflow horizontal** (`scrollWidth ==
> innerWidth` a 1000 px). KPIs `2 → 3 → 6` columnas; gráficas y tablas `1 → 2 →
> 3`; botones de reporte `1 → 2 → 4`.
>
> Nota sobre el script: la primera versión daba FALTA para 7 de 8 clases porque
> buscaba el texto plano. Tailwind las escribe escapadas (`.md\:grid-cols-3`), y
> un `in` sobre `md:grid-cols-3` no encuentra nada. Corregido con `_escapar()`.
> Recordatorio de que "no lo encuentro" y "no existe" son cosas distintas.

### F7 — Despliegue y cutover (0.5 día)
1. `Dockerfile` sin cambios: `requirements.txt` ya se copia y `compileall` cubre el módulo
   nuevo. Solo verificar que `pypdf` y `reportlab` estén **fijados por versión**.
2. Fly: `fly deploy`. Verificar `fly logs` sin errores de arranque (`init_db` corre en
   `on_event("startup")`, línea 48–51).
3. Validar con el golden set de F0: subir uno de los PDFs de prueba por la UI y comparar
   los 5 PDFs descargados contra los de Streamlit (`pdftotext -layout`).
4. **Rollback:** quitar la entrada del sidebar. La app Streamlit en Railway **no se toca**
   hasta cerrar D1–D4 y validar un ciclo completo de operación real.
5. **Apagado de Streamlit** (meseta, ~2 semanas después): solo entonces desactivar el
   servicio en Railway. Los datos viven en `comandas`, tabla compartida: no hay migración
   de datos que hacer.

---

## 3. Cambios en Supabase

Mínimos y no disruptivos. Los dos proyectos comparten la base, así que **nada** de esto puede
afectar a precarga2.

```sql
-- 003_comandas.sql

-- 1) VERIFICAR PRIMERO. El upsert de app.py:414 depende de este constraint.
--    Si no existe, el upsert falla y el import silenciosamente no guarda nada.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'comandas'::regclass
      AND contype = 'u'
      AND pg_get_constraintdef(oid) LIKE '%folio%subido_por%fecha_registro%'
  ) THEN
    RAISE NOTICE 'Falta el unique (folio, subido_por, fecha_registro): crearlo antes de migrar';
  END IF;
END $$;

-- 2) Índice para el patrón real de lectura: usuario + fecha desc.
--    B3 hoy escanea la tabla entera en cada rerun.
CREATE INDEX IF NOT EXISTS idx_comandas_usuario_fecha
  ON comandas (subido_por, fecha_registro DESC);

-- 3) Índice parcial del folio para la descarga individual.
CREATE INDEX IF NOT EXISTS idx_comandas_folio
  ON comandas (folio);

-- 4) RPC de fechas disponibles (sustituye traer N filas: corrige B3).
CREATE OR REPLACE FUNCTION comandas_fechas_usuario(p_usuario text)
RETURNS TABLE (fecha_registro text)
LANGUAGE sql SECURITY DEFINER AS $$
  SELECT DISTINCT c.fecha_registro
  FROM comandas c
  WHERE lower(c.subido_por) = lower(p_usuario)
    AND c.fecha_registro IS NOT NULL
  ORDER BY 1 DESC;
$$;
```

**No hacer** (y por qué):
- **No** renombrar ni reescribir `comandas` → cambiar el esquema mientras la app Streamlit
  sigue en producción parte ambas apps.
- **No** migrar `fecha_registro` de `TEXT` a `DATE` (B12). Sería lo correcto a futuro, pero
  el `upsert` de Streamlit manda strings y `ilike` no depende del tipo. Es deuda
  documentada, no un bloqueante.
- **No** activar RLS restrictive sobre `comandas` todavía. El backend de precarga2 usa
  `service_role` y aplica el filtro en código; activar RLS sin reglas `FOR SELECT` rompería
  los SELECT de ambos backends. Es el paso 2 de una fase de seguridad posterior.
- **No** tocar `usuarios`. Solo se **lee**. (D2: si un usuario debe ser `lector`, es un
  UPDATE de `rol`.)

### Corrección de B13 (anon key expuesta) — parte de esta migración
`precarga2` ya resolvió esto por diseño (`core/supabase_db.py:24–37` documenta por qué usa
`service_role`). Al absorber comandas:
- La anon key **desaparece** de este flujo: el frontend nunca habla con Supabase.
- Verificar en el dashboard de Supabase que la anon key no esté publicada en ningún cliente.
- Rotar la anon key no es necesario, pero **no debe volver a usarse** desde el backend:
  `core/supabase_db._elegir_clave()` ya cae a `SUPABASE_ANON_KEY`/`SUPABASE_KEY` como
  último recurso. Para que un despliegue con la key equivocada **falle en el arranque** en
  lugar de degradar a `USING(true)`, añadir al `startup` de `main.py` un assert:
```python
if KEY_TIPO != "service_role":
    raise RuntimeError("Se requiere SUPABASE_SERVICE_ROLE_KEY (ver core/supabase_db.py:24)")
```
> Esto **sí** es un cambio de comportamiento: hoy `precarga2` arranca con la anon key.
> Si alguien tiene un entorno que depende de eso, hay que arreglarlo antes. Verificar en el
> panel de Fly qué variable está puesta.

---

## 4. Matriz de trazabilidad app.py → precarga2

| Funcionalidad Streamlit | Ubicación nueva | Tipo de prueba |
|---|---|---|
| Login con usuario/contraseña | `core.auth` + cookie `sesiones` (ya existe) | `test_auth` de precarga2 |
| Selector de fecha | `header-comandas.tsx` (`useFechas`) | manual |
| Diagnóstico (expander) | `GET /api/comandas/diagnostico` | curl |
| Dropzone + parseo | `POST /api/comandas/importar` | `test_parser.py` (5 fixtures) |
| 6 KPI cards | `kpi-grid.tsx` | `test_stats.py` |
| Tabla PAX por destino | `tablas-lateral.tsx` | `test_stats.py` |
| Tabla PAX por compañía | `tablas-lateral.tsx` | `test_stats.py` |
| Donut por destino | `chart-destino.tsx` | visual |
| Barras por transporte | `chart-transporte.tsx` | visual |
| 4 botones de reporte | `reportes.tsx` + 5 endpoints | `test_pdf.py` |
| Tabla de comandas | `tabla-comandas.tsx` (TanStack Table) | manual |
| Búsqueda folio/destino/compañía | `globalFilter` de TanStack Table | manual |
| PDF individual | `GET /reporte/{folio}` + Dialog | `test_pdf.py` |
| Tema claro/oscuro | `index.css` + `index.html` (ya existente) | visual |
| Navbar + logout | `AppLayout` + `Sidebar` (ya existente) | — |

---

## 5. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El parser regex no detecta un PDF nuevo malformado | **Alta** | PDFs incompletos en producción | F2 golden set con 5 PDFs reales antes de tocar la API. Añadir contador `advertencias` en la respuesta de `/importar` (nº de folios en el PDF no parseados). |
| Deriva de coordenadas reportlab al portar | Media | Machote visualmente distinto | F2 `test_pdf_equivalente.py` (diff de texto) + validación visual contra los PDFs de F0. Las coordenadas se copian sin reinterpretar. |
| Subir un PDF pierde datos ya guardados | Media | Pérdida de comandas | El merge 548–551 se sustituye por `upsert` con `on_conflict`: nunca borra, solo agrega/actualiza por folio. Probarlo explícitamente en F3. |
| Colisión de folios entre usuarios | Baja | Sobrescritura cruzada | `on_conflict` incluye `subido_por`. Verificar que el **constraint único de la BD** incluye las 3 columnas (bloque 1 del SQL). |
| Coste de CPU de generar 5 PDFs | Media | Latencia en Fly (1 vCPU) | `run_in_threadpool` + `--workers 2`. Los PDFs se generan **bajo demanda** (corrige B1): el usuario ya no paga 4 PDFs por cada clic en la app. |
| Los datos en `subido_por` no coinciden con `username` | Media | Usuarios no ven sus datos | Normalizar a `username.lower()` siempre. Auditoría previa: `SELECT DISTINCT subido_por FROM comandas` vs `SELECT username FROM usuarios` y corregir las filas que no cuadren (un UPDATE, no una migración). |
| `descargas_usadas` se agota con los PDF de comandas | Media | Usuarios bloqueados | D3 antes de F3. |
| Romper precarga2 con un cambio compartido | Baja | production caída | Solo se **añade** `routers/api_comandas.py` y `include_router`. El assert de `KEY_TIPO` (sección 3) es el único cambio que altera comportamiento existente → verificar entorno Fly antes. |

---

## 6. Cronograma

| Fase | Días | Acumulado | GATE |
|---|---|---|---|
| F0 Decisiones + baseline | 0.5 | 0.5 | D1–D4 respondidas, fixtures en disco |
| F1 Extracción del dominio | 1.0 | 1.5 | Import del módulo en un REPL |
| F2 Tests golden | 1.0 | 2.5 | **Suite verde — no se avanza sin esto** |
| F3 Endpoints FastAPI | 1.0 | 3.5 | curl OK en los 10 endpoints |
| F4 Capa de datos FE | 0.5 | 4.0 | TypeScript compila |
| F5 Página `/comandas` | 2.0 | 6.0 | Equivalente funcional verificado |
| F6 PWA + responsive | 0.5 | 6.5 | ✅ PWA instalable, SW v4, shortcut |
| F7 Deploy + validación | 0.5 | 7.0 | Pendiente — requiere tu OK |
| **Meseta: operación real** | **14 días** | | Streamlit sigue vivo como red de seguridad |
| Apagado de Streamlit | 0.5 | 7.5 | Railway apagado |

**Total de desarrollo: ~7 días. La meseta no es opcional** — es el periodo en el que los
usuarios reales suben PDFs con formatos que no están en el golden set.

---

## 7. Los primeros 3 pasos concretos

1. **Hoy:** responder D1–D4 y copiar 5 PDFs reales a `precarga2/tests/fixtures/`.
   Sin esto, F2 no tiene contra qué comparar.
2. **Mañana:** `core/comandas/parser.py` + `core/comandas/fecha.py` portados tal cual, con
   `test_parser.py` en verde. Cero Streamlit, cero FastAPI, cero frontend — solo lógica
   pura movida de sitio. Es la fase más mecánica y la que más riesgo elimina.
3. **Pasado:** los 5 endpoints de PDF, envueltos en `run_in_threadpool`, con
   `test_pdf.py` comparando contra los PDFs de Streamlit. Si los PDFs salen idénticos, la
   parte más delicada del proyecto está resuelta y el resto es UI.

---

## Anexo — Notas de implementación

**`--workers 2` y CPU.** Fly `min_machines_running = 0` + `auto_stop_machines` significa
cold starts. `reportlab` es Python puro: 60 comandas × 1 página ≈ 300–600 ms. Como máximo
dos usuarios generan PDFs a la vez por máquina. Si se nota, el siguiente paso es mover la
generación a una cola, no subir workers: la app tiene pocos usuarios y los datos se leen
de Supabase, no de disco.

**Por qué NO `vite-plugin-pwa`.** El `sw.js` de precarga2 está escrito a mano con cuatro
estrategias justificadas en comentarios. `vite-plugin-pwa` con `generateSW` reescribiría
precisamente la regla que hace que este módulo sea seguro (`/api/` nunca se cachea, línea
91). Agregar Workbox es agregar peso y perder control sobre la única regla crítica.

**Por qué NO TanStack Start.** La app ya es una SPA servida por FastAPI con fallback
propio. Meter SSR debajo de `/comandas` obliga a resolver: `base` de Vite, doble caché de
assets, hidratación del `AuthProvider`, y el hecho de que FastAPI devuelve `index.html`
para *cualquier* ruta no-API (línea 130 de `main.py`) — eso es exactamente lo que hace
imposible el SSR sin reescribir el fallback.

**Por qué NO Supabase Auth.** La sesión actual funciona, tiene 24 h de expiración, usa
cookie `httponly` (no accesible desde JS, por lo que un XSS no puede robarla) y ya está
probada. Migrar a Supabase Auth obligaría a reescribir `core/auth.py` (841 líneas),
`use-auth.tsx`, los 5 endpoints de `api_auth.py` y las filas de `usuarios`. Cero beneficio
para este módulo.

**Sobre el aislamiento por usuario.** `repository.py` **siempre** aplica
`subido_por = username.lower()` y **nunca** acepta el `usuario` desde el cuerpo de la
petición. El único camino es `get_current_user(request)`. Si algún día alguien agrega un
endpoint que tome el usuario de un parámetro, el aislamiento por usuario se rompe en
silencio: es el invariante más importante del módulo, y por eso vive en el repositorio y
no en cada endpoint.
