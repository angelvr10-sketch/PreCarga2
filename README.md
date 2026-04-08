# Precarga SHAT Web — FastAPI + HTMX

## Instalación

```bash
pip install -r requirements.txt
```

## Estructura del proyecto

```
precarga_web/
├── main.py                  ← punto de entrada
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── config.py            ← rutas, logging
│   ├── procesador.py        ← toda la lógica de PDF/Excel
│   └── catalogo.py          ← companias.csv y activos.csv
├── routers/
│   ├── pages.py             ← páginas HTML completas
│   ├── api.py               ← endpoints JSON (upload, descarga)
│   └── htmx.py              ← fragmentos HTML parciales (CRUD inline)
├── templates/
│   ├── base.html            ← layout con sidebar
│   ├── dashboard.html
│   ├── procesar.html
│   ├── altas.html
│   ├── bajas.html
│   ├── companias.html
│   ├── activos.html
│   ├── logs.html
│   └── partials/
│       ├── solicitudes.html
│       ├── tabla_companias.html
│       └── lista_activos.html
├── static/
│   ├── css/app.css
│   └── js/app.js
└── lib/                     ← plantillas Excel y catálogos CSV
    ├── plantilla.xlsx
    ├── salida.xlsx
    ├── entrada.xlsx
    ├── companias.csv
    └── activos.csv
```

## Archivos necesarios en lib/

Copia desde tu proyecto desktop:
- `lib/plantilla.xlsx`
- `lib/salida.xlsx`
- `lib/entrada.xlsx`
- `lib/companias.csv`
- `lib/activos.csv`

## Correr en desarrollo

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Abrir → http://localhost:8000

## Deploy en Railway

1. Sube el proyecto a GitHub
2. Crea un nuevo proyecto en Railway → Deploy from GitHub
3. Railway detecta automáticamente el `requirements.txt`
4. Agrega variable de entorno:
   ```
   PORT=8000
   ```
5. Agrega un `Procfile`:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

## Notas importantes

- La carpeta `solicitudes/` se crea automáticamente y es donde se guardan los Excel generados
- La carpeta `logs/` guarda los logs del día actual
- Los archivos `_salidas_*.xlsx` y `_entradas_*.xlsx` generados se guardan en `solicitudes/` y se descargan automáticamente
- En producción con múltiples usuarios, la BD cargada en Bajas se almacena en memoria por sesión (token) — se pierde al reiniciar el servidor
