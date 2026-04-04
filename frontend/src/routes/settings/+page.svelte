<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type Memory, type MemoryStats } from '$lib/api/client';

	let activeTab = $state<'memories' | 'model' | 'health'>('memories');

	// Memories
	let memories = $state<Memory[]>([]);
	let memoryStats = $state<MemoryStats | null>(null);
	let memoryFilter = $state<string>('');
	let loadingMemories = $state(false);

	// Behavioral model
	let model = $state<any>(null);
	let loadingModel = $state(false);

	// Health
	let health = $state<any>(null);

	onMount(() => {
		loadMemories();
		loadStats();
	});

	async function loadMemories() {
		loadingMemories = true;
		try {
			const params: any = { limit: 100 };
			if (memoryFilter) params.memory_type = memoryFilter;
			memories = await api.listMemories(params);
		} catch (e) { console.error(e); }
		loadingMemories = false;
	}

	async function loadStats() {
		try { memoryStats = await api.memoryStats(); } catch (e) { console.error(e); }
	}

	async function loadModel() {
		loadingModel = true;
		try { model = await api.behavioralModel(); } catch (e) { console.error(e); }
		loadingModel = false;
	}

	async function loadHealth() {
		try { health = await api.health(); } catch (e) { console.error(e); }
	}

	async function deleteMemory(id: string) {
		await api.deleteMemory(id);
		memories = memories.filter(m => m.id !== id);
		await loadStats();
	}

	function switchTab(tab: typeof activeTab) {
		activeTab = tab;
		if (tab === 'model' && !model) loadModel();
		if (tab === 'health' && !health) loadHealth();
	}

	function typeIcon(type: string): string {
		const icons: Record<string, string> = {
			fact: '📌', preference: '⚙️', pattern: '📊',
			association: '🔗', context: '🧠'
		};
		return icons[type] || '💭';
	}

	function confidenceColor(c: number): string {
		if (c >= 0.8) return 'text-green-400';
		if (c >= 0.5) return 'text-yellow-400';
		return 'text-red-400';
	}
</script>

<svelte:head>
	<title>Daystrom — Settings</title>
</svelte:head>

