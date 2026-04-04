import { updateItemInStore } from './items';

let eventSource: EventSource | null = null;

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
