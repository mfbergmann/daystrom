<script lang="ts">
	import { api } from '$lib/api/client';

	let query = $state('');
	let results = $state<any[]>([]);
	let searching = $state(false);
	let searched = $state(false);

	async function handleSearch() {
		const q = query.trim();
		if (!q) return;
		searching = true;
		searched = true;
		try {
			results = await api.search(q);
		} catch (e) {
			console.error('Search failed:', e);
			results = [];
		} finally {
			searching = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleSearch();
		}
	}
</script>

<svelte:head>
	<title>Daystrom — Search</title>
</svelte:head>

<div class="max-w-lg mx-auto px-4 pt-[var(--sat)]">
	<header class="pt-6 pb-4">
		<h1 class="text-2xl font-bold text-slate-100">Search</h1>
		<p class="text-sm text-slate-500">Semantic search across all your items</p>
	</header>

	<div class="flex gap-2 mb-4">
		<input
			bind:value={query}
			onkeydown={handleKeydown}
			type="text"
			placeholder="Search by meaning, not just keywords..."
			class="flex-1 bg-slate-800 text-slate-100 rounded-xl px-4 py-3 text-base
				placeholder-slate-500 border border-slate-700 focus:border-blue-500
				focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
		/>
		<button
			onclick={handleSearch}
			disabled={!query.trim() || searching}
			class="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700
				text-white rounded-xl px-4 py-3 font-medium transition-colors"
		>
			{searching ? '...' : '🔍'}
		</button>
	</div>

	{#if searching}
		<div class="flex justify-center py-8">
			<div class="text-slate-500">Searching...</div>
		</div>
	{:else if results.length > 0}
		<div class="space-y-2">
			{#each results as result}
				<div class="bg-slate-900 rounded-xl p-3 border border-slate-800">
					<div class="flex items-start justify-between gap-2">
						<p class="text-sm text-slate-200">{result.parsed_title || result.content}</p>
						<span class="text-xs text-blue-400 flex-shrink-0">
							{Math.round(result.score * 100)}%
						</span>
					</div>
					{#if result.item_type}
						<span class="inline-block mt-1.5 text-xs text-slate-500 bg-slate-800 rounded px-2 py-0.5">
							{result.item_type}
						</span>
					{/if}
				</div>
			{/each}
		</div>
	{:else if searched}
		<div class="text-center py-8">
			<p class="text-slate-500">No results found</p>
		</div>
	{/if}
</div>