<div class="max-w-lg mx-auto px-4 pt-[var(--sat)]">
	<header class="pt-6 pb-4">
		<h1 class="text-2xl font-bold text-slate-100">Settings</h1>
	</header>

	<!-- Tab bar -->
	<div class="flex gap-1 bg-slate-900 rounded-xl p-1 mb-4">
		{#each [['memories', '🧠 Memories'], ['model', '📊 Model'], ['health', '💚 Health']] as [tab, label]}
			<button
				onclick={() => switchTab(tab as any)}
				class="flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
					{activeTab === tab ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-300'}"
			>
				{label}
			</button>
		{/each}
	</div>

	<!-- Memories tab -->
	{#if activeTab === 'memories'}
		<!-- Stats bar -->
		{#if memoryStats}
			<div class="flex gap-3 mb-4 text-sm">
				<span class="bg-slate-900 rounded-lg px-3 py-1.5 text-slate-300">
					{memoryStats.total} memories
				</span>
				<span class="bg-slate-900 rounded-lg px-3 py-1.5 text-slate-300">
					avg confidence: <span class={confidenceColor(memoryStats.avg_confidence)}>{memoryStats.avg_confidence}</span>
				</span>
			</div>
		{/if}

		<!-- Filter -->
		<div class="flex gap-2 mb-4 overflow-x-auto">
			{#each ['', 'fact', 'preference', 'pattern', 'context', 'association'] as type}
				<button
					onclick={() => { memoryFilter = type; loadMemories(); }}
					class="px-3 py-1 rounded-full text-xs whitespace-nowrap transition-colors
						{memoryFilter === type ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'}"
				>
					{type || 'All'}
				</button>
			{/each}
		</div>

		<!-- Memory list -->
		{#if loadingMemories}
			<div class="text-center py-8 text-slate-500">Loading...</div>
		{:else if memories.length === 0}
			<div class="text-center py-12">
				<p class="text-slate-500">No memories yet</p>
				<p class="text-slate-600 text-sm mt-1">Daystrom learns as you add items</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each memories as memory (memory.id)}
					<div class="bg-slate-900 rounded-xl p-3 border border-slate-800 group">
						<div class="flex items-start gap-2">
							<span class="text-lg flex-shrink-0">{typeIcon(memory.memory_type)}</span>
							<div class="flex-1 min-w-0">
								<p class="text-sm text-slate-200">{memory.content}</p>
								<div class="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
									<span class={confidenceColor(memory.confidence)}>
										{Math.round(memory.confidence * 100)}% confident
									</span>
									<span>accessed {memory.access_count}x</span>
									<span>{memory.memory_type}</span>
								</div>
							</div>
							<button
								onclick={() => deleteMemory(memory.id)}
								class="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400
									transition-all text-sm px-2 py-1"
								title="Delete memory"
							>
								✕
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

	<!-- Model tab -->
	{:else if activeTab === 'model'}
		{#if loadingModel}
			<div class="text-center py-8 text-slate-500">Loading...</div>
		{:else if model}
			<div class="space-y-4">
				<!-- Type distribution -->
				<div class="bg-slate-900 rounded-xl p-4 border border-slate-800">
					<h3 class="text-sm font-semibold text-slate-300 mb-3">Item Type Distribution</h3>
					{#each Object.entries(model.type_distribution || {}) as [type, count]}
						<div class="flex items-center justify-between py-1">
							<span class="text-sm text-slate-400">{type}</span>
							<span class="text-sm text-slate-200">{count}</span>
						</div>
					{/each}
				</div>

				<!-- Task completion -->
				<div class="bg-slate-900 rounded-xl p-4 border border-slate-800">
					<h3 class="text-sm font-semibold text-slate-300 mb-3">Task Metrics</h3>
					<div class="flex items-center justify-between py-1">
						<span class="text-sm text-slate-400">Completion rate</span>
						<span class="text-sm text-green-400">{Math.round((model.task_completion_rate || 0) * 100)}%</span>
					</div>
					{#if model.avg_completion_hours}
						<div class="flex items-center justify-between py-1">
							<span class="text-sm text-slate-400">Avg completion time</span>
							<span class="text-sm text-slate-200">{model.avg_completion_hours}h</span>
						</div>
					{/if}
					<div class="flex items-center justify-between py-1">
						<span class="text-sm text-slate-400">Classification corrections</span>
						<span class="text-sm text-slate-200">{model.classification_corrections || 0}</span>
					</div>
					<div class="flex items-center justify-between py-1">
						<span class="text-sm text-slate-400">Active memories</span>
						<span class="text-sm text-slate-200">{model.active_memories || 0}</span>
					</div>
				</div>

				<!-- Tag affinity -->
				{#if model.tag_affinity && Object.keys(model.tag_affinity).length > 0}
					<div class="bg-slate-900 rounded-xl p-4 border border-slate-800">
						<h3 class="text-sm font-semibold text-slate-300 mb-3">Tag Affinity (AI acceptance rate)</h3>
						{#each Object.entries(model.tag_affinity).sort((a, b) => (b[1] as number) - (a[1] as number)).slice(0, 15) as [tag, rate]}
							<div class="flex items-center justify-between py-1">
								<span class="text-sm text-slate-400">{tag}</span>
								<div class="flex items-center gap-2">
									<div class="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
										<div class="h-full bg-blue-500 rounded-full" style="width: {(rate as number) * 100}%"></div>
									</div>
									<span class="text-xs text-slate-500 w-8 text-right">{Math.round((rate as number) * 100)}%</span>
								</div>
							</div>
						{/each}
					</div>
				{/if}

				<!-- Capture hours -->
				{#if model.capture_hours && Object.keys(model.capture_hours).length > 0}
					<div class="bg-slate-900 rounded-xl p-4 border border-slate-800">
						<h3 class="text-sm font-semibold text-slate-300 mb-3">Capture Time Patterns</h3>
						<div class="flex items-end gap-0.5 h-16">
							{#each Array.from({length: 24}, (_, i) => i) as hour}
								{@const count = model.capture_hours[hour] || 0}
								{@const max = Math.max(...Object.values(model.capture_hours) as number[])}
								<div
									class="flex-1 bg-blue-500/60 rounded-t-sm transition-all"
									style="height: {max > 0 ? (count / max) * 100 : 0}%"
									title="{hour}:00 — {count} items"
								></div>
							{/each}
						</div>
						<div class="flex justify-between mt-1 text-xs text-slate-600">
							<span>12am</span><span>6am</span><span>12pm</span><span>6pm</span><span>11pm</span>
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<div class="text-center py-8 text-slate-500">No data yet</div>
		{/if}

	<!-- Health tab -->
	{:else if activeTab === 'health'}
		{#if health}
			<div class="space-y-3">
				{#each [['Database', health.database], ['Ollama', health.ollama]] as [name, ok]}
					<div class="bg-slate-900 rounded-xl p-4 border border-slate-800 flex items-center justify-between">
						<span class="text-sm text-slate-300">{name}</span>
						<span class="text-sm {ok ? 'text-green-400' : 'text-red-400'}">
							{ok ? '● Connected' : '● Disconnected'}
						</span>
					</div>
				{/each}
				<div class="bg-slate-900 rounded-xl p-4 border border-slate-800 flex items-center justify-between">
					<span class="text-sm text-slate-300">Status</span>
					<span class="text-sm text-slate-200">{health.status}</span>
				</div>
			</div>
		{:else}
			<div class="text-center py-8 text-slate-500">Loading...</div>
		{/if}
	{/if}
</div>
