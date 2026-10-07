# Probar el módulo de Comandas en local

Todo esto corre en tu máquina. **El único punto de contacto con producción es
la base de datos de Supabase**, que es la misma de siempre (los dos proyectos
comparten `usuarios` y `comandas`).

---

## 1. Arrancar

### Para desarrollar (con recarga automática)

```bat
scripts\dev.bat
```

Abre dos ventanas. Entra a **<http://localhost:5173>**.

- El backend corre en `:8000` con `--reload`.
- El frontend corre en Vite, que recarga sola al guardar.
- El service worker **NO** se registra en este modo (a propósito, para no
  cachear el código de desarrollo).

### Para probar la PWA de verdad

```bat
scripts\ver.bat
```

Compila el frontend y lo sirve desde FastAPI, igual que en Fly. Entra a
**<http://localhost:8000>** (no 5173). **Aquí el service worker sí se
registra**, así que la app se puede instalar.

### Credenciales

```
admin / admin123
```

> `admin123` es la contraseña que crea `init_db()` al arrancar por primera vez.
> Cámbiala antes de que esto llegue a producción; es la cuenta con rol `admin`.

---

## 2. El detalle importante: `admin` no tiene comandas

`admin` es la cuenta de administración de precarga2 y **nunca ha subido un
reporte de comandas**. Si entras con ella:

- Los 6 indicadores, las gráficas y la tabla **no aparecen** (no hay nada que
  mostrar).
- Los **4 botones de descarga sí aparecen**, pero deshabilitados, con un aviso
  en amarillo que explica por qué.

Esto es a propósito. La app de Streamlit vieja ocultaba el panel entero y no
decía nada, que es peor: quien lo veía concluía "faltan los botones". Ahora se
ven los botones y se explica el motivo.

Para verlos funcionando necesitas un usuario **con datos**:

### Opción A — Entrar con `erika` (solo lectura, recomendado)

`erika` tiene **3,140 comandas en 71 fechas**. Con esa cuenta ves todo:
indicadores, gráficas, tabla y los 4 PDF descargables. No escribe nada.

Necesitas su contraseña.

### Opción B — Subir un reporte como `admin` (escribe en la BD)

**Escribe datos en la base real de Supabase**, bajo el usuario `admin`. No toca
los datos de `erika` ni de nadie más (el aislamiento es por `subido_por`), pero
quedan filas nuevas.

PDF de prueba recommended:

```
tests\fixtures\ComandaAlimentos.pdf       18 comandas, 295 PAX, 2026-07-03
```

---

## 3. Qué conviene probar

En este orden, porque cada paso depende del anterior.

### a) Que se leen bien los datos

1. Entra con `erika`.
2. Abre el sidebar → **Comandas**.
3. Comprueba:
   - La fecha por defecto es la más reciente con datos.
   - Los 6 indicadores cuadran entre sí (Total PAX = Menú 1 + Menú 2, y
     Morteras + Viandas = Total PAX).
   - La gráfica de dona tiene sectores, y la leyenda cuadra con la tabla de
     destinos.
   - La tabla lista 40 comandas para el 07/10/2026.

### b) La búsqueda y el detalle

1. Escribe `ABKATUN` en el buscador → la tabla se filtra.
2. Escribe algo que no exista → "Sin resultados".
3. **Clic en una fila** → abre el diálogo con el detalle.
4. Fíjate en el campo **Observaciones**: en la app vieja de Streamlit esto
   *nunca se veía en pantalla*, solo se imprimía en el PDF. Ahora sí.

### c) Los PDF (esto es lo importante)

Cada botón genera el PDF **en ese momento**. Nada se genera al abrir la
pantalla (la app vieja generaba los cuatro en cada clic, aunque nadie los
abriera).

| Botón | Qué produce | Nombre del archivo |
|---|---|---|
| **Reporte Estadístico** | Una hoja: dona de destino, barras de transporte, tabla de compañías | `Reporte_Estadistico_REFORMA_PEMEX.pdf` |
| **Todas las Comandas** | **Un solo PDF con todas**, una comanda por página, con el machote completo (encabezado, tabla de datos, tablas de utensilios, 4 pares de firmas) | `Todas_las_Comandas_REFORMA_PEMEX.pdf` |
| **Comandas c/ Mortera** | **Otro diseño del mismo PDF**: todas las comandas, una por página, pero las de tipo MORTERA traen las 6 líneas de firma de control adicionales | `Comandas_Mortera_REFORMA_PEMEX.pdf` |
| **Vales de Alimentos** | 10 vales por hoja, con la firma de recepción de ADMINISTRACION | `Vales_Alimentos_REFORMA_PEMEX.pdf` |

Comprobado contra la base real con las 40 comandas del 07/10/2026:

```
estadistico    1 pag   Reporte_Estadistico_REFORMA_PEMEX.pdf
todas         40 pag   Todas_las_Comandas_REFORMA_PEMEX.pdf
mortera       40 pag   Comandas_Mortera_REFORMA_PEMEX.pdf
vales          4 pag   Vales_Alimentos_REFORMA_PEMEX.pdf
```

**Compara el PDF que descargas con el de la app vieja.** Si el papel es
distinto en algo, dímelo: las coordenadas están verificadas contra un PDF real
de la app, pero un cambio en la fuente sería lo primero en notarse.

Cada descarga descuenta una del contador. Con 40 comandas el PDF de "todas" es
de 40 páginas: no lo abras esperando algo corto.

### d) La cuota de descargas

Cada PDF que descargas descuenta una del contador del usuario. Para agotar las
30 gratuitas tendrías que descargar 30 veces.

Si quieres verlo funcionar sin gastarte la cuota:

