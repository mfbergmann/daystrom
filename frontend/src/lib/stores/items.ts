import { writable } from 'svelte/store';
import { api, type Item } from '$lib/api/client';

export const items = writable<Item[]>([]);
export const loading = writable(false);
export const totalItems = writable(0);

export async function loadItems(params?: { status?: string; item_type?: string; tag?: string }) {
	loading.set(true);
	try {
		const result = await api.listItems({ ...params, limit: 100 });
		items.set(result.items);
		totalItems.set(result.total);
	} catch (e) {
		console.error('Failed to load items:', e);
	} finally {
		loading.set(false);
	}
}

export async function captureItem(content: string, tags?: string[]): Promise<Item | null> {
	try {
		const item = await api.captureItem(content, tags);
		items.update(current => [item, ...current]);
		return item;
	} catch (e) {
		console.error('Failed to capture item:', e);
		return null;
	}
}

export async function completeItem(id: string) {
	try {
		const updated = await api.updateItem(id, { status: 'done' } as any);
		items.update(current => current.map(i => i.id === id ? updated : i));
	} catch (e) {
		console.error('Failed to complete item:', e);
	}
}

export async function deleteItem(id: string) {
	try {
		await api.deleteItem(id);
		items.update(current => current.filter(i => i.id !== id));
	} catch (e) {
		console.error('Failed to delete item:', e);
	}
}

export function updateItemInStore(updated: Partial<Item> & { id: string }) {
	items.update(current =>
		current.map(i => i.id === updated.id ? { ...i, ...updated } : i)
	);
}
