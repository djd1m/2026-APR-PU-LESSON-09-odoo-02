/**
 * СтройУправ Offline Sync Manager
 *
 * IndexedDB-based queue for offline task writes and photo uploads.
 * Sync strategy:
 * - Tasks: server wins on conflict (409 -> accept server version)
 * - Photos: append-only (no conflicts)
 * - Retry: max 5 attempts with exponential backoff
 */

const DB_NAME = 'stroyuprav-offline';
const DB_VERSION = 1;

const STORE_SYNC_QUEUE = 'sync_queue';
const STORE_TASKS_CACHE = 'tasks_cache';
const STORE_PHOTOS_QUEUE = 'photos_queue';

const MAX_RETRIES = 5;
const MAX_PHOTOS_QUEUED = 100;
const PHOTOS_WARN_THRESHOLD = 80;

class OfflineSyncManager {
    constructor() {
        this.db = null;
        this._syncInProgress = false;
    }

    // ─── Initialize IndexedDB ────────────────────────────
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Sync queue for task mutations
                if (!db.objectStoreNames.contains(STORE_SYNC_QUEUE)) {
                    const syncStore = db.createObjectStore(STORE_SYNC_QUEUE, {
                        keyPath: 'id',
                        autoIncrement: true,
                    });
                    syncStore.createIndex('by_created', 'created_at', { unique: false });
                    syncStore.createIndex('by_type', 'type', { unique: false });
                    syncStore.createIndex('by_status', 'status', { unique: false });
                }

                // Local tasks cache
                if (!db.objectStoreNames.contains(STORE_TASKS_CACHE)) {
                    const tasksStore = db.createObjectStore(STORE_TASKS_CACHE, {
                        keyPath: 'id',
                    });
                    tasksStore.createIndex('by_project', 'project_id', { unique: false });
                }

                // Photo upload queue
                if (!db.objectStoreNames.contains(STORE_PHOTOS_QUEUE)) {
                    const photosStore = db.createObjectStore(STORE_PHOTOS_QUEUE, {
                        keyPath: 'id',
                        autoIncrement: true,
                    });
                    photosStore.createIndex('by_task', 'task_id', { unique: false });
                    photosStore.createIndex('by_status', 'status', { unique: false });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };

            request.onerror = (event) => {
                console.error('[OfflineSync] IndexedDB open failed:', event.target.error);
                reject(event.target.error);
            };
        });
    }

    // ─── Queue an offline write ──────────────────────────
    async queueWrite(type, endpoint, method, payload) {
        const entry = {
            type,
            endpoint,
            method,
            payload,
            created_at: Date.now(),
            retry_count: 0,
            status: 'pending',
            local_id: this._generateUUID(),
        };

        await this._put(STORE_SYNC_QUEUE, entry);

        this._showToast('Сохранено офлайн. Будет отправлено при подключении.');

        return entry.local_id;
    }

    // ─── Queue a photo for upload ────────────────────────
    async queuePhoto(taskId, projectId, photoBlob, metadata) {
        const count = await this._count(STORE_PHOTOS_QUEUE);

        if (count >= MAX_PHOTOS_QUEUED) {
            this._showToast(
                'Очередь фото заполнена. Подключитесь к сети для загрузки.',
                'error'
            );
            return null;
        }

        if (count >= PHOTOS_WARN_THRESHOLD) {
            this._showToast(
                `В очереди ${count} фото. Рекомендуем подключиться к сети.`,
                'warning'
            );
        }

        const entry = {
            task_id: taskId,
            project_id: projectId,
            blob: photoBlob,
            latitude: metadata.latitude || null,
            longitude: metadata.longitude || null,
            captured_at: metadata.captured_at || new Date().toISOString(),
            comment: metadata.comment || '',
            created_at: Date.now(),
            retry_count: 0,
            status: 'pending',
        };

        await this._put(STORE_PHOTOS_QUEUE, entry);
        return entry;
    }

    // ─── Sync all pending entries ────────────────────────
    async syncAll() {
        if (!navigator.onLine) {
            return { synced: 0, failed: 0, reason: 'offline' };
        }

        if (this._syncInProgress) {
            return { synced: 0, failed: 0, reason: 'sync_in_progress' };
        }

        this._syncInProgress = true;
        let synced = 0;
        let failed = 0;

        try {
            // 1. Sync task writes (ordered by creation time)
            const taskResult = await this._syncTaskQueue();
            synced += taskResult.synced;
            failed += taskResult.failed;

            // 2. Sync photos (append-only)
            const photoResult = await this._syncPhotoQueue();
            synced += photoResult.synced;
            failed += photoResult.failed;

            if (synced > 0) {
                this._showToast(`Данные синхронизированы (${synced} элементов)`);
            }
        } finally {
            this._syncInProgress = false;
        }

        return { synced, failed };
    }

    // ─── Sync task queue ─────────────────────────────────
    async _syncTaskQueue() {
        const entries = await this._getAllByIndex(
            STORE_SYNC_QUEUE, 'by_status', 'pending'
        );

        // Sort by created_at to preserve order
        entries.sort((a, b) => a.created_at - b.created_at);

        let synced = 0;
        let failed = 0;

        for (const entry of entries) {
            try {
                const response = await fetch(entry.endpoint, {
                    method: entry.method,
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(entry.payload),
                });

                if (response.ok) {
                    const serverData = await response.json();
                    // Update local cache with server response
                    if (serverData.id) {
                        await this._put(STORE_TASKS_CACHE, serverData);
                    }
                    await this._delete(STORE_SYNC_QUEUE, entry.id);
                    synced++;
                } else if (response.status === 409) {
                    // Conflict: server wins
                    try {
                        const serverData = await response.json();
                        if (serverData.id) {
                            await this._put(STORE_TASKS_CACHE, serverData);
                        }
                    } catch {
                        // Server did not return conflicting data
                    }
                    await this._delete(STORE_SYNC_QUEUE, entry.id);
                    synced++;
                    console.warn(
                        `[OfflineSync] Conflict resolved (server wins): ${entry.type} ${entry.local_id}`
                    );
                } else if (response.status === 404) {
                    // Resource deleted on server
                    await this._delete(STORE_SYNC_QUEUE, entry.id);
                    this._showToast('Задача была удалена другим пользователем.', 'warning');
                    synced++;
                } else if (response.status === 401) {
                    // Auth expired — stop sync, redirect to login
                    console.warn('[OfflineSync] Auth expired during sync');
                    break;
                } else if (response.status >= 500) {
                    // Server error — retry with backoff
                    entry.retry_count++;
                    if (entry.retry_count >= MAX_RETRIES) {
                        entry.status = 'failed';
                        failed++;
                    }
                    await this._put(STORE_SYNC_QUEUE, entry);
                }
            } catch {
                // Network error — stop sync
                console.warn('[OfflineSync] Network lost during task sync');
                break;
            }
        }

        return { synced, failed };
    }

    // ─── Sync photo queue ────────────────────────────────
    async _syncPhotoQueue() {
        const photos = await this._getAllByIndex(
            STORE_PHOTOS_QUEUE, 'by_status', 'pending'
        );

        let synced = 0;
        let failed = 0;

        for (const photo of photos) {
            try {
                const formData = new FormData();
                formData.append('file', photo.blob, 'photo.jpg');
                formData.append('task_id', photo.task_id);
                if (photo.latitude != null) {
                    formData.append('latitude', String(photo.latitude));
                }
                if (photo.longitude != null) {
                    formData.append('longitude', String(photo.longitude));
                }
                formData.append('captured_at', photo.captured_at);
                if (photo.comment) {
                    formData.append('comment', photo.comment);
                }

                const response = await fetch(
                    `/api/v1/projects/${photo.project_id}/photos`,
                    {
                        method: 'POST',
                        credentials: 'include',
                        body: formData,
                    }
                );

                if (response.ok) {
                    await this._delete(STORE_PHOTOS_QUEUE, photo.id);
                    synced++;
                } else if (response.status === 401) {
                    // Auth expired — stop
                    break;
                } else {
                    photo.retry_count = (photo.retry_count || 0) + 1;
                    if (photo.retry_count >= MAX_RETRIES) {
                        photo.status = 'failed';
                        failed++;
                    }
                    await this._put(STORE_PHOTOS_QUEUE, photo);
                }
            } catch {
                // Network error — stop
                console.warn('[OfflineSync] Network lost during photo sync');
                break;
            }
        }

        return { synced, failed };
    }

    // ─── Cache tasks locally ─────────────────────────────
    async cacheTasks(projectId, tasks) {
        const tx = this.db.transaction(STORE_TASKS_CACHE, 'readwrite');
        const store = tx.objectStore(STORE_TASKS_CACHE);
        for (const task of tasks) {
            store.put(task);
        }
        return new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve(tasks.length);
            tx.onerror = () => reject(tx.error);
        });
    }

    // ─── Get cached tasks ────────────────────────────────
    async getCachedTasks(projectId) {
        return this._getAllByIndex(STORE_TASKS_CACHE, 'by_project', projectId);
    }

    // ─── Get pending counts ──────────────────────────────
    async getPendingCount() {
        const tasksPending = await this._countByIndex(
            STORE_SYNC_QUEUE, 'by_status', 'pending'
        );
        const photosPending = await this._countByIndex(
            STORE_PHOTOS_QUEUE, 'by_status', 'pending'
        );
        return { tasks: tasksPending, photos: photosPending };
    }

    // ─── Clear all data (on logout) ─────────────────────
    async clearAllData() {
        if (this.db) {
            const storeNames = [STORE_SYNC_QUEUE, STORE_TASKS_CACHE, STORE_PHOTOS_QUEUE];
            const tx = this.db.transaction(storeNames, 'readwrite');
            for (const name of storeNames) {
                tx.objectStore(name).clear();
            }
            await new Promise((resolve) => { tx.oncomplete = resolve; });
        }

        // Purge API cache
        try {
            await caches.delete('su-api-v1');
        } catch {
            // Cache API not available
        }

        console.log('[OfflineSync] All offline data cleared on logout');
    }

    // ─── IndexedDB helpers ───────────────────────────────

    _put(storeName, value) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            const store = tx.objectStore(storeName);
            const request = store.put(value);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    _delete(storeName, key) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            const store = tx.objectStore(storeName);
            const request = store.delete(key);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    _getAllByIndex(storeName, indexName, value) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const store = tx.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.getAll(value);
            request.onsuccess = () => resolve(request.result || []);
            request.onerror = () => reject(request.error);
        });
    }

    _count(storeName) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const store = tx.objectStore(storeName);
            const request = store.count();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    _countByIndex(storeName, indexName, value) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const store = tx.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.count(value);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    _generateUUID() {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        // Fallback for older browsers
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
            const r = (Math.random() * 16) | 0;
            const v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    _showToast(message, level = 'info') {
        // Integration point with Odoo OWL notification system
        if (typeof window !== 'undefined' && window.__owl_notifications) {
            window.__owl_notifications.add(message, { type: level });
        } else {
            console.log(`[OfflineSync] [${level}] ${message}`);
        }
    }
}