```sql
-- En el SQL Editor de Supabase
UPDATE usuarios
SET descargas_usadas = 30
WHERE username = 'erika';
```

Con eso, el siguiente PDF debe responder **"No tenés descargas disponibles"**
y *no* descargarse. Después lo devuelves a 0.

> Ojo: al agotarse, el botón igual genera el PDF en el servidor antes de
> responder 402. Es un desperdicio menor de CPU que decidí no optimizar: en Fly
> con 1 vCPU son ~300 ms por reporte.

### e) La subida de un reporte

**Esto escribe en la base real.** Si decides probarlo:

1. Arrastra un PDF sobre la zona punteada (o haz clic y búscalo).
2. Deberías ver un toast verde con el número de comandas y el PAX.
3. La pantalla se actualiza sola: no hay que recargar.
4. **Vuelve a subir el MISMO archivo.** El toast debe decir lo mismo y la tabla
   debe seguir con las mismas comandas, **no duplicadas**. Ese es el
   comportamiento del `upsert`.

Si ves folios duplicados después de subir dos veces el mismo archivo, **para
inmediatamente**: significaría que el índice único
`(folio, subido_por, fecha_registro)` no está aplicado.

### f) La PWA

Con `scripts\ver.bat` (modo producción):

1. Chrome o Edge → menú → **"Instalar app"**.
2. Ábrela desde el icono y verifica que abre en ventana propia.
3. Mantén presionado el ícono en el escritorio (Android) o clic derecho en el
   ícono (escritorio) → debería aparecer el atajo **Comandas**.

---

## 4. Qué mirar con más cuidado

No es todo lo mismo de confiable. Esto es lo que yo NO pude verificar:

| Cosa | Por qué hay que probarla a mano |
|---|---|
| **El arrastre de archivos desde el celular** | Es el uso principal de esta app y depende del navegador y del sistema operativo. En mi prueba no pude arrastrar un archivo real. |
| **La cuota agotada** | Requieremanyas descargas o tocar la base a mano. |
| **Los PDF en papel** | Verifiqué que el texto y la geometría coinciden con un PDF real de la app. Lo que no puedo verificar es el papel en la mano. |
| **El diálogo en pantalla angosta** | En mi prueba a 1000 px no hubo desborde, pero no pude probar 375 px (teléfono). |

Si encuentras algo raro, lo más probable es que esté en el frontend. Los datos
del backend están verificados contra Supabase real:

```
erika: 71 fechas, 3,140 comandas
2026-10-07: 40 comandas, 429 PAX
5,544 comandas en total en la tabla
```

---

## 5. Si algo falla

**"Configuración incompleta: define SUPABASE_URL y SUPABASE_KEY"**

No cargó el `.env`. Se carga desde `main.py` con `load_dotenv`, así que tiene
que arrancarse con uvicorn desde la raíz del proyecto, no desde `frontend/`.

**La pantalla sale en blanco y el sidebar no aparece**

Casi siempre es que el backend no está corriendo. Mira la ventana del backend:
si tiene un error de importación, el frontend recibe un 500 y no puede pintar
nada. En `scripts\ver.bat` se compila antes de arrancar justamente para no
levantar con un bundle roto.

**"La app no se instala" (PWA)**

El service worker solo se registra en producción. En `dev.bat` (Vite, `:5173`)
no hay service worker, y es intencional. Usa `ver.bat` (`:8000`).

**El ícono de la PWA sigue siendo el viejo**

Borrar las caches del sitio desde las herramientas de desarrollo, o recargar
con "vaciar caché y recargar". El service worker rota el nombre de las caches
en cada despliegue, pero el navegador puede tener la anterior en disco.

---

## 6. Revertir

Nada de esto toca la base de datos salvo lo que subas tú. Para deshacer una
subida de prueba:

```sql
-- Borra SOLO lo que subió admin
DELETE FROM comandas WHERE subido_por = 'admin';
```

O más quirúrgico, por fecha:

```sql
DELETE FROM comandas
WHERE subido_por = 'admin' AND fecha_registro = '2026-07-03';
```

Y para devolver la cuota:

```sql
UPDATE usuarios SET descargas_usadas = 0 WHERE username = 'erika';
```

---

## 7. Requisitos

Si algo no arranca, verifica:

```bat
REM Python y dependencias del backend
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -m pip install -r requirements.txt

REM Node y dependencias del frontend
cd frontend
node --version
npm install
```

Y los tests, que no necesitan nada corriendo:

```bat
.venv\Scripts\python.exe -m pytest
```

Deben salir **267 tests verdes**.

---

## 8. Other scripts

No hacen falta para usar la app, pero sirven para verificar cosas sin
abrir el navegador:

| Script | Para qué |
|---|---|
| `python scripts/comparar_pdf.py` | Compara los 5 PDF contra la app de Streamlit vieja. Debe salir `IDENTICO` en los 5. |
| `python scripts/comparar_golden.py` | Compara las 30 páginas del golden real, texto **y posición**. Debe salir `30/30`. |
| `python scripts/comparar_parser.py` | Compara el parser contra el de la app vieja. |
| `python scripts/e2e_lectura.py [usuario] [-]` | Endpoint por endpoint contra Supabase real, sin escribir nada. |
| `python scripts/verificar_layout.py` | Que las clases responsive existan en el CSS compilado. |
| `python scripts/verificar_datos_pantalla.py [usuario]` | Que los datos tengan la forma que espera el frontend. |
| `python scripts/buscar_fixtures.py [carpeta]` | Busca PDF con forma de reporte de comandas. |

Los que hablan con la BD (`e2e_lectura`, `verificar_datos_pantalla`) necesitan
el `.env`; para eso se importan `main` o se arrancan vía `main.py`.
