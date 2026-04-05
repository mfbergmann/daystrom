<script lang="ts">
	import { onMount } from 'svelte';
	import { items, loading, loadItems, completeItem } from '$lib/stores/items';

	let groupBy = $state<'type' | 'priority' | 'none'>('type');

	onMount(() => {
		loadItems({ status: 'active' });
	});

	function grouped(): Record<string, typeof $items> {
		if (groupBy === 'none') return { 'All': $items };

		const groups: Record<string, typeof $items> = {};
		for (const item of $items) {
			const key = groupBy === 'type'
				? (item.item_type || 'uncategorized')
				: (item.priority || 'none');
			if (!groups[key]) groups[key] = [];
			groups[key].push(item);
		}
		return groups;
	}

	function typeLabel(type: string): string {
		const labels: Record<string, string> = {
			task: '☑️ Tasks', idea: '💡 Ideas', note: '📝 Notes',
			event: '📅 Events', reference: '🔗 References', uncategorized: '○ Uncategorized'
		};
		return labels[type] || type;
	}

	function priorityLabel(p: string): string {
		const labels: Record<string, string> = {
			urgent: '🔴 Urgent', high: '🟠 High', medium: '🟡 Medium',
			low: '🔵 Low', none: '⚪ None'
		};
		return labels[p] || p;
	}
</script>

<svelte:head>
	<title>Daystrom — Active</title>
</svelte:head>

<div class="max-w-lg mx-auto px-4 pt-[var(--sat)]">
	<header class="pt-6 pb-4 flex items-center justify-between">
		<h1 class="text-2xl font-bold text-slate-100">Active</h1>
		<select
			bind:value={groupBy}
			class="bg-slate-800 text-slate-300 text-sm rounded-lg px-3 py-1.5 border border-slate-700"
		>
			<option value="type">By Type</option>
			<option value="priority">By Priority</option>
			<option value="none">No Grouping</option>
		</select>
	</header>

	{#if $loading && $items.length === 0}
		<div class="flex justify-center py-12">
			<div class="text-slate-500">Loading...</div>
		</div>
	{:else}
		{#each Object.entries(grouped()) as [group, groupItems]}
			<div class="mb-6">
				{#if groupBy !== 'none'}
					<h2 class="text-sm font-semibold text-slate-400 mb-2 px-1">
						{groupBy === 'type' ? typeLabel(group) : priorityLabel(group)}
						<span class="text-slate-600 ml-1">({groupItems.length})</span>
					</h2>
				{/if}

				<div class="space-y-1.5">
					{#each groupItems as item (item.id)}
						<div class="flex items-center gap-3 bg-slate-900 rounded-lg px-3 py-2.5 border border-slate-800">
							<button
								onclick={() => completeItem(item.id)}
								aria-label="Complete item"
								class="w-5 h-5 rounded-full border-2 border-slate-600 hover:border-green-400
									hover:bg-green-400/20 transition-colors flex-shrink-0"
							></button>
							<div class="flex-1 min-w-0">
								<p class="text-sm text-slate-200 truncate">
									{item.parsed_title || item.content}
								</p>
								{#if item.tags.length > 0}
									<div class="flex gap-1 mt-1">
										{#each item.tags.slice(0, 3) as tag}
											<span class="text-xs text-slate-500">{tag.name}</span>
										{/each}
									</div>
								{/if}
							</div>
							{#if item.due_date}
								<span class="text-xs text-amber-400 flex-shrink-0">
									{new Date(item.due_date).toLocaleDateString()}
								</span>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/each}

		{#if $items.length === 0}
			<div class="text-center py-16">
				<p class="text-slate-500">No active items</p>
			</div>
		{/if}
	{/if}
</div>
