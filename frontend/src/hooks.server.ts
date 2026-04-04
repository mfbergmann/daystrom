/**
 * SvelteKit server hook to proxy /api requests to the backend.
 *
 * In development, Vite's built-in proxy handles this. In production
 * (adapter-node), this hook forwards /api/* to the backend service.
 */

import type { Handle } from '@sveltejs/kit';

const API_URL = process.env.API_URL || 'http://localhost:8000';

export const handle: Handle = async ({ event, resolve }) => {
	if (event.url.pathname.startsWith('/api/')) {
		const backendUrl = `${API_URL}${event.url.pathname}${event.url.search}`;

		const headers = new Headers(event.request.headers);
		// Remove host header to avoid upstream confusion
		headers.delete('host');

		try {
			const response = await fetch(backendUrl, {
				method: event.request.method,
				headers,
				body: event.request.method !== 'GET' && event.request.method !== 'HEAD'
					? event.request.body
					: undefined,
				// @ts-ignore - duplex needed for streaming body
				duplex: 'half',
			});

			// For SSE, stream the response through
			return new Response(response.body, {
				status: response.status,
				statusText: response.statusText,
				headers: response.headers,
			});
		} catch (err) {
			return new Response(JSON.stringify({ error: 'Backend unavailable' }), {
				status: 502,
				headers: { 'Content-Type': 'application/json' },
			});
		}
	}

	return resolve(event);
};
