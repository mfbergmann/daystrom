import { writable } from 'svelte/store';
import { updateItemInStore } from './items';

let eventSource: EventSource | null = null;

// Agent task events store
export const agentEvents = writable<{ type: string; data: any }[]>([]);

export function connectSSE() {
	if (typeof window === 'undefined') return;
	if (eventSource) return;

	const token = localStorage.getItem('daystrom_token');
	const url = token ? `/api/events?token=${token}` : '/api/events';

	eventSource = new EventSource(url);

	eventSource.addEventListener('item_enriched', (e) => {
		try {
			const data = JSON.parse(e.data);
			updateItemInStore({
				id: data.item_id,
				item_type: data.item_type,
				parsed_title: data.parsed_title,
				ai_confidence: data.ai_confidence,
				enrichment_status: 'complete',
				tags: data.tags?.map((name: string) => ({ id: '', name, source: 'ai', confidence: null })) || [],
			});
		} catch (err) {
			console.error('SSE parse error:', err);
		}
	});

	// Agent events
	eventSource.addEventListener('agent_started', (e) => {
		try {
			const data = JSON.parse(e.data);
			agentEvents.update(events => [...events.slice(-50), { type: 'started', data }]);
		} catch (err) { /* ignore */ }
	});

	eventSource.addEventListener('agent_step', (e) => {
		try {
			const data = JSON.parse(e.data);
			agentEvents.update(events => [...events.slice(-50), { type: 'step', data }]);
		} catch (err) { /* ignore */ }
	});

	eventSource.addEventListener('agent_completed', (e) => {
		try {
			const data = JSON.parse(e.data);
			agentEvents.update(events => [...events.slice(-50), { type: 'completed', data }]);
		} catch (err) { /* ignore */ }
	});

	eventSource.addEventListener('agent_failed', (e) => {
		try {
			const data = JSON.parse(e.data);
			agentEvents.update(events => [...events.slice(-50), { type: 'failed', data }]);
		} catch (err) { /* ignore */ }
	});

	eventSource.addEventListener('ping', () => {
		// keepalive, ignore
	});

	eventSource.onerror = () => {
		eventSource?.close();
		eventSource = null;
		// Reconnect after 3 seconds
		setTimeout(connectSSE, 3000);
	};
}

export function disconnectSSE() {
	eventSource?.close();
	eventSource = null;
}