// ─── Connectivity handler ────────────────────────────────
function initConnectivityHandler(syncManager) {
    window.addEventListener('online', async () => {
        const banner = document.getElementById('su-offline-banner');
        if (banner) {
            banner.textContent = 'Подключение восстановлено. Синхронизация...';
            banner.className = 'su-connectivity-banner su-syncing';
        }

        await syncManager.syncAll();

        if (banner) {
            setTimeout(() => {
                banner.style.display = 'none';
                banner.className = 'su-connectivity-banner';
            }, 3000);
        }
    });

    window.addEventListener('offline', () => {
        const banner = document.getElementById('su-offline-banner');
        if (banner) {
            banner.textContent = 'Нет подключения. Изменения сохраняются локально.';
            banner.className = 'su-connectivity-banner su-offline';
            banner.style.display = 'block';
        }
    });

    // Periodic sync when online (every 60 seconds)
    setInterval(async () => {
        if (navigator.onLine) {
            const pending = await syncManager.getPendingCount();
            if (pending.tasks > 0 || pending.photos > 0) {
                await syncManager.syncAll();
            }
        }
    }, 60000);
}

// ─── Export for module use ───────────────────────────────
if (typeof window !== 'undefined') {
    window.OfflineSyncManager = OfflineSyncManager;
    window.initConnectivityHandler = initConnectivityHandler;
}
