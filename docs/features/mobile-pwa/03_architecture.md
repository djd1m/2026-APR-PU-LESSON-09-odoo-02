# Architecture: Mobile App (PWA) — F06

---

## 1. Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (PWA)                         │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │  OWL Frontend    │  │  PWA Shell                        │ │
│  │  (Odoo views)    │  │                                   │ │
│  │                  │  │  ┌──────────┐ ┌────────────────┐ │ │
│  │  - Task views    │  │  │ manifest │ │ offline-sync   │ │ │
│  │  - Project views │  │  │ .json    │ │ .js            │ │ │
│  │  - Photo views   │  │  └──────────┘ │                │ │ │
│  │                  │  │               │ - IndexedDB    │ │ │
│  └──────┬───────────┘  │  ┌──────────┐│ - Sync queue   │ │ │
│         │              │  │ sw.js    ││ - Photo queue  │ │ │
│         │              │  │          ││ - Task cache   │ │ │
│         │              │  │ - Cache  │└────────────────┘ │ │
│         │              │  │ - Fetch  │                   │ │
│         │              │  │ - Push   │                   │ │
│         │              │  │ - Sync   │                   │ │
│         │              │  └──────────┘                   │ │
│         │              └─────────────────────────────────┘ │
└─────────┼──────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                         Nginx                                │
│  - Service-Worker-Allowed header                             │
│  - Cache-Control for SW assets                               │
│  - /pwa/* static files                                       │
└────────┬───────────────────────────────────────┬─────────────┘
         │                                       │
┌────────▼────────┐                   ┌──────────▼────────────┐
│  Odoo Backend   │                   │  FastAPI AI Service   │
│                 │                   │                       │
│  - Task CRUD    │                   │  - Push notification  │
│  - Photo upload │                   │    sender (Celery)    │
│  - Project data │                   │                       │
│  - Push sub.    │                   │                       │
└─────────────────┘                   └───────────────────────┘
```

## 2. File Structure

```
custom-addons/su_project/
├── static/
│   └── src/
│       └── pwa/
│           ├── manifest.json          # PWA manifest
│           ├── sw.js                  # Service Worker
│           ├── offline-sync.js        # IndexedDB sync manager
│           ├── pwa-register.js        # SW registration + push setup
│           ├── offline.html           # Offline fallback page
│           └── icons/
│               ├── icon-192.png       # PWA icon 192x192
│               ├── icon-512.png       # PWA icon 512x512
│               └── badge-72.png       # Notification badge
├── views/
│   └── su_pwa_templates.xml           # Odoo template to inject manifest/SW
└── tests/
    └── test_pwa_sync.py               # Server-side sync endpoint tests
```

## 3. Data Flow: Offline Write + Sync

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────┐
│  User   │────▶│ OWL Frontend │────▶│ offline-sync  │────▶│IndexedDB│
│ (offline)│     │ (create task)│     │ queueWrite()  │     │sync_queue│
└─────────┘     └──────────────┘     └──────────────┘     └────┬────┘
                                                                │
                                          ┌─────────────────────┘
                                          │ (online event)
                                          ▼
                                     ┌──────────────┐
                                     │ syncAll()    │
                                     │              │
                                     │ FOR EACH     │
                                     │  pending     │──── POST /api/v1/tasks
                                     │  entry       │          │
                                     └──────────────┘          ▼
                                                          ┌─────────┐
                                                          │ Server  │
                                                          │ 200 OK  │──▶ Delete from queue
                                                          │ 409     │──▶ Server wins, update cache
                                                          │ 5xx     │──▶ Retry (max 5)
                                                          └─────────┘
```

## 4. IndexedDB Schema

```
Database: "stroyuprav-offline" (version 1)

ObjectStore: sync_queue
  keyPath: "id" (autoIncrement)
  indexes:
    - "by_created" -> "created_at"
    - "by_type" -> "type"
  Entry shape:
    {
      id: auto,
      type: string,        // "task_create" | "task_update" | "task_status"
      endpoint: string,    // API URL
      method: string,      // "POST" | "PATCH"
      payload: object,     // Request body
      created_at: number,  // timestamp
      retry_count: number,
      status: string,      // "pending" | "syncing" | "failed"
      local_id: string     // UUID for optimistic UI
    }

ObjectStore: tasks_cache
  keyPath: "id"
  indexes:
    - "by_project" -> "project_id"
  Entry shape: Task API response object

ObjectStore: photos_queue
  keyPath: "id" (autoIncrement)
  indexes:
    - "by_task" -> "task_id"
  Entry shape:
    {
      id: auto,
      task_id: string,
      project_id: string,
      blob: Blob,          // Compressed JPEG
      latitude: number,
      longitude: number,
      captured_at: string,
      comment: string,
      created_at: number,
      retry_count: number,
      status: string       // "pending" | "uploading" | "failed"
    }
```

## 5. Nginx Configuration for PWA

Required headers and location blocks:

```nginx
# PWA manifest
location = /su_project/static/src/pwa/manifest.json {
    add_header Cache-Control "no-cache";
    add_header Content-Type "application/manifest+json";
}

# Service Worker — must be served from root scope
location = /sw.js {
    alias /path/to/custom-addons/su_project/static/src/pwa/sw.js;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Service-Worker-Allowed "/";
    add_header Content-Type "application/javascript";
}

# PWA static assets
location /su_project/static/src/pwa/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
}
```

## 6. Push Notification Architecture

```
┌──────────┐   subscribe   ┌──────────┐   store   ┌──────────────┐
│  Browser │──────────────▶│ Odoo API │─────────▶│ su_push_sub  │
│  (PWA)   │               │          │           │ (PostgreSQL) │
└──────────┘               └──────────┘           └──────┬───────┘
                                                         │
    ┌────────────────────────────────────────────────────┘
    │ (task assigned, status changed, etc.)
    ▼
┌──────────────┐  pywebpush  ┌───────────────┐  HTTP  ┌──────────┐
│ Celery Worker│────────────▶│ Push Service  │───────▶│ Browser  │
│ (send_push)  │             │ (FCM/Mozilla) │        │ (SW)     │
└──────────────┘             └───────────────┘        └──────────┘
```

## 7. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| XSS via cached responses | CSP header blocks inline scripts; SW only caches same-origin |
| Token leakage in IndexedDB | No tokens stored — httpOnly cookies used for all requests |
| Stale cached data after logout | `clearAllData()` called on logout; all caches + IndexedDB purged |
| SW update propagation | `skipWaiting()` + `clients.claim()` for immediate activation |
| Sensitive data in cache | API cache entries have 5-min TTL; purged on logout |
| Push endpoint spoofing | Server validates subscription endpoint format before storing |

## 8. Integration Points

| System | Integration | Direction |
|--------|------------|-----------|
| Odoo OWL | manifest.json link + SW registration script injected via `web.assets_frontend` | Frontend -> Browser |
| Odoo API | Task CRUD, Photo upload via existing REST endpoints | PWA -> Server |
| Celery | Push notification dispatch via `send_push_notification` task | Server -> Browser |
| Nginx | SW scope headers, manifest MIME type, PWA asset caching | Proxy -> Browser |
