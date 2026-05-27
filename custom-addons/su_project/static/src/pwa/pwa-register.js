/**
 * СтройУправ PWA Registration
 *
 * Registers Service Worker and sets up push notifications.
 * Must be loaded after page load to avoid blocking rendering.
 */

(function () {
    'use strict';

    // ─── Service Worker Registration ─────────────────────
    async function registerServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            console.warn('[PWA] Service Worker not supported');
            return null;
        }

        try {
            const registration = await navigator.serviceWorker.register('/sw.js', {
                scope: '/',
            });

            console.log('[PWA] Service Worker registered, scope:', registration.scope);

            // Check for updates periodically
            setInterval(() => {
                registration.update();
            }, 60 * 60 * 1000); // Every hour

            return registration;
        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
            return null;
        }
    }

    // ─── Push Notification Setup ─────────────────────────
    async function setupPushNotifications() {
        if (!('PushManager' in window)) {
            console.warn('[PWA] Push notifications not supported');
            return false;
        }

        if (!('serviceWorker' in navigator)) {
            return false;
        }

        const registration = await navigator.serviceWorker.ready;

        // Check existing subscription
        const existingSub = await registration.pushManager.getSubscription();
        if (existingSub) {
            console.log('[PWA] Push subscription exists');
            return true;
        }

        // Request permission
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('[PWA] Push permission denied');
            return false;
        }

        // Get VAPID public key from server
        try {
            const response = await fetch('/api/v1/push/vapid-key', {
                credentials: 'include',
            });

            if (!response.ok) {
                console.warn('[PWA] Failed to get VAPID key');
                return false;
            }

            const { public_key: vapidPublicKey } = await response.json();

            // Subscribe to push
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
            });

            // Send subscription to server
            await fetch('/api/v1/push/subscribe', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    endpoint: subscription.endpoint,
                    keys: {
                        p256dh: arrayBufferToBase64(subscription.getKey('p256dh')),
                        auth: arrayBufferToBase64(subscription.getKey('auth')),
                    },
                }),
            });

            console.log('[PWA] Push subscription created');
            return true;
        } catch (error) {
            console.error('[PWA] Push setup failed:', error);
            return false;
        }
    }

    // ─── Install Prompt Handling ─────────────────────────
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (event) => {
        event.preventDefault();
        deferredPrompt = event;

        // Show install banner after 2nd visit
        const visitCount = parseInt(localStorage.getItem('su-visit-count') || '0', 10) + 1;
        localStorage.setItem('su-visit-count', String(visitCount));

        if (visitCount >= 2) {
            showInstallBanner();
        }
    });

    function showInstallBanner() {
        const banner = document.createElement('div');
        banner.id = 'su-install-banner';
        banner.className = 'su-install-banner';
        banner.innerHTML = `
            <span>Установите СтройУправ для быстрого доступа</span>
            <button id="su-install-btn" class="su-install-btn">Установить</button>
            <button id="su-install-dismiss" class="su-install-dismiss">&times;</button>
        `;

        document.body.appendChild(banner);

        document.getElementById('su-install-btn').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const result = await deferredPrompt.userChoice;
                console.log('[PWA] Install prompt result:', result.outcome);
                deferredPrompt = null;
            }
            banner.remove();
        });

        document.getElementById('su-install-dismiss').addEventListener('click', () => {
            banner.remove();
        });
    }

    // ─── Initialize Offline Sync ─────────────────────────
    async function initOfflineSync() {
        if (typeof OfflineSyncManager === 'undefined') {
            console.warn('[PWA] OfflineSyncManager not loaded');
            return;
        }

        const syncManager = new OfflineSyncManager();
        await syncManager.init();

        // Make globally available for OWL components
        window.suSyncManager = syncManager;

        // Set up connectivity handlers
        if (typeof initConnectivityHandler === 'function') {
            initConnectivityHandler(syncManager);
        }

        // Initial sync if online
        if (navigator.onLine) {
            const pending = await syncManager.getPendingCount();
            if (pending.tasks > 0 || pending.photos > 0) {
                syncManager.syncAll();
            }
        }
    }

    // ─── Helpers ─────────────────────────────────────────
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        const rawData = atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; i++) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    // ─── Boot on page load ───────────────────────────────
    window.addEventListener('load', async () => {
        await registerServiceWorker();
        await initOfflineSync();
        // Delay push setup to avoid overwhelming user on first visit
        setTimeout(() => setupPushNotifications(), 5000);
    });
})();
