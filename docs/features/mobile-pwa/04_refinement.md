# Refinement: Mobile App (PWA) — F06

---

## 1. Edge Cases

### 1.1 Offline Sync Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | User edits task offline, another user deletes same task on server | Sync returns 404 -> remove from local queue, show "Задача была удалена другим пользователем" |
| 2 | User creates task offline, goes online, creates same task again online | Each creation has unique `local_id` -> both sent, server deduplicates by `local_id` if implemented, otherwise two tasks created |
| 3 | User offline for 7+ days, auth cookie expires | On sync attempt, 401 returned -> redirect to login, preserve queue for post-login sync |
| 4 | Photo queue reaches 100 items | Block new photos, show warning "Освободите место: подключитесь к сети для загрузки фото" |
| 5 | Large photo (20MB) before compression fails to compress | Fallback: store original, compress on sync attempt; if still too large -> error "Фото слишком большое" |
| 6 | IndexedDB quota exceeded | Catch QuotaExceededError -> warn user, purge oldest tasks_cache entries, keep sync_queue intact |
| 7 | Multiple tabs open, sync runs in both | Use IndexedDB transaction locking; first tab acquires lock, second skips |
| 8 | Network drops mid-sync (partial sync) | Each entry synced individually; completed entries removed; remaining stay in queue for next attempt |
| 9 | Server returns 409 conflict on task update | Accept server version (server wins), update local cache, notify user "Задача обновлена на сервере" |
| 10 | User logs out with pending sync items | Warn "У вас X несохранённых изменений. Выйти?" -> if confirmed, clear all data |

### 1.2 Service Worker Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | SW update available while user is mid-task | New SW waits until all tabs closed, then activates; no interruption |
| 2 | Cache storage full | Evict oldest entries from `su-photos-v1` first, then `su-api-v1` |
| 3 | SW registration fails (non-HTTPS dev env) | Graceful degradation: app works without offline support; log warning |
| 4 | Push permission denied | Record in user preferences; don't re-prompt; show in-app notifications instead |
| 5 | Third-party script loaded by Odoo | SW only intercepts same-origin requests; third-party passes through |

### 1.3 UI Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | Viewport < 320px (very old device) | Horizontal scroll allowed; no layout breakage |
| 2 | iOS Safari PWA restrictions | No push notifications on iOS < 16.4; detect and hide push UI |
| 3 | Android Chrome back button | Browser back navigates within PWA correctly via History API |
| 4 | Screen reader (accessibility) | All touch targets have ARIA labels; offline banner has role="alert" |

---

## 2. Error Handling

| Error | HTTP Code | User Message | Recovery |
|-------|-----------|-------------|----------|
| Network timeout during sync | - | "Медленное соединение. Попробуем позже." | Retry in 60s |
| Auth cookie expired | 401 | "Сессия истекла. Войдите заново." | Redirect to login, preserve queue |
| Server error during sync | 500 | "Ошибка сервера. Данные сохранены локально." | Retry with backoff |
| Photo upload too large | 413 | "Фото слишком большое после сжатия." | Skip photo, mark failed |
| IndexedDB unavailable | - | "Офлайн-режим недоступен в этом браузере." | Graceful degradation |
| Push subscription failed | - | (Silent) | Log error, in-app notifications fallback |
| SW registration failed | - | (Silent) | App works without offline; log warning |
| Conflict on task update | 409 | "Задача обновлена другим пользователем. Применена серверная версия." | Update local cache |

---

## 3. Performance Optimizations

| Optimization | Impact | Implementation |
|-------------|--------|----------------|
| Photo compression client-side | Reduce upload 10x (20MB -> 2MB) | Canvas API, quality 80%, max 1920px |
| Precache critical path | Instant load from cache | SW install event caches app shell |
| IndexedDB batch operations | Faster sync for 10+ items | Transaction batching in syncAll() |
| Lazy SW registration | Don't block initial page load | Register after `window.onload` |
| Stale-while-revalidate for tasks | Instant display + background refresh | Show cached, fetch new in background |

---

## 4. Testing Strategy

### 4.1 Unit Tests

| Test | What | Tool |
|------|------|------|
| queueWrite stores entry | IndexedDB write | Jest + fake-indexeddb |
| syncAll sends pending entries | Network calls in order | Jest + MSW |
| syncAll handles 409 (server wins) | Conflict resolution | Jest + MSW |
| syncAll handles network error | Stops processing, preserves queue | Jest |
| getPendingCount returns correct counts | Counter accuracy | Jest + fake-indexeddb |
| clearAllData purges everything | Logout cleanup | Jest + fake-indexeddb |

### 4.2 Integration Tests

| Test | What | Tool |
|------|------|------|
| SW caches static assets on install | Cache population | Playwright |
| SW serves cached response when offline | Offline read | Playwright |
| SW queues POST when offline | Offline write | Playwright |
| Full offline-online-sync cycle | End-to-end sync | Playwright |
| Push notification received and displayed | Push API | Playwright |

### 4.3 Server-Side Tests

| Test | What | Tool |
|------|------|------|
| POST /api/v1/push/subscribe stores subscription | Push registration | pytest |
| Push notification sent on task assignment | Celery task trigger | pytest + celery test |
| Conflict detection returns 409 | Concurrent edit handling | pytest |
| Sync endpoint handles batch operations | Multiple writes | pytest |

---

## 5. Browser Compatibility

| Feature | Chrome 90+ | Safari 16.4+ | Firefox 90+ | Samsung Internet |
|---------|:----------:|:------------:|:-----------:|:----------------:|
| Service Worker | Yes | Yes | Yes | Yes |
| IndexedDB | Yes | Yes | Yes | Yes |
| Push Notifications | Yes | Yes (16.4+) | Yes | Yes |
| Cache API | Yes | Yes | Yes | Yes |
| Background Sync | Yes | No | No | Yes |
| `navigator.onLine` | Yes | Yes | Yes | Yes |
| `beforeinstallprompt` | Yes | No (auto) | No | Yes |

**Note:** For browsers without Background Sync API, we use the periodic
`setInterval` approach (every 60s) as fallback.
