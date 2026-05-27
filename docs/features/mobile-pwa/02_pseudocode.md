# Pseudocode: Mobile App (PWA) — F06

---

## 1. Service Worker (sw.js)

```pseudocode
CONST STATIC_CACHE = "su-static-v1"
CONST API_CACHE = "su-api-v1"
CONST PHOTO_CACHE = "su-photos-v1"

CONST PRECACHE_URLS = [
  "/web",
  "/su_project/static/src/pwa/offline.html",
  "/su_project/static/src/pwa/manifest.json",
]

// ─── Install Event ──────────────────────────────────
ON install:
  OPEN cache STATIC_CACHE
  ADD ALL PRECACHE_URLS to cache
  CALL self.skipWaiting()

// ─── Activate Event ─────────────────────────────────
ON activate:
  GET all cache keys
  FOR EACH key NOT IN [STATIC_CACHE, API_CACHE, PHOTO_CACHE]:
    DELETE cache(key)
  CALL clients.claim()

// ─── Fetch Event ────────────────────────────────────
ON fetch(request):
  url = request.url

  IF request.method != "GET":
    // Non-GET requests: try network, queue if offline
    TRY:
      response = AWAIT fetch(request.clone())
      RETURN response
    CATCH (NetworkError):
      IF url MATCHES "/api/v1/projects/*/tasks" OR "/api/v1/projects/*/photos":
        STORE request in IndexedDB sync_queue
        RETURN new Response({queued: true, offline: true}, 202)
      ELSE:
        RETURN new Response({error: "offline"}, 503)

  // Static assets: cache-first
  IF url MATCHES "*.js" OR "*.css" OR "*.woff2" OR "*.png" OR "*.svg" OR "/web/static/":
    cached = AWAIT caches.match(request)
    IF cached:
      RETURN cached
    ELSE:
      response = AWAIT fetch(request)
      IF response.ok:
        cache = AWAIT caches.open(STATIC_CACHE)
        cache.put(request, response.clone())
      RETURN response

  // Photo thumbnails: cache-first
  IF url MATCHES "/photos/*_thumb*" OR "/web/image/*":
    cached = AWAIT caches.match(request)
    IF cached:
      RETURN cached
    response = AWAIT fetch(request)
    IF response.ok:
      cache = AWAIT caches.open(PHOTO_CACHE)
      cache.put(request, response.clone())
    RETURN response

  // API GET requests: network-first with cache fallback
  IF url MATCHES "/api/v1/" OR "/web/dataset/":
    TRY:
      response = AWAIT fetch(request)
      IF response.ok:
        cache = AWAIT caches.open(API_CACHE)
        cache.put(request, response.clone())
      RETURN response
    CATCH:
      cached = AWAIT caches.match(request)
      IF cached:
        RETURN cached
      RETURN new Response({error: "offline", cached: false}, 503)

  // Default: network with offline fallback page
  TRY:
    RETURN AWAIT fetch(request)
  CATCH:
    RETURN AWAIT caches.match("/su_project/static/src/pwa/offline.html")
```

## 2. Offline Sync Manager (offline-sync.js)

