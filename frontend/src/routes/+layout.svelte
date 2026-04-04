<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { connectSSE } from '$lib/stores/sse';
	import { page } from '$app/stores';

	onMount(() => {
		connectSSE();
	});

	const navItems = [
		{ href: '/', label: 'Inbox', icon: '📥' },
		{ href: '/active', label: 'Active', icon: '⚡' },
		{ href: '/chat', label: 'Chat', icon: '💬' },
		{ href: '/search', label: 'Search', icon: '🔍' },
		{ href: '/settings', label: 'Brain', icon: '🧠' },
	];
</script>

<div class="flex flex-col h-screen">
	<!-- Main content area -->
	<main class="flex-1 overflow-y-auto pb-20">
		<slot />
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
