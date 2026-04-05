/// <reference lib="webworker" />

const CACHE_NAME = 'daystrom-v1';
const OFFLINE_QUEUE_STORE = 'offline-queue';
const DB_NAME = 'daystrom-offline';
const DB_VERSION = 1;

// Static assets to cache on install
const PRECACHE_URLS = [
	'/',
	'/manifest.json',
	'/icons/icon-192.png',
	'/icons/icon-512.png',
];

// Auth token, passed from the main thread
let authToken = null;

// Install: precache shell assets
self.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
	);
	self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches.keys().then((keys) =>
			Promise.all(
				keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
			)
		)
	);
	self.clients.claim();
});

// Fetch: network-only for API, cache-first for static assets
self.addEventListener('fetch', (event) => {
	const url = new URL(event.request.url);

	// Skip non-GET requests except for offline capture queue
	if (event.request.method !== 'GET') {
		// Intercept POST to /api/items/capture when offline
		if (
			event.request.method === 'POST' &&
			url.pathname === '/api/items/capture'
		) {
			event.respondWith(handleOfflineCapture(event.request));
			return;
		}
		return;
	}

	// Don't intercept API requests — avoid caching sensitive/user-specific data.
	// Let them go straight to the network. Offline API calls will just fail
	// gracefully in the UI.
	if (url.pathname.startsWith('/api/')) return;

	// Static assets: cache-first
	event.respondWith(cacheFirst(event.request));
});

async function cacheFirst(request) {
	const cached = await caches.match(request);
	if (cached) return cached;

	try {
		const response = await fetch(request);
		if (response.ok) {
			const cache = await caches.open(CACHE_NAME);
			cache.put(request, response.clone());
		}
		return response;
	} catch {
		// Return offline fallback page if available
		const cached = await caches.match('/');
		if (cached) return cached;
		return new Response('Offline', { status: 503 });
	}
}

// IndexedDB for offline capture queue
function openDB() {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);
		request.onupgradeneeded = () => {
			const db = request.result;
			if (!db.objectStoreNames.contains(OFFLINE_QUEUE_STORE)) {
				db.createObjectStore(OFFLINE_QUEUE_STORE, {
					keyPath: 'id',
					autoIncrement: true,
				});
			}
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

async function addToQueue(data) {
	const db = await openDB();
	return new Promise((resolve, reject) => {
		const tx = db.transaction(OFFLINE_QUEUE_STORE, 'readwrite');
		const store = tx.objectStore(OFFLINE_QUEUE_STORE);
		store.add({ ...data, queued_at: new Date().toISOString() });
		tx.oncomplete = () => resolve();
		tx.onerror = () => reject(tx.error);
	});
}

async function getQueuedItems() {
	const db = await openDB();
	return new Promise((resolve, reject) => {
		const tx = db.transaction(OFFLINE_QUEUE_STORE, 'readonly');
		const store = tx.objectStore(OFFLINE_QUEUE_STORE);
		const request = store.getAll();
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

async function clearQueue() {
	const db = await openDB();
	return new Promise((resolve, reject) => {
		const tx = db.transaction(OFFLINE_QUEUE_STORE, 'readwrite');
		const store = tx.objectStore(OFFLINE_QUEUE_STORE);
		store.clear();
		tx.oncomplete = () => resolve();
		tx.onerror = () => reject(tx.error);
	});
}

async function handleOfflineCapture(request) {
	try {
		// Try network first
		const response = await fetch(request.clone());
		return response;
	} catch {
		// Offline — queue the capture
		try {
			const body = await request.json();
			await addToQueue(body);

			// Return a synthetic success response
			return new Response(
				JSON.stringify({
					id: `offline-${Date.now()}`,
					content: body.content,
					status: 'inbox',
					enrichment_status: 'pending',
					tags: [],
					created_at: new Date().toISOString(),
					updated_at: new Date().toISOString(),
					_offline: true,
				}),
				{
					status: 201,
					headers: { 'Content-Type': 'application/json' },
				}
			);
		} catch (e) {
			return new Response(JSON.stringify({ error: 'Failed to queue offline' }), {
				status: 500,
				headers: { 'Content-Type': 'application/json' },
			});
		}
	}
}

// Handle messages from the main thread
self.addEventListener('message', async (event) => {
	if (event.data && event.data.type === 'SYNC_OFFLINE') {
		// Accept token from main thread for authenticated sync
		if (event.data.token) {
			authToken = event.data.token;
		}
		await syncOfflineQueue();
	} else if (event.data && event.data.type === 'SET_TOKEN') {
		authToken = event.data.token || null;
	}
});

async function syncOfflineQueue() {
	const items = await getQueuedItems();
	if (items.length === 0) return;

	// Build auth headers
	const headers = { 'Content-Type': 'application/json' };
	if (authToken) {
		headers['Authorization'] = `Bearer ${authToken}`;
	}

	let synced = 0;
	for (const item of items) {
		try {
			const { id, queued_at, ...body } = item;
			const response = await fetch('/api/items/capture', {
				method: 'POST',
				headers,
				body: JSON.stringify(body),
			});
			if (response.ok) synced++;
		} catch {
			break; // Still offline, stop trying
		}
	}

	if (synced === items.length) {
		await clearQueue();
	}

	// Notify clients
	const clients = await self.clients.matchAll();
	for (const client of clients) {
		client.postMessage({
			type: 'OFFLINE_SYNC_COMPLETE',
			synced,
			total: items.length,
		});
	}
}