```pseudocode
CLASS OfflineSyncManager:
  CONST DB_NAME = "stroyuprav-offline"
  CONST DB_VERSION = 1
  CONST STORE_SYNC_QUEUE = "sync_queue"
  CONST STORE_TASKS_CACHE = "tasks_cache"
  CONST STORE_PHOTOS_QUEUE = "photos_queue"
  CONST MAX_RETRIES = 5

  // ─── Initialize IndexedDB ──────────────────────────
  METHOD init():
    db = OPEN IndexedDB(DB_NAME, DB_VERSION)
    ON upgradeneeded:
      CREATE objectStore STORE_SYNC_QUEUE (keyPath: "id", autoIncrement: true)
        CREATE index "by_created" on "created_at"
        CREATE index "by_type" on "type"
      CREATE objectStore STORE_TASKS_CACHE (keyPath: "id")
        CREATE index "by_project" on "project_id"
      CREATE objectStore STORE_PHOTOS_QUEUE (keyPath: "id", autoIncrement: true)
        CREATE index "by_task" on "task_id"
    RETURN db

  // ─── Queue Offline Write ────────────────────────────
  METHOD queueWrite(type, endpoint, method, payload):
    entry = {
      type: type,              // "task_create" | "task_update" | "photo_upload"
      endpoint: endpoint,
      method: method,          // "POST" | "PATCH"
      payload: payload,
      created_at: Date.now(),
      retry_count: 0,
      status: "pending",
      local_id: generateUUID()
    }
    STORE entry IN STORE_SYNC_QUEUE
    SHOW toast "Сохранено офлайн. Будет отправлено при подключении."
    RETURN entry.local_id

  // ─── Queue Photo for Upload ─────────────────────────
  METHOD queuePhoto(taskId, projectId, photoBlob, metadata):
    IF COUNT(STORE_PHOTOS_QUEUE) >= 100:
      SHOW warning "Очередь фото заполнена. Подключитесь к сети для загрузки."
      RETURN null
    IF COUNT(STORE_PHOTOS_QUEUE) >= 80:
      SHOW warning "В очереди 80+ фото. Рекомендуем подключиться к сети."

    entry = {
      task_id: taskId,
      project_id: projectId,
      blob: photoBlob,         // Compressed to 2MB
      latitude: metadata.latitude,
      longitude: metadata.longitude,
      captured_at: metadata.captured_at,
      comment: metadata.comment || "",
      created_at: Date.now(),
      status: "pending"
    }
    STORE entry IN STORE_PHOTOS_QUEUE
    RETURN entry

  // ─── Sync All Pending ───────────────────────────────
  METHOD syncAll():
    IF NOT navigator.onLine:
      RETURN {synced: 0, failed: 0, reason: "offline"}

    // 1. Sync task writes (order by created_at ASC)
    pendingTasks = GET ALL FROM STORE_SYNC_QUEUE WHERE status = "pending"
                   ORDER BY created_at ASC
    synced = 0
    failed = 0

    FOR EACH entry IN pendingTasks:
      TRY:
        response = AWAIT fetch(entry.endpoint, {
          method: entry.method,
          headers: {"Content-Type": "application/json"},
          credentials: "include",   // httpOnly cookies
          body: JSON.stringify(entry.payload)
        })

        IF response.status == 409:   // Conflict — server wins
          serverData = AWAIT response.json()
          UPDATE STORE_TASKS_CACHE WITH serverData
          DELETE entry FROM STORE_SYNC_QUEUE
          synced += 1
          LOG "Conflict resolved (server wins) for", entry.type, entry.local_id

        ELSE IF response.ok:
          serverData = AWAIT response.json()
          UPDATE STORE_TASKS_CACHE WITH serverData
          DELETE entry FROM STORE_SYNC_QUEUE
          synced += 1

        ELSE IF response.status >= 500:
          entry.retry_count += 1
          IF entry.retry_count >= MAX_RETRIES:
            entry.status = "failed"
            failed += 1
          UPDATE entry IN STORE_SYNC_QUEUE

      CATCH (NetworkError):
        BREAK   // Network lost during sync, stop

    // 2. Sync photos (append-only, no conflicts)
    pendingPhotos = GET ALL FROM STORE_PHOTOS_QUEUE WHERE status = "pending"

    FOR EACH photo IN pendingPhotos:
      TRY:
        formData = new FormData()
        formData.append("file", photo.blob, "photo.jpg")
        formData.append("task_id", photo.task_id)
        formData.append("latitude", photo.latitude)
        formData.append("longitude", photo.longitude)
        formData.append("captured_at", photo.captured_at)
        formData.append("comment", photo.comment)

        response = AWAIT fetch(
          "/api/v1/projects/" + photo.project_id + "/photos",
          {method: "POST", credentials: "include", body: formData}
        )

        IF response.ok:
          DELETE photo FROM STORE_PHOTOS_QUEUE
          synced += 1
        ELSE:
          photo.retry_count = (photo.retry_count || 0) + 1
          IF photo.retry_count >= MAX_RETRIES:
            photo.status = "failed"
            failed += 1
          UPDATE photo IN STORE_PHOTOS_QUEUE

      CATCH (NetworkError):
        BREAK

    IF synced > 0:
      SHOW notification "Данные синхронизированы ({synced} элементов)"

    RETURN {synced, failed}

  // ─── Cache Tasks Locally ────────────────────────────
  METHOD cacheTasks(projectId, tasks):
    FOR EACH task IN tasks:
      PUT task IN STORE_TASKS_CACHE
    RETURN tasks.length

  // ─── Get Cached Tasks ──────────────────────────────
  METHOD getCachedTasks(projectId):
    RETURN GET ALL FROM STORE_TASKS_CACHE
           WHERE project_id = projectId

  // ─── Get Pending Count ─────────────────────────────
  METHOD getPendingCount():
    tasksPending = COUNT(STORE_SYNC_QUEUE WHERE status = "pending")
    photosPending = COUNT(STORE_PHOTOS_QUEUE WHERE status = "pending")
    RETURN {tasks: tasksPending, photos: photosPending}

  // ─── Clear On Logout ───────────────────────────────
  METHOD clearAllData():
    CLEAR STORE_SYNC_QUEUE
    CLEAR STORE_TASKS_CACHE
    CLEAR STORE_PHOTOS_QUEUE
    // Also purge API cache
    caches.delete(API_CACHE)
    LOG "All offline data cleared on logout"
```

