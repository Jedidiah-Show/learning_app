const CACHE_NAME = 'ruach-v2';
const ASSETS = [
  '/static/css/tailwind.css',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/img/ruach-icon-96.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;
  // Never cache authenticated HTML: cache keys are shared by browser profiles
  // and can otherwise expose one learner's page after account switching.
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) return;
  const isStaticAsset = url.pathname.startsWith('/static/');
  if (!isStaticAsset) return;
  event.respondWith(caches.match(request).then((cached) => {
    if (cached) return cached;
    return fetch(request).then((response) => {
      if (response.ok) caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
      return response;
    });
  }));
});
