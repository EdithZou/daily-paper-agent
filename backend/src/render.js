function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function escapeMd(s) {
  return String(s).replace(/[*_`\[\]()]/g, '\\$&');
}

function authorsLine(authors) {
  const head = authors.slice(0, 4).join(', ');
  return authors.length > 4 ? `${head} 等` : head;
}

export function renderEmailHtml(papers, dateStr) {
  const items = papers.map((p, i) => `
    <li style="margin-bottom:18px;list-style:none;padding-left:0">
      <div style="font-weight:600;font-size:15px;line-height:1.4">
        ${i + 1}. <a href="${escapeHtml(p.id)}" style="color:#0f172a;text-decoration:none">${escapeHtml(p.title)}</a>
      </div>
      <div style="color:#64748b;font-size:13px;margin:4px 0">${escapeHtml(authorsLine(p.authors))}</div>
      ${p.aiSummary ? `<div style="font-size:14px;line-height:1.55;color:#1e293b;margin:6px 0">${escapeHtml(p.aiSummary)}</div>` : ''}
      <div style="font-size:12px;color:#94a3b8;margin-top:4px">${escapeHtml(p.categories.join(' · '))}</div>
    </li>`).join('');
  return `<!doctype html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#0f172a;background:#f8fafc">
    <div style="background:white;padding:24px;border-radius:8px">
      <h1 style="font-size:20px;margin:0 0 4px">每日 arXiv 论文</h1>
      <div style="color:#64748b;font-size:13px;margin-bottom:20px">${escapeHtml(dateStr)} · 共 ${papers.length} 篇</div>
      <ul style="padding:0;margin:0">${items}</ul>
    </div>
    <div style="text-align:center;color:#94a3b8;font-size:12px;margin-top:16px">daily-paper-agent</div>
  </body></html>`;
}

export function renderMarkdown(papers, dateStr) {
  const head = `*每日 arXiv · ${escapeMd(dateStr)} · ${papers.length} 篇*\n\n`;
  return head + papers.map((p, i) => {
    const title = escapeMd(p.title);
    const authors = escapeMd(authorsLine(p.authors));
    const summary = p.aiSummary ? `\n${escapeMd(p.aiSummary)}` : '';
    return `*${i + 1}. ${title}*\n${authors}${summary}\n${p.id}`;
  }).join('\n\n');
}
