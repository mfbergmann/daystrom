<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { api } from '$lib/api/client';
	import { agentEvents } from '$lib/stores/sse';
	import type { AgentTask } from '$lib/api/client';

	let tasks: AgentTask[] = [];
	let total = 0;
	let loading = true;
	let filter: string | undefined = undefined;
	let expandedTask: string | null = null;
	let newPrompt = '';
	let creating = false;

	const unsubscribe = agentEvents.subscribe(() => {
		// Refresh when we get agent events
		loadTasks();
	});

	onMount(() => loadTasks());
	onDestroy(() => unsubscribe());

	async function loadTasks() {
		try {
			const result = await api.listAgentTasks({ status: filter, limit: 50 });
			tasks = result.tasks;
			total = result.total;
		} catch (e) {
			console.error('Failed to load agent tasks:', e);
		} finally {
			loading = false;
		}
	}

	async function createTask() {
		if (!newPrompt.trim() || creating) return;
		creating = true;
		try {
			await api.createAgentTask(newPrompt.trim());
			newPrompt = '';
			await loadTasks();
		} catch (e) {
			console.error('Failed to create agent task:', e);
		} finally {
			creating = false;
		}
	}

	async function cancelTask(id: string) {
		try {
			await api.cancelAgentTask(id);
			await loadTasks();
		} catch (e) {
			console.error('Failed to cancel task:', e);
		}
	}

	function toggleExpand(id: string) {
		expandedTask = expandedTask === id ? null : id;
	}

	function statusColor(status: string): string {
		switch (status) {
			case 'completed': return 'text-green-400';
			case 'running': return 'text-amber-400';
			case 'pending': return 'text-sky-400';
			case 'failed': return 'text-red-400';
			case 'cancelled': return 'text-slate-500';
			default: return 'text-slate-400';
		}
	}

	function statusIcon(status: string): string {
		switch (status) {
			case 'completed': return '\u2713';
			case 'running': return '\u25CB';
			case 'pending': return '\u2026';
			case 'failed': return '\u2717';
			case 'cancelled': return '\u2014';
			default: return '?';
		}
	}

	function typeIcon(type: string): string {
		switch (type) {
			case 'research': return '\uD83D\uDD2C';
			case 'summarize': return '\uD83D\uDCDD';
			case 'find': return '\uD83D\uDD0D';
			case 'compare': return '\u2696\uFE0F';
			case 'plan': return '\uD83D\uDCCB';
			default: return '\uD83E\uDD16';
		}
	}

	function formatTime(dateStr: string | null): string {
		if (!dateStr) return '';
		const d = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - d.getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return 'just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		const diffHr = Math.floor(diffMin / 60);
		if (diffHr < 24) return `${diffHr}h ago`;
		return d.toLocaleDateString();
	}
</script>

<svelte:head>
	<title>Daystrom — Agents</title>
</svelte:head>

<div class="max-w-lg mx-auto px-4 pt-[var(--sat)]">
	<header class="pt-6 pb-4">
		<h1 class="text-2xl font-bold text-slate-100">Agent Tasks</h1>
		<p class="text-sm text-slate-500 mt-1">Autonomous AI tasks and research</p>
	</header>

	<!-- Create new task -->
	<div class="mb-4">
		<div class="flex gap-2">
			<input
				bind:value={newPrompt}
				on:keydown={(e) => e.key === 'Enter' && createTask()}
				placeholder="Ask an agent to research something..."
				disabled={creating}
				class="flex-1 rounded-xl bg-slate-800 text-white px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
			/>
			<button
				on:click={createTask}
				disabled={creating || !newPrompt.trim()}
				class="rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-40 px-4 py-3 text-white text-sm font-medium"
			>
				Go
			</button>
		</div>
	</div>

	<!-- Filter tabs -->
	<div class="flex gap-2 mb-4 overflow-x-auto">
		{#each [undefined, 'running', 'completed', 'failed'] as f}
			<button
				on:click={() => { filter = f; loadTasks(); }}
				class="px-3 py-1 rounded-full text-xs whitespace-nowrap {filter === f ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}"
			>
				{f || 'All'}
			</button>
		{/each}
	</div>

	<!-- Task list -->
	{#if loading}
		<div class="text-center py-12 text-slate-500">Loading...</div>
	{:else if tasks.length === 0}
		<div class="text-center py-12">
			<p class="text-3xl mb-3">&#x1F916;</p>
			<p class="text-slate-400 text-sm">No agent tasks yet</p>
			<p class="text-slate-600 text-xs mt-1">
				Create research tasks or they'll spawn automatically from actionable items
			</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each tasks as task}
				<div
					role="button"
					tabindex="0"
					on:click={() => toggleExpand(task.id)}
					on:keydown={(e) => e.key === 'Enter' && toggleExpand(task.id)}
					class="w-full text-left rounded-xl bg-slate-800/60 p-4 hover:bg-slate-800 transition-colors cursor-pointer"
				>
					<div class="flex items-start gap-3">
						<span class="text-lg flex-shrink-0">{typeIcon(task.task_type)}</span>
						<div class="flex-1 min-w-0">
							<p class="text-sm text-slate-200 line-clamp-2">{task.prompt}</p>
							<div class="flex items-center gap-2 mt-1.5">
								<span class="text-xs {statusColor(task.status)} font-medium">
									{statusIcon(task.status)} {task.status}
								</span>
								{#if task.steps}
									<span class="text-xs text-slate-600">{task.steps.length} steps</span>
								{/if}
								<span class="text-xs text-slate-600">{formatTime(task.created_at)}</span>
							</div>
						</div>
						{#if task.status === 'running'}
							<div class="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
						{/if}
					</div>

					<!-- Expanded details -->
					{#if expandedTask === task.id}
						<div class="mt-3 pt-3 border-t border-slate-700/50">
							{#if task.result_summary}
								<div class="mb-3">
									<p class="text-xs text-slate-500 mb-1 font-medium">Result</p>
									<p class="text-sm text-slate-300 whitespace-pre-wrap">{task.result_summary}</p>
								</div>
							{/if}

							{#if task.steps && task.steps.length > 0}
								<div class="mb-3">
									<p class="text-xs text-slate-500 mb-1 font-medium">Steps</p>
									<div class="space-y-1.5">
										{#each task.steps as step, i}
											<div class="text-xs bg-slate-900/50 rounded-lg p-2">
												<span class="text-slate-600">#{i + 1}</span>
												<span class="text-slate-400 ml-1">{step.action}</span>
												{#if step.result}
													<p class="text-slate-500 mt-0.5 line-clamp-3">{step.result}</p>
												{/if}
											</div>
										{/each}
									</div>
								</div>
							{/if}

							{#if task.status === 'running' || task.status === 'pending'}
								<button
									on:click|stopPropagation={() => cancelTask(task.id)}
									class="text-xs text-red-400 hover:text-red-300 mt-1"
								>
									Cancel task
								</button>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>

		<p class="text-xs text-slate-600 text-center mt-4 mb-8">{total} total tasks</p>
	{/if}
</div>
