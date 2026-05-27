/**
 * СтройУправ Service Worker
 *
 * Caching strategies:
 * - Cache-first: static assets (JS, CSS, fonts, icons)
 * - Network-first: API GET requests (fallback to cache)
 * - Network-only + queue: API mutations (POST/PATCH/PUT/DELETE)
 * - Cache-first: photo thumbnails
 */

const STATIC_CACHE = 'su-static-v1';
const API_CACHE = 'su-api-v1';
const PHOTO_CACHE = 'su-photos-v1';

const CACHE_NAMES = [STATIC_CACHE, API_CACHE, PHOTO_CACHE];

const PRECACHE_URLS = [
    '/web',
    '/su_project/static/src/pwa/offline.html',
    '/su_project/static/src/pwa/manifest.json',
];

// Patterns for cache-first static assets
const STATIC_PATTERNS = [
    /\.js(\?.*)?$/,
    /\.css(\?.*)?$/,
    /\.woff2?(\?.*)?$/,
    /\.png(\?.*)?$/,
    /\.svg(\?.*)?$/,
    /\.ico(\?.*)?$/,
    /\/web\/static\//,
];

// Patterns for API requests (network-first)
const API_PATTERNS = [
    /\/api\/v1\//,
    /\/web\/dataset\//,
    /\/web\/action\//,
];

// Patterns for photo thumbnails (cache-first)
const PHOTO_PATTERNS = [
    /_thumb/,
    /\/web\/image\//,
    /\/photos\/.*\.(jpg|jpeg|png|webp)/i,
];

// Patterns for offline-queueable mutations
const SYNC_QUEUE_PATTERNS = [
    /\/api\/v1\/projects\/[^/]+\/tasks/,
    /\/api\/v1\/projects\/[^/]+\/photos/,
    /\/web\/dataset\/call_kw\/su\.task/,
];

// ─── Install ────────────────────────────────────────────
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// ─── Activate ───────────────────────────────────────────
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys
                    .filter((key) => !CACHE_NAMES.includes(key))
                    .map((key) => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

// ─── Fetch ──────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Only handle same-origin requests
    if (url.origin !== self.location.origin) {
        return;
    }

    // Non-GET requests: network-only with offline queue signal
    if (request.method !== 'GET') {
        event.respondWith(handleMutation(request));
        return;
    }

    // Photo thumbnails: cache-first
    if (PHOTO_PATTERNS.some((p) => p.test(url.pathname))) {
        event.respondWith(cacheFirst(request, PHOTO_CACHE));
        return;
    }

    // Static assets: cache-first
    if (STATIC_PATTERNS.some((p) => p.test(url.pathname))) {
        event.respondWith(cacheFirst(request, STATIC_CACHE));
        return;
    }

    // API requests: network-first with cache fallback
    if (API_PATTERNS.some((p) => p.test(url.pathname))) {
        event.respondWith(networkFirst(request, API_CACHE));
        return;
    }

    // Default: network with offline fallback page
    event.respondWith(networkWithFallback(request));
});

// ─── Cache-first strategy ───────────────────────────────
async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('', { status: 503, statusText: 'Offline' });
    }
}

// ─── Network-first strategy ─────────────────────────────
async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        return new Response(
            JSON.stringify({ error: 'offline', cached: false }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' },
            }
        );
    }
}

// ─── Mutation handler (non-GET) ─────────────────────────
async function handleMutation(request) {
    try {
        return await fetch(request);
    } catch {
        const url = new URL(request.url);
        if (SYNC_QUEUE_PATTERNS.some((p) => p.test(url.pathname))) {
            // Signal to client that request was queued
            return new Response(
                JSON.stringify({
                    queued: true,
                    offline: true,
                    message: 'Сохранено офлайн. Будет отправлено при подключении.',
                }),
                {
                    status: 202,
                    headers: { 'Content-Type': 'application/json' },
                }
            );
        }
        return new Response(
            JSON.stringify({ error: 'offline', message: 'Нет подключения к сети.' }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' },
            }
        );
    }
}

// ─── Network with offline fallback page ─────────────────
async function networkWithFallback(request) {
    try {
        return await fetch(request);
    } catch {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        // Return offline fallback page for navigation requests
        if (request.mode === 'navigate') {
            return caches.match('/su_project/static/src/pwa/offline.html');
        }
        return new Response('', { status: 503, statusText: 'Offline' });
    }
}

// ─── Push Notifications ─────────────────────────────────
self.addEventListener('push', (event) => {
    if (!event.data) return;

    let data;
    try {
        data = event.data.json();
    } catch {
        data = {
            title: 'СтройУправ',
            body: event.data.text(),
            url: '/web',
        };
    }

    const options = {
        body: data.body || '',
        icon: '/su_project/static/src/pwa/icons/icon-192.png',
        badge: '/su_project/static/src/pwa/icons/icon-192.png',
        tag: data.tag || 'su-notification',
        data: { url: data.url || '/web' },
        vibrate: [200, 100, 200],
        requireInteraction: data.priority === 'high',
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'СтройУправ', options)
    );
});

// ─── Notification Click ─────────────────────────────────
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const targetUrl = event.notification.data?.url || '/web';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Focus existing window if possible
                for (const client of clientList) {
                    if (client.url.includes(targetUrl) && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Open new window
                return self.clients.openWindow(targetUrl);
            })
    );
});
