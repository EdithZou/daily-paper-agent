function bad(msg, status = 400) {
  return new Response(JSON.stringify({ ok: false, error: msg }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function ok(data) {
  return new Response(JSON.stringify({ ok: true, ...data }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

const REQUIRED = ['email', 'categories', 'delivery_time', 'timezone', 'top_n', 'summary_lang'];

function validate(body) {
  if (!body || typeof body !== 'object') return 'Body must be JSON object';
  for (const f of REQUIRED) {
    if (body[f] === undefined || body[f] === null || body[f] === '') return `Missing field: ${f}`;
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(body.email)) return 'Invalid email';
  if (!Array.isArray(body.categories) || body.categories.length === 0) return 'categories must be non-empty array';
  if (!/^\d{2}:\d{2}$/.test(body.delivery_time)) return 'delivery_time must be HH:MM';
  const n = Number(body.top_n);
  if (!Number.isInteger(n) || n < 1 || n > 50) return 'top_n must be integer 1..50';
  if (!['zh', 'en', 'none'].includes(body.summary_lang)) return 'summary_lang must be zh|en|none';
  return null;
}

export async function handleSubscribe(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return bad('Invalid JSON');
  }
  const err = validate(body);
  if (err) return bad(err);

  const existing = await env.DB
    .prepare('SELECT id FROM subscriptions WHERE email = ?')
    .bind(body.email)
    .first();

  const args = [
    body.telegram_chat_id || null,
    body.serverchan_key || null,
    JSON.stringify(body.categories),
    body.keywords || '',
    body.delivery_time,
    body.timezone,
    Number(body.top_n),
    body.summary_lang,
  ];

  if (existing) {
    await env.DB.prepare(`
      UPDATE subscriptions
      SET telegram_chat_id = ?, serverchan_key = ?, categories = ?, keywords = ?,
          delivery_time = ?, timezone = ?, top_n = ?, summary_lang = ?, active = 1,
          updated_at = datetime('now')
      WHERE id = ?
    `).bind(...args, existing.id).run();
    return ok({ id: existing.id, updated: true });
  }

  const r = await env.DB.prepare(`
    INSERT INTO subscriptions
      (email, telegram_chat_id, serverchan_key, categories, keywords,
       delivery_time, timezone, top_n, summary_lang)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(body.email, ...args).run();
  return ok({ id: r.meta.last_row_id, created: true });
}

export async function handleUnsubscribe(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return bad('Invalid JSON');
  }
  if (!body.email) return bad('email required');
  await env.DB
    .prepare('UPDATE subscriptions SET active = 0, updated_at = datetime(\'now\') WHERE email = ?')
    .bind(body.email)
    .run();
  return ok({});
}

export async function handleHealth(env) {
  const r = await env.DB.prepare('SELECT count(*) as n FROM subscriptions WHERE active = 1').first();
  return new Response(JSON.stringify({ ok: true, active_subscribers: r?.n ?? 0 }), {
    headers: { 'Content-Type': 'application/json' },
  });
}
