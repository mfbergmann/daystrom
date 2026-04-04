<script lang="ts">
	import { onMount } from 'svelte';
	import { items, loading, captureItem, loadItems, completeItem, deleteItem, updateItemInStore } from '$lib/stores/items';
	import { api } from '$lib/api/client';

	let inputValue = $state('');
	let inputEl: HTMLInputElement;

	onMount(() => {
		loadItems({ status: 'inbox' });
		inputEl?.focus();
	});

	async function handleCapture() {
		const content = inputValue.trim();
		if (!content) return;
		inputValue = '';
		await captureItem(content);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleCapture();
		}
	}

	function typeIcon(type: string | null): string {
		switch (type) {
			case 'task': return '☑️';
			case 'idea': return '💡';
			case 'note': return '📝';
			case 'event': return '📅';
			case 'reference': return '🔗';
			default: return '○';
		}
	}

	function priorityColor(priority: string | null): string {
		switch (priority) {
			case 'urgent': return 'border-l-red-500';
			case 'high': return 'border-l-orange-500';
			case 'medium': return 'border-l-yellow-500';
			case 'low': return 'border-l-blue-500';
			default: return 'border-l-transparent';
		}
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		const diffHours = Math.floor(diffMins / 60);
		if (diffHours < 24) return `${diffHours}h ago`;
		return date.toLocaleDateString();
	}
</script>

<svelte:head>
	<title>Daystrom — Inbox</title>
</svelte:head>

<div class="max-w-lg mx-auto px-4 pt-[var(--sat)]">
	<!-- Header -->
	<header class="pt-6 pb-4">
		<h1 class="text-2xl font-bold text-slate-100">Daystrom</h1>
		<p class="text-sm text-slate-500">What's on your mind?</p>
	</header>

	<!-- Quick capture input -->
	<div class="sticky top-0 z-10 bg-slate-950/95 backdrop-blur-sm pb-3">
		<div class="flex gap-2">
			<input
				bind:this={inputEl}
				bind:value={inputValue}
				onkeydown={handleKeydown}
				type="text"
				placeholder="Add a task, idea, or note..."
				class="flex-1 bg-slate-800 text-slate-100 rounded-xl px-4 py-3 text-base
					placeholder-slate-500 border border-slate-700 focus:border-blue-500
					focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
			/>
			<button
				onclick={handleCapture}
				disabled={!inputValue.trim()}
				class="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500
					text-white rounded-xl px-4 py-3 font-medium transition-colors"
			>
				Add
			</button>
		</div>
	</div>

	<!-- Items list -->
	{#if $loading && $items.length === 0}
		<div class="flex justify-center py-12">
			<div class="text-slate-500">Loading...</div>
		</div>
	{:else if $items.length === 0}
		<div class="text-center py-16">
			<p class="text-slate-500 text-lg">Your inbox is empty</p>
			<p class="text-slate-600 text-sm mt-2">Start typing above to capture thoughts</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each $items as item (item.id)}
				<div class="slide-in bg-slate-900 rounded-xl border-l-4 {priorityColor(item.priority)}
					border border-slate-800 overflow-hidden">
					<div class="flex items-start gap-3 p-3">
						<!-- Complete button -->
						<button
							onclick={() => completeItem(item.id)}
							class="mt-0.5 text-slate-600 hover:text-green-400 transition-colors text-lg flex-shrink-0"
							title="Complete"
						>
							{typeIcon(item.item_type)}
						</button>

						<!-- Content -->
						<div class="flex-1 min-w-0">
							<p class="text-slate-200 text-sm leading-relaxed">
								{item.parsed_title || item.content}
							</p>

							<!-- Tags -->
							<div class="flex flex-wrap gap-1.5 mt-2">
								{#if item.enrichment_status === 'pending'}
									<span class="shimmer inline-block bg-slate-700 rounded-full px-2.5 py-0.5 text-xs text-slate-400">
										classifying...
									</span>
								{:else}
									{#each item.tags as tag}
										<button
											onclick={async () => {
												await api.removeTagFromItem(item.id, tag.name);
												const refreshed = await api.getItem(item.id);
												updateItemInStore(refreshed);
											}}
											class="inline-flex items-center gap-0.5 bg-slate-800 rounded-full px-2.5 py-0.5 text-xs text-slate-400
												hover:bg-red-900/30 hover:text-red-400 transition-colors cursor-pointer
												{tag.source === 'user' ? 'border border-blue-800' : ''}"
											title="Click to remove tag"
										>
											{tag.name}
											<span class="opacity-0 group-hover:opacity-100 ml-0.5">x</span>
										</button>
									{/each}
								{/if}

								{#if item.due_date}
									<span class="inline-block bg-slate-800 rounded-full px-2.5 py-0.5 text-xs text-amber-400">
										📅 {new Date(item.due_date).toLocaleDateString()}
									</span>
								{/if}
							</div>
						</div>

						<!-- Time -->
						<span class="text-xs text-slate-600 flex-shrink-0 mt-1">
							{formatDate(item.created_at)}
						</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
