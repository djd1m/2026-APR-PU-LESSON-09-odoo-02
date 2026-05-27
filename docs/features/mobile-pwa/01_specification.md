# Specification: Mobile App (PWA) — F06

**Feature ID:** F06
**Status:** Draft
**Date:** 2026-05-27

---

## 1. Functional Requirements

### FR-MOB-01: Progressive Web App Shell

Install-capable PWA with `manifest.json` providing:
- `name`: "СтройУправ"
- `short_name`: "СтройУправ"
- `start_url`: "/web"
- `display`: "standalone"
- `theme_color`: "#1B5E20" (construction green)
- `background_color`: "#FFFFFF"
- Icons: 192x192, 512x512 (PNG, maskable)
- Splash screen auto-generated from manifest

Service Worker registered at scope `/` via Odoo asset pipeline.

### FR-MOB-02: Offline-First Architecture

| Data Type | Offline Capability | Storage | Sync Strategy |
|-----------|-------------------|---------|---------------|
| Tasks | Read + Write | IndexedDB | Network-first read, background sync write |
| Photos | Write only | IndexedDB (blob) | Append-only, background sync upload |
| Project data | Read only | IndexedDB | Cache-first with stale-while-revalidate |
| Estimates | Read only | Not cached offline | Network-only |

**Sync queue requirements:**
- All offline writes stored in IndexedDB `sync_queue` object store
- Each entry: `{id, type, endpoint, method, payload, created_at, retry_count}`
- Max retry: 5 attempts with exponential backoff (1s, 5s, 25s, 125s, 625s)
- Conflict resolution: **server wins** for task data, **append** for photos
- Sync triggered on: `online` event, periodic (every 60s when online), manual pull-to-refresh

### FR-MOB-03: Service Worker Caching Strategy

| Resource Type | Strategy | Cache Name | Max Age |
|---------------|----------|-----------|---------|
| App shell (HTML, JS, CSS) | Cache-first | `su-static-v1` | Until SW update |
| Odoo OWL assets | Cache-first | `su-assets-v1` | Until SW update |
| API GET responses | Network-first, fallback to cache | `su-api-v1` | 5 minutes |
| API POST/PATCH/PUT | Network-only, queue if offline | N/A (IndexedDB) | N/A |
| Photos/thumbnails | Cache-first | `su-photos-v1` | 30 days |
| Fonts, icons | Cache-first | `su-static-v1` | Until SW update |

**Precaching:** manifest.json, offline fallback page, app shell critical path.

### FR-MOB-04: Push Notifications (Web Push API)

| Event | Notification Content | Priority |
|-------|---------------------|----------|
| Task assigned | "Новая задача: {title}" | High |
| Task status changed | "Задача '{title}' -> {status}" | Normal |
| Budget AI-alert | "Перерасход на объекте {project}: {pct}%" | High |
| Comment with @-mention | "{author}: {comment_preview}" | Normal |

**Technical:**
- VAPID key pair generated server-side, stored as env vars
- Push subscription stored in `su_push_subscription` table (user_id, endpoint, p256dh, auth)
- Server sends via `pywebpush` library from Celery worker
- User can manage notification preferences per category

### FR-MOB-05: Mobile-Optimized UI

- Viewport: 320-428px optimized
- Touch targets: minimum 44x44px
- Bottom navigation bar: Объекты | Задачи | Фото | Профиль
- Swipe gestures: swipe-right on task to change status
- Pull-to-refresh on all list views
- Offline indicator banner at top when disconnected

### FR-MOB-06: Camera Access

- `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })`
- Fallback to `<input type="file" accept="image/*" capture="environment">`
- Client-side compression to 2MB (quality 80%) before upload/storage
- EXIF GPS extraction for geotag

---

## 2. Non-Functional Requirements

| ID | Requirement | Metric |
|----|-------------|--------|
| NFR-PWA-01 | Lighthouse PWA score | >= 90 |
| NFR-PWA-02 | Offline availability | Tasks readable within 1s offline |
| NFR-PWA-03 | Sync latency | < 60s after reconnection |
| NFR-PWA-04 | Install prompt | Shown after 2nd visit |
| NFR-PWA-05 | Storage quota | < 50MB for app data (excluding photos) |
| NFR-PWA-06 | Photo queue size | Max 100 photos queued offline (auto-warn at 80) |

---

## 3. Security Requirements

| ID | Requirement |
|----|-------------|
| SEC-PWA-01 | IndexedDB data encrypted at rest via browser-native encryption (no custom crypto) |
| SEC-PWA-02 | No auth tokens stored in IndexedDB or localStorage — httpOnly cookies only |
| SEC-PWA-03 | Service Worker scope restricted to same-origin |
| SEC-PWA-04 | CSP headers updated to allow Service Worker registration |
| SEC-PWA-05 | Offline cached API responses purged on logout |
| SEC-PWA-06 | VAPID keys stored as environment variables, never hardcoded |
| SEC-PWA-07 | Push subscription endpoint validated server-side |

---

## 4. Acceptance Criteria

```
US-12: Работа офлайн на объекте

AC-1: GIVEN устройство offline
      THEN доступны: просмотр задач, создание задач, фотофиксация
AC-2: GIVEN устройство вернулось online
      THEN все изменения синхронизируются автоматически в течение 60 сек
AC-3: GIVEN конфликт данных (offline edit + server edit)
      THEN серверная версия побеждает для данных; фото добавляются (append)
AC-4: GIVEN синхронизация завершена
      THEN пользователь видит уведомление «Данные синхронизированы»
AC-5: GIVEN PWA installed
      THEN bottom navigation renders correctly on 320px viewport
AC-6: GIVEN push notification received
      THEN clicking notification opens relevant task/project view
```

---

## 5. Dependencies

| Dependency | Type | Notes |
|-----------|------|-------|
| F03 Task Management | Required | Offline task read/write |
| F04 Photo Reports | Required | Offline photo capture/queue |
| F08 Auth & Billing | Required | httpOnly cookie auth for SW |
| HTTPS | Required | Service Worker requires secure context |
