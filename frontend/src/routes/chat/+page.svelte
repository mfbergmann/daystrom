<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { api } from '$lib/api/client';
	import type { ConversationSummary, ChatMessage } from '$lib/api/client';

	let conversations: ConversationSummary[] = [];
	let currentConversationId: string | null = null;
	let messages: ChatMessage[] = [];
	let input = '';
	let loading = false;
	let streaming = false;
	let streamedContent = '';
	let showHistory = false;
	let messagesContainer: HTMLDivElement;

	onMount(async () => {
		try {
			conversations = await api.listConversations(20);
		} catch (e) {
			console.error('Failed to load conversations:', e);
		}
	});

	async function scrollToBottom() {
		await tick();
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	async function loadConversation(id: string) {
		try {
			const conv = await api.getConversation(id);
			currentConversationId = id;
			messages = conv.messages;
			showHistory = false;
			await scrollToBottom();
		} catch (e) {
			console.error('Failed to load conversation:', e);
		}
	}

	function startNewChat() {
		currentConversationId = null;
		messages = [];
		showHistory = false;
	}

	async function sendMessage() {
		if (!input.trim() || loading) return;

		const userMessage = input.trim();
		input = '';
		loading = true;

		// Add user message optimistically
		messages = [...messages, {
			id: crypto.randomUUID(),
			role: 'user',
			content: userMessage,
			created_at: new Date().toISOString()
		}];
		await scrollToBottom();

		try {
			// Try streaming first
			const token = localStorage.getItem('daystrom_token');
			const headers: HeadersInit = {
				'Content-Type': 'application/json',
				'Accept': 'text/event-stream'
			};
			if (token) headers['Authorization'] = `Bearer ${token}`;

			const res = await fetch('/api/chat', {
				method: 'POST',
				headers,
				body: JSON.stringify({
					message: userMessage,
					conversation_id: currentConversationId
				})
			});

			if (!res.ok) throw new Error(`Chat failed: ${res.status}`);

			const contentType = res.headers.get('content-type') || '';

			if (contentType.includes('text/event-stream')) {
				// SSE streaming
				streaming = true;
				streamedContent = '';

				const reader = res.body?.getReader();
				const decoder = new TextDecoder();

				if (reader) {
					let buffer = '';
					while (true) {
						const { done, value } = await reader.read();
						if (done) break;

						buffer += decoder.decode(value, { stream: true });
						const lines = buffer.split('\n');
						buffer = lines.pop() || '';

						for (const line of lines) {
							if (line.startsWith('data: ')) {
								try {
									const data = JSON.parse(line.slice(6));
									if (data.conversation_id) {
										currentConversationId = data.conversation_id;
									}
									if (data.content) {
										streamedContent += data.content;
										await scrollToBottom();
									}
								} catch { /* ignore parse errors */ }
							}
						}
					}
				}

				// Finalize streamed message
				if (streamedContent) {
					messages = [...messages, {
						id: crypto.randomUUID(),
						role: 'assistant',
						content: streamedContent,
						created_at: new Date().toISOString()
					}];
				}
				streaming = false;
				streamedContent = '';
			} else {
				// JSON response
				const data = await res.json();
				currentConversationId = data.conversation_id;
				messages = [...messages, {
					id: crypto.randomUUID(),
					role: 'assistant',
					content: data.message,
					created_at: new Date().toISOString()
				}];
			}

			// Refresh conversations list
			conversations = await api.listConversations(20);

		} catch (e) {
			console.error('Chat error:', e);
			messages = [...messages, {
				id: crypto.randomUUID(),
				role: 'assistant',
				content: 'Sorry, something went wrong. Please try again.',
				created_at: new Date().toISOString()
			}];
		} finally {
			loading = false;
			streaming = false;
			await scrollToBottom();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

	async function deleteConversation(id: string, e: Event) {
		e.stopPropagation();
		try {
			await api.deleteConversation(id);
			conversations = conversations.filter(c => c.id !== id);
			if (currentConversationId === id) startNewChat();
		} catch (err) {
			console.error('Delete failed:', err);
		}
	}

	function formatTime(dateStr: string): string {
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
	<title>Daystrom — Chat</title>
</svelte:head>

<div class="flex flex-col h-[calc(100vh-5rem)] max-w-lg mx-auto px-4 pt-[var(--sat)]">
	<!-- Header -->
	<header class="flex items-center justify-between pt-4 pb-3 flex-shrink-0">
		<h1 class="text-xl font-bold text-slate-100">Chat</h1>
		<div class="flex gap-2">
			<button
				on:click={() => showHistory = !showHistory}
				class="px-3 py-1.5 text-xs rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
			>
				{showHistory ? 'Close' : 'History'}
			</button>
			<button
				on:click={startNewChat}
				class="px-3 py-1.5 text-xs rounded-lg bg-sky-600 text-white hover:bg-sky-500"
			>
				New Chat
			</button>
		</div>
	</header>

	<!-- Conversation History Panel -->
	{#if showHistory}
		<div class="mb-3 rounded-xl bg-slate-800/50 p-3 max-h-60 overflow-y-auto flex-shrink-0">
			{#if conversations.length === 0}
				<p class="text-slate-500 text-sm text-center py-4">No conversations yet</p>
			{:else}
				{#each conversations as conv}
					<button
						on:click={() => loadConversation(conv.id)}
						class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-slate-700/50 text-left group {currentConversationId === conv.id ? 'bg-slate-700/50' : ''}"
					>
						<div class="min-w-0 flex-1">
							<p class="text-sm text-slate-200 truncate">{conv.title || 'Untitled'}</p>
							<p class="text-xs text-slate-500">{conv.message_count} messages · {formatTime(conv.updated_at)}</p>
						</div>
						<button
							on:click={(e) => deleteConversation(conv.id, e)}
							class="ml-2 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 text-xs"
						>
							&times;
						</button>
					</button>
				{/each}
			{/if}
		</div>
	{/if}

	<!-- Messages -->
	<div bind:this={messagesContainer} class="flex-1 overflow-y-auto space-y-3 pb-3">
		{#if messages.length === 0 && !streaming}
			<div class="text-center py-16">
				<p class="text-3xl mb-3">&#x1F4AC;</p>
				<p class="text-slate-400 text-sm">Ask Daystrom anything about your tasks and ideas</p>
				<p class="text-slate-600 text-xs mt-1">
					You can also ask to create items, search, or brainstorm
				</p>
			</div>
		{/if}

		{#each messages as msg}
			<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
				<div class="max-w-[85%] rounded-2xl px-4 py-2.5 {msg.role === 'user' ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-200'}">
					<p class="text-sm whitespace-pre-wrap">{msg.content}</p>
					<p class="text-[10px] mt-1 {msg.role === 'user' ? 'text-sky-200' : 'text-slate-500'}">
						{formatTime(msg.created_at)}
					</p>
				</div>
			</div>
		{/each}

		{#if streaming && streamedContent}
			<div class="flex justify-start">
				<div class="max-w-[85%] rounded-2xl px-4 py-2.5 bg-slate-800 text-slate-200">
					<p class="text-sm whitespace-pre-wrap">{streamedContent}<span class="animate-pulse">|</span></p>
				</div>
			</div>
		{/if}

		{#if loading && !streaming}
			<div class="flex justify-start">
				<div class="rounded-2xl px-4 py-2.5 bg-slate-800">
					<div class="flex gap-1">
						<div class="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style="animation-delay: 0ms"></div>
						<div class="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style="animation-delay: 150ms"></div>
						<div class="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style="animation-delay: 300ms"></div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Input -->
	<div class="flex-shrink-0 pb-2 pt-2">
		<div class="flex gap-2 items-end">
			<textarea
				bind:value={input}
				on:keydown={handleKeydown}
				placeholder="Message Daystrom..."
				rows="1"
				disabled={loading}
				class="flex-1 resize-none rounded-xl bg-slate-800 text-white px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-50"
			></textarea>
			<button
				on:click={sendMessage}
				disabled={loading || !input.trim()}
				class="rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed p-3 text-white flex-shrink-0"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M12 5l7 7-7 7" />
				</svg>
			</button>
		</div>
	</div>
</div>
