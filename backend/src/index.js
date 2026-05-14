import { handleSubscribe, handleUnsubscribe, handleHealth } from './routes.js';
import { runDailyPush } from './scheduler.js';

function withCors(env, response) {
  const origin = env.ALLOWED_ORIGIN || '*';
  const headers = new Headers(response.headers);
  headers.set('Access-Control-Allow-Origin', origin);
  headers.set('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Content-Type');
  headers.set('Access-Control-Max-Age', '86400');
  return new Response(response.body, { status: response.status, headers });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return withCors(env, new Response(null, { status: 204 }));
    }
    const url = new URL(request.url);

    if (url.pathname === '/api/health') {
      return withCors(env, await handleHealth(env));
    }
    if (url.pathname === '/api/subscribe' && request.method === 'POST') {
      return withCors(env, await handleSubscribe(request, env));
    }
    if (url.pathname === '/api/unsubscribe' && request.method === 'POST') {
      return withCors(env, await handleUnsubscribe(request, env));
    }
    return withCors(env, new Response('Not found', { status: 404 }));
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(runDailyPush(env));
  },
};
