<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { connectSSE } from '$lib/stores/sse';
	import { page } from '$app/stores';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	let isOffline = $state(false);
	let offlineSyncMessage = $state('');
	let loggedIn = $state(false);
	let pinInput = $state('');
	let loginError = $state('');
	let authRequired = $state(true);

	async function checkAuth() {
		const token = localStorage.getItem('daystrom_token');
		if (token) { loggedIn = true; return; }
		try {
			const r = await fetch('/api/auth/status');
			const data = await r.json();
			authRequired = data.auth_required;
			if (!authRequired) await doLogin('');
		} catch { loggedIn = true; } // if backend unreachable, let it through to show errors naturally
	}

	async function doLogin(pin: string) {
		try {
			const r = await fetch('/api/auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ pin })
			});
			if (!r.ok) { loginError = 'Incorrect PIN'; return; }
			const data = await r.json();
			localStorage.setItem('daystrom_token', data.access_token);
			loggedIn = true;
			connectSSE();
		} catch { loginError = 'Could not reach backend'; }
	}

	onMount(() => {
		checkAuth();
		connectSSE();

		// Register service worker
		if ('serviceWorker' in navigator) {
			navigator.serviceWorker.register('/service-worker.js').catch((err) => {
				console.warn('SW registration failed:', err);
			});

			// Listen for offline sync messages
			navigator.serviceWorker.addEventListener('message', (event) => {
				if (event.data?.type === 'OFFLINE_SYNC_COMPLETE') {
					const { synced, total } = event.data;
					offlineSyncMessage = `Synced ${synced}/${total} offline items`;
					setTimeout(() => { offlineSyncMessage = ''; }, 3000);
				}
			});
		}

		// Online/offline detection
		const updateOnlineStatus = () => {
			isOffline = !navigator.onLine;
			if (navigator.onLine && navigator.serviceWorker?.controller) {
				const token = localStorage.getItem('daystrom_token');
				navigator.serviceWorker.controller.postMessage({ type: 'SYNC_OFFLINE', token });
			}
		};
		window.addEventListener('online', updateOnlineStatus);
		window.addEventListener('offline', updateOnlineStatus);
		isOffline = !navigator.onLine;

		return () => {
			window.removeEventListener('online', updateOnlineStatus);
			window.removeEventListener('offline', updateOnlineStatus);
		};
	});

	const navItems = [
		{ href: '/', label: 'Inbox', icon: '\uD83D\uDCE5' },
		{ href: '/active', label: 'Active', icon: '\u26A1' },
		{ href: '/chat', label: 'Chat', icon: '\uD83D\uDCAC' },
		{ href: '/agents', label: 'Agents', icon: '\uD83E\uDD16' },
		{ href: '/search', label: 'Search', icon: '\uD83D\uDD0D' },
	];
</script>

{#if !loggedIn && authRequired}
<div class="flex flex-col items-center justify-center h-screen bg-slate-950 px-6">
	<p class="text-4xl mb-6">🔒</p>
	<h1 class="text-white text-xl font-semibold mb-1">Daystrom</h1>
	<p class="text-slate-500 text-sm mb-8">Enter your PIN to continue</p>
	<form onsubmit={(e) => { e.preventDefault(); doLogin(pinInput); }} class="w-full max-w-xs flex flex-col gap-3">
		<input
			type="password"
			inputmode="numeric"
			placeholder="PIN"
			bind:value={pinInput}
			autofocus
			class="w-full rounded-xl bg-slate-800 text-white px-4 py-3 text-center text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-sky-500"
		/>
		{#if loginError}<p class="text-red-400 text-sm text-center">{loginError}</p>{/if}
		<button type="submit" class="w-full rounded-xl bg-sky-600 hover:bg-sky-500 text-white py-3 font-medium transition-colors">
			Unlock
		</button>
	</form>
</div>
{:else}
<div class="flex flex-col h-screen">
	<!-- Offline banner -->
	{#if isOffline}
		<div class="bg-amber-600/90 text-white text-xs text-center py-1.5 px-4 flex-shrink-0">
			Offline — items will sync when you reconnect
		</div>
	{/if}

	{#if offlineSyncMessage}
		<div class="bg-green-600/90 text-white text-xs text-center py-1.5 px-4 flex-shrink-0 slide-in">
			{offlineSyncMessage}
		</div>
	{/if}

	<!-- Main content area -->
	<main class="flex-1 overflow-y-auto pb-20">
		{@render children()}
	</main>

	<!-- Bottom navigation bar (iOS-style tab bar) -->
	<nav class="fixed bottom-0 left-0 right-0 bg-slate-900/95 backdrop-blur-lg border-t border-slate-800 pb-[var(--sab)]">
		<div class="flex justify-around items-center h-14 max-w-lg mx-auto">
			{#each navItems as item}
				<a
					href={item.href}
					class="flex flex-col items-center gap-0.5 px-4 py-1 text-xs transition-colors
						{$page.url.pathname === item.href ? 'text-blue-400' : 'text-slate-500 hover:text-slate-300'}"
				>
					<span class="text-lg">{item.icon}</span>
					<span>{item.label}</span>
				</a>
			{/each}
		</div>
	</nav>
</div>
{/if}
