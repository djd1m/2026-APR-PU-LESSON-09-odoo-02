# Completion Checklist: Mobile App (PWA) — F06

---

## 1. Implementation Checklist

### 1.1 PWA Core Files

- [ ] `custom-addons/su_project/static/src/pwa/manifest.json` — PWA manifest with name, icons, start_url, display: standalone
- [ ] `custom-addons/su_project/static/src/pwa/sw.js` — Service Worker with cache-first/network-first strategies
- [ ] `custom-addons/su_project/static/src/pwa/offline-sync.js` — IndexedDB queue manager for offline writes
- [ ] `custom-addons/su_project/static/src/pwa/pwa-register.js` — SW registration + push notification setup
- [ ] `custom-addons/su_project/static/src/pwa/offline.html` — Offline fallback page (Russian text)
- [ ] `custom-addons/su_project/static/src/pwa/icons/icon-192.png` — PWA icon 192x192
- [ ] `custom-addons/su_project/static/src/pwa/icons/icon-512.png` — PWA icon 512x512

### 1.2 Odoo Integration

- [ ] `su_pwa_templates.xml` — Odoo QWeb template injecting `<link rel="manifest">` and SW registration script into `web.assets_frontend`
- [ ] `__manifest__.py` updated — new template added to `data` list

### 1.3 Nginx Configuration

- [ ] `nginx/conf.d/default.conf` updated — SW scope header, manifest MIME type, PWA asset caching rules

### 1.4 Server-Side (Push Notifications)

- [ ] Push subscription model (`su_push_subscription`) or endpoint
- [ ] Celery task for sending push notifications
- [ ] VAPID key generation documented in DEVELOPMENT_GUIDE.md

### 1.5 Tests

- [ ] `test_pwa_sync.py` — server-side push subscription and notification tests
- [ ] Manual test: install PWA on Android Chrome
- [ ] Manual test: offline task creation + sync
- [ ] Manual test: offline photo capture + sync
- [ ] Manual test: push notification received

---

## 2. Acceptance Criteria Verification

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Offline: view tasks, create tasks, take photos | Pending |
| AC-2 | Auto-sync within 60s of reconnection | Pending |
| AC-3 | Server wins for data conflicts, append for photos | Pending |
| AC-4 | "Данные синхронизированы" notification after sync | Pending |
| AC-5 | Bottom nav renders on 320px viewport | Pending |
| AC-6 | Push notification click opens relevant view | Pending |

---

## 3. Security Verification

| Check | Status |
|-------|--------|
| No tokens in IndexedDB/localStorage | Pending |
| Cached API responses purged on logout | Pending |
| CSP allows SW registration | Pending |
| VAPID keys from env vars, not hardcoded | Pending |
| SW scope same-origin only | Pending |

---

## 4. Documentation

- [ ] This SPARC feature documentation (01-05)
- [ ] Validation report
- [ ] Review report
- [ ] DEVELOPMENT_GUIDE.md updated with PWA setup instructions
- [ ] Nginx PWA headers documented

---

## 5. Definition of Done

1. All PWA core files created and functional
2. Service Worker registers and caches app shell
3. Offline task read/write works with IndexedDB queue
4. Offline photo capture queues for upload
5. Sync resolves conflicts (server wins for data, append for photos)
6. Push notifications delivered for task assignment
7. Mobile UI renders correctly on 320-428px viewports
8. Nginx configured with PWA headers
9. All tests pass
10. Security review completed (no tokens in storage, cache purged on logout)
