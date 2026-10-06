/* ============================================================
   Service worker de PreCarga.

   Escrito a mano, sin Workbox ni dependencias: son cuatro estrategias y
   meter una libreria para esto seria mas peso que el propio archivo.

   El principio que manda aqui es que la API NUNCA se cachea. Todo lo que
   va a /api/ pasa directo a la red y punto:

     - /api/auth/*  -> la cookie de sesion caduca en 24 h; servir una
       respuesta vieja deja al usuario adentro de una sesion que ya no
       existe, o muestra un /auth/me cacheado de otra cuenta.
     - /api/*       -> datos de la operacion. UnAltas cacheada o una baja
       duplicada son datos equivocados, no solo datos viejos.
     - descargas    -> /api/procesar-pdf y /api/descargar responden un
       Excel generado. Cachearlos mezcla archivos de personas distintas.

   Que la app funcione sin conexion esSecondary: los datos viven en
   Supabase, asi que offline solo se puede mostrar la ultima pantalla que
   se haya cacheado. Se prioriza mostrar siempre la version actual del
   codigo antes que una experiencia offline incompleta.
   ============================================================ */

const VERSION = 'v2';
const CACHE_ACTIVOS = `precarga-${VERSION}`;
const CACHE_INMUTABLES = `precarga-inmutables-${VERSION}`;

// Solo estos. Ampliarlos a ciegas termina sirviendo index.html como si fuera
// un .js y rompiendo la app entera.
const PRECACHE = [
  '/',
  '/dashboard',
  '/manifest.webmanifest',
  '/favicon/favicon.ico',
  '/favicon/icon-192.png',
  '/favicon/icon-512.png',
  '/logos/precarga-horizontal-dark.svg',
  '/logos/precarga-icono.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_ACTIVOS)
      // addAll es atomico: si un recurso falla, no se cachea ninguno. Con
      // Promise.allSettled fallaria uno solo y la app abriria sin estetica.
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(
        claves
          .filter((k) => k !== CACHE_ACTIVOS && k !== CACHE_INMUTABLES)
          .map((k) => caches.delete(k)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Solo GET: un POST de /api/procesar-pdf no tiene nada que cachear y
  // tocarlo es pedir problemas.
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // 1) API: siempre red, nunca cache. Tampoco de fallback: si falla la red
  //    se propaga el error y la app muestra su estado de error real.
  if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) {
    return;
  }

  // 2) Los assets de Vite llevan hash en el nombre (landing-a1b2c3.js), asi
  //    que si cambia el contenido cambia la URL. Cache-first es seguro y
  //    evita un round-trip en cada carga. El servidor ya los manda con
  //    immutable de un año, asi que tampoco se revalidan.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.open(CACHE_INMUTABLES).then(async (cache) => {
        const guardado = await cache.match(request);
        if (guardado) return guardado;
        const respuesta = await fetch(request);
        if (respuesta.ok) cache.put(request, respuesta.clone());
        return respuesta;
      }),
    );
    return;
  }

  // 3) Navegacion. Network-first es lo que evita el fallo clasico de las PWA:
  //    el usuario instalado una version y se queda clavado en ella para
  //    siempre porque el index.html viejo sale del cache. Con red primero, cada
  //    arranque trae el codigo actual; el cache es solo el plan B sin conexion.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((respuesta) => {
          const copia = respuesta.clone();
          caches.open(CACHE_ACTIVOS).then((c) => c.put('/', copia));
          return respuesta;
        })
        .catch(() => caches.match('/').then((r) => r || Response.error())),
    );
    return;
  }

  // 4) El resto (iconos, logos, imagenes de la landing). Stale-while-revalidate:
  //    responde al instante con lo cacheado y refresca por detras. Aqui NO
  //    sirve cache-first porque estos archivos no llevan hash: si el logo
  //    cambia, el nombre sigue siendo el mismo y nunca se veria el nuevo.
  event.respondWith(
    caches.open(CACHE_ACTIVOS).then(async (cache) => {
      const guardado = await cache.match(request);
      const red = fetch(request)
        .then((respuesta) => {
          if (respuesta.ok) cache.put(request, respuesta.clone());
          return respuesta;
        })
        .catch(() => guardado || Response.error());
      return guardado || red;
    }),
  );
});

// Permite que la app pregunte si hay una version nueva y fuerce el refresco.
// Se usa desde el frontend; ver use-actualizacion.ts.
self.addEventListener('message', (event) => {
  if (event.data === 'skip-waiting') self.skipWaiting();
});