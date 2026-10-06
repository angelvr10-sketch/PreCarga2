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

// Subir esto en CUALQUIER cambio de sw.js. Es lo unico que decide que caches
// se descartan en activate: si el archivo del worker cambia pero VERSION no,
// las caches viejas sobreviven con contenido que ya no corresponde.
const VERSION = 'v3';
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
      .then((cache) => cache.addAll(PRECACHE)),
  );
  // DELIBERADAMENTE no se llama a skipWaiting() aqui.
  //
  // Sin ese llamada, el service worker nuevo queda en estado 'waiting' y el
  // usuario recibe el aviso de version nueva, con su boton para recargar.
  // Con skipWaiting() el control cambia solo, y el aviso nunca llega a verse:
  // lo unico que se lograria es que la pestana quedara con una version vieja
  // del HTML cargada en memoria mientras el cache ya tiene los assets
  // nuevos, que es peor que no avisar.
  //
  // El salto real ocurre por mensaje, cuando el usuario acepta:
  // ver el listener de 'message' mas abajo.
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(
        claves
          .filter((k) => k !== CACHE_ACTIVOS && k !== CACHE_INMUTABLES)
          .map((k) => caches.delete(k)),
      ))
      // claim solo afecta a la primera instalacion: si no hay un SW
      // anterior, este es el unico que controla y hay que adoptarlo al
      // instante. En una actualizacion ya hay un controlador, asi que
      // claim no hace nada y el cambio llega por el mensaje del usuario.
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

// Salto de version bajo demanda.
//
// El frontend (hooks/use-actualizacion.ts) muestra el aviso de version nueva
// y, si el usuario pulsa Recargar, manda este mensaje. Ahi si se llama a
// skipWaiting: activate se encarga de limpiar los caches viejos y
// clients.claim() le pasa el control, lo que dispara 'controllerchange' en la
// pagina y ahi se hace el location.reload().
self.addEventListener('message', (event) => {
  if (event.data === 'skip-waiting') self.skipWaiting();
});