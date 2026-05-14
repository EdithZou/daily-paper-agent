export async function pushEmail(to, subject, html, env) {
  if (!env.RESEND_API_KEY) return { ok: false, error: 'RESEND_API_KEY not configured' };
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: env.EMAIL_FROM || 'Daily Paper <onboarding@resend.dev>',
      to: [to],
      subject,
      html,
    }),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    return { ok: false, error: `Resend ${r.status}: ${text.slice(0, 200)}` };
  }
  return { ok: true };
}

export async function pushTelegram(chatId, text, env) {
  if (!env.TELEGRAM_BOT_TOKEN) return { ok: false, error: 'TELEGRAM_BOT_TOKEN not configured' };
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    }),
  });
  if (!r.ok) return { ok: false, error: `Telegram ${r.status}` };
  return { ok: true };
}

export async function pushServerChan(sendKey, title, desp) {
  const r = await fetch(`https://sctapi.ftqq.com/${sendKey}.send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ title, desp }),
  });
  if (!r.ok) return { ok: false, error: `Server酱 HTTP ${r.status}` };
  const data = await r.json().catch(() => ({}));
  if (data.code !== 0) return { ok: false, error: data.message || 'unknown' };
  return { ok: true };
}