## 3. Online/Offline Event Handler

```pseudocode
FUNCTION initConnectivityHandler(syncManager):
  // Listen for online event
  window.addEventListener("online", () =>
    SHOW banner "Подключение восстановлено. Синхронизация..."
    result = AWAIT syncManager.syncAll()
    HIDE banner AFTER 3 seconds
  )

  window.addEventListener("offline", () =>
    SHOW persistent_banner "Нет подключения. Изменения сохраняются локально."
  )

  // Periodic sync when online (every 60s)
  setInterval(() =>
    IF navigator.onLine:
      pending = syncManager.getPendingCount()
      IF pending.tasks > 0 OR pending.photos > 0:
        syncManager.syncAll()
  , 60000)
```

## 4. Push Notification Registration

```pseudocode
FUNCTION registerPushNotifications():
  IF NOT ("PushManager" in window):
    RETURN false

  IF NOT ("serviceWorker" in navigator):
    RETURN false

  registration = AWAIT navigator.serviceWorker.ready
  permission = AWAIT Notification.requestPermission()

  IF permission != "granted":
    RETURN false

  subscription = AWAIT registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
  })

  // Send subscription to server
  AWAIT fetch("/api/v1/push/subscribe", {
    method: "POST",
    credentials: "include",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: {
        p256dh: btoa(String.fromCharCode(...new Uint8Array(subscription.getKey("p256dh")))),
        auth: btoa(String.fromCharCode(...new Uint8Array(subscription.getKey("auth"))))
      }
    })
  })

  RETURN true
```

## 5. Service Worker Push Handler

```pseudocode
// In sw.js
ON push(event):
  data = event.data.json()
  options = {
    body: data.body,
    icon: "/su_project/static/src/pwa/icons/icon-192.png",
    badge: "/su_project/static/src/pwa/icons/badge-72.png",
    tag: data.tag || "su-notification",
    data: {url: data.url || "/web"},
    vibrate: [200, 100, 200],
    requireInteraction: data.priority == "high"
  }
  SHOW notification(data.title, options)

ON notificationclick(event):
  event.notification.close()
  url = event.notification.data.url
  // Focus existing window or open new
  clients = AWAIT self.clients.matchAll({type: "window"})
  FOR EACH client IN clients:
    IF client.url == url AND "focus" IN client:
      RETURN client.focus()
  RETURN clients.openWindow(url)
```
