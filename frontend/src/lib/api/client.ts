const BASE = '/api';

function getHeaders(): HeadersInit {
	const headers: HeadersInit = { 'Content-Type': 'application/json' };
	if (typeof window !== 'undefined') {
		const token = localStorage.getItem('daystrom_token');
		if (token) headers['Authorization'] = `Bearer ${token}`;
	}
	return headers;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		...options,
		headers: { ...getHeaders(), ...(options.headers || {}) }
	});
	if (!res.ok) {
		if (res.status === 401 && typeof window !== 'undefined') {
			localStorage.removeItem('daystrom_token');
			window.location.href = '/';
		}
		throw new Error(`API error: ${res.status}`);
	}
	if (res.status === 204) return undefined as T;
	return res.json();
}

export type Item = {
	id: string;
	content: string;
	parsed_title: string | null;
	item_type: string | null;
	status: string;
	enrichment_status: string;
	priority: string | null;
	due_date: string | null;
	completed_at: string | null;
	parent_id: string | null;
	ai_confidence: number | null;
	tags: { id: string; name: string; source: string; confidence: number | null }[];
	created_at: string;
	updated_at: string;
};

export type ItemList = {
	items: Item[];
	total: number;
};

export type Tag = {
	id: string;
	name: string;
	tag_type: string;
	color: string | null;
	usage_count: number;
	auto_generated: boolean;
};

export type Memory = {
	id: string;
	content: string;
	memory_type: string;
	confidence: number;
	access_count: number;
	created_at: string;
	updated_at: string;
};

export type MemoryStats = {
	total: number;
	by_type: Record<string, number>;
	avg_confidence: number;
};

export const api = {
	// Auth
	authStatus: () => request<{ auth_required: boolean }>('/auth/status'),
	login: (pin: string) => request<{ access_token: string }>('/auth/login', {
		method: 'POST', body: JSON.stringify({ pin })
	}),

	// Items
	captureItem: (content: string, tags?: string[]) =>
		request<Item>('/items/capture', {
			method: 'POST',
			body: JSON.stringify({ content, tags })
		}),
	listItems: (params?: { status?: string; item_type?: string; tag?: string; limit?: number; offset?: number }) => {
		const search = new URLSearchParams();
		if (params) {
			Object.entries(params).forEach(([k, v]) => {
				if (v !== undefined) search.set(k, String(v));
			});
		}
		return request<ItemList>(`/items?${search}`);
	},
	getItem: (id: string) => request<Item>(`/items/${id}`),
	updateItem: (id: string, data: Partial<Item>) =>
		request<Item>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
	deleteItem: (id: string) =>
		request<void>(`/items/${id}`, { method: 'DELETE' }),

	// Tags
	listTags: () => request<Tag[]>('/tags'),
	addTagToItem: (itemId: string, tagName: string) =>
		request<any>(`/tags/items/${itemId}/tags`, {
			method: 'POST', body: JSON.stringify({ tag_name: tagName })
		}),
	removeTagFromItem: (itemId: string, tagName: string) =>
		request<any>(`/tags/items/${itemId}/tags/${encodeURIComponent(tagName)}`, { method: 'DELETE' }),

	// Search
	search: (q: string, limit = 20) =>
		request<any[]>(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),

	// Memories
	listMemories: (params?: { memory_type?: string; limit?: number }) => {
		const search = new URLSearchParams();
		if (params) {
			Object.entries(params).forEach(([k, v]) => {
				if (v !== undefined) search.set(k, String(v));
			});
		}
		return request<Memory[]>(`/memories?${search}`);
	},
	memoryStats: () => request<MemoryStats>('/memories/stats'),
	updateMemory: (id: string, data: { content?: string; confidence?: number }) =>
		request<Memory>(`/memories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
	deleteMemory: (id: string) => request<void>(`/memories/${id}`, { method: 'DELETE' }),

	// Learning
	behavioralModel: () => request<any>('/learning/model'),
	associations: (itemId: string) => request<any[]>(`/learning/associations/${itemId}`),
	interactions: (limit = 50) => request<any[]>(`/learning/interactions?limit=${limit}`),

	// Health
	health: () => request<{ status: string; database: boolean; ollama: boolean }>('/health'),
};
