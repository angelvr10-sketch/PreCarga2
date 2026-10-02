# Precarga Web — FastAPI + React

SPA de React 19 + Vite servida por FastAPI. El backend expone una API
JSON; el frontend se compila en el Stage 1 del Dockerfile y se sirve
como `frontend/dist` con fallback a `index.html`.

## Instalación

```bash
# Backend
pip install -r requirements.txt

# Frontend (el build debe existir en frontend/dist)
cd frontend && npm ci && npm run build && cd ..
```

En desarrollo, con recarga en caliente para ambos:

```bash
# terminal 1 — API en :8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# terminal 2 — Vite en :5173, hace proxy de /api al backend
cd frontend && npm run dev
```

## Estructura del proyecto

```
precarga_web/
├── main.py                  ← punto de entrada, middlewares, catch-all SPA
├── requirements.txt
├── Dockerfile               ← Stage 1 compila React, Stage 2 solo Python
├── core/
│   ├── __init__.py
│   ├── config.py            ← rutas, logging
│   ├── auth.py              ← sesiones, usuarios, suscripciones
│   ├── supabase_db.py       ← cliente HTTP de Supabase (PostgREST)
│   ├── db.py                ← solicitudes y personal
│   ├── procesador.py        ← toda la lógica de PDF/Excel
│   ├── stripe.py            ← planes, checkout, webhooks
│   └── catalogo.py          ← companias.csv y activos.csv
├── routers/
│   ├── auth.py              ← GET /logout de emergencia
│   ├── api.py               ← /api: upload, descarga, buscar-bajas
│   ├── api_auth.py          ← /api/auth: login, register, verify, logout, me
│   ├── api_data.py          ← /api: dashboard, catalogos, solicitudes, logs
│   └── payments.py          ← /api/checkout, /api/stripe, webhook de Stripe
├── frontend/                ← SPA React 19 + Vite + TanStack
│   ├── src/
│   │   ├── router.tsx       ← rutas con React.lazy
│   │   ├── lib/             ← cliente HTTP y endpoints
│   │   ├── routes/          ← páginas de la SPA
│   │   └── components/      ← layout y UI
│   └── dist/                ← build (generado, no se versiona)
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

Requiere que `frontend/dist` exista. Ábrelo en http://localhost:8000

## Deploy

El `Dockerfile` es multi-stage: compila el frontend con Node y produce
una imagen final solo con Python y `frontend/dist`.

```bash
docker build -t precarga .
docker run -p 8080:8080 --env-file .env precarga
```

En Fly.io:

```bash
fly launch --no-deploy      # solo la primera vez, crea la app
fly deploy
```

El build de Fly usa el Dockerfile, así que el frontend se compila
automáticamente. No hace falta commitear `frontend/dist`.

Si la app ya existe con otro nombre, renómbrala antes de desplegar
para no crear una nueva por accidente:

```bash
fly apps rename <viejo> precarga
```

## Notas importantes

- `solicitudes/` y `logs/` se crean automáticamente. En Fly el disco es
  efímera: se pierden en cada cold start, por eso no se versionan.
- Los Excel se regeneran bajo demanda desde la base de datos; el
  `.xlsx` de cada solicitud ya no se guarda en disco.
- Si `frontend/dist` no existe, el backend responde `503` con un mensaje
  explicativo en vez de un error de ruta.

