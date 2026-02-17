// HealthCentral Service Worker — Scaffold (no caching)
// TODO: Add cache strategies (cache-first for assets, network-first for API)

const CACHE_VERSION = 'v0.1.0';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Pass-through — no caching in scaffold version
  event.respondWith(fetch(event.request));
});
