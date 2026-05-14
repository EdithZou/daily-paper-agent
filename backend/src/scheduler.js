import { fetchArxivPapers } from './arxiv.js';
import { rankPapers } from './ranker.js';
import { summarize } from './summarizer.js';
import { pushEmail, pushTelegram, pushServerChan } from './push.js';
import { renderEmailHtml, renderMarkdown } from './render.js';

const FRESH_WINDOW_HOURS = 36;

export async function runDailyPush(env) {
  const { results: subs } = await env.DB
    .prepare('SELECT * FROM subscriptions WHERE active = 1')
    .all();
  const now = new Date();

  for (const sub of subs) {
    try {
      if (!isDeliveryMinute(now, sub.delivery_time, sub.timezone)) continue;
      await processOne(sub, now, env);
    } catch (err) {
      console.error(`subscription ${sub.id} failed:`, err?.stack || err);
    }
  }
}

async function processOne(sub, now, env) {
  const cats = JSON.parse(sub.categories);
  const papers = await fetchArxivPapers(cats, 100);

  const cutoff = new Date(now.getTime() - FRESH_WINDOW_HOURS * 3600 * 1000);
  const fresh = papers.filter((p) => {
    const t = p.published ? new Date(p.published) : null;
    return t && t >= cutoff;
  });

  const sent = await env.DB
    .prepare('SELECT paper_id FROM sends WHERE subscription_id = ?')
    .bind(sub.id)
    .all();
  const sentSet = new Set(sent.results.map((r) => r.paper_id));
  const unsent = fresh.filter((p) => !sentSet.has(p.id));

  const top = rankPapers(unsent, sub.keywords || '', sub.top_n);
  if (top.length === 0) return;

  if (sub.summary_lang !== 'none') {
    for (const p of top) {
      p.aiSummary = await summarize(p, sub.summary_lang, env.ANTHROPIC_API_KEY);
    }
  }

  const dateStr = formatDateInTz(now, sub.timezone);
  const dispatch = await sendAll(sub, top, dateStr, env);

  const stmts = [];
  for (const p of top) {
    for (const [channel, result] of Object.entries(dispatch)) {
      stmts.push(env.DB.prepare(`
        INSERT OR IGNORE INTO sends (subscription_id, paper_id, channel, status, error)
        VALUES (?, ?, ?, ?, ?)
      `).bind(sub.id, p.id, channel, result.ok ? 'ok' : 'fail', result.error || null));
    }
  }
  if (stmts.length) await env.DB.batch(stmts);
}

async function sendAll(sub, papers, dateStr, env) {
  const out = {};
  const subject = `每日 arXiv · ${dateStr} · ${papers.length} 篇`;
  if (sub.email) {
    out.email = await pushEmail(sub.email, subject, renderEmailHtml(papers, dateStr), env);
  }
  if (sub.telegram_chat_id) {
    out.telegram = await pushTelegram(sub.telegram_chat_id, renderMarkdown(papers, dateStr), env);
  }
  if (sub.serverchan_key) {
    out.serverchan = await pushServerChan(sub.serverchan_key, subject, renderMarkdown(papers, dateStr));
  }
  return out;
}

function isDeliveryMinute(now, deliveryTime, tz) {
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: tz, hour12: false, hour: '2-digit', minute: '2-digit',
  });
  const parts = fmt.formatToParts(now);
  const hh = parts.find((p) => p.type === 'hour')?.value;
  const mm = parts.find((p) => p.type === 'minute')?.value;
  return `${hh}:${mm}` === deliveryTime;
}

function formatDateInTz(now, tz) {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
  });
  return fmt.format(now);
}
