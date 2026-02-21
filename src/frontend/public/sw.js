// HealthCentral Service Worker — Scaffold (no caching)
// TODO: Add cache strategies (cache-first for assets, network-first for API)

const CACHE_VERSION = 'v0.1.0';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only intercept same-origin GET requests; pass through all others
  // (non-GET, cross-origin requests are handled natively by the browser)
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Pass-through — no caching in scaffold version
  event.respondWith(fetch(event.request));
});
