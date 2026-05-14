const MODEL = 'claude-haiku-4-5-20251001';
const ENDPOINT = 'https://api.anthropic.com/v1/messages';

export async function summarize(paper, lang, apiKey) {
  if (lang === 'none' || !apiKey) return null;
  const prompt = lang === 'zh'
    ? `用 1-2 句中文总结这篇 arXiv 论文的核心贡献，避免空话和"本文提出"等套话。\n\n标题：${paper.title}\n\n摘要：${paper.summary}`
    : `Summarize this arXiv paper's core contribution in 1-2 sentences. Be concrete; skip filler like "this paper proposes".\n\nTitle: ${paper.title}\n\nAbstract: ${paper.summary}`;

  const r = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 200,
      messages: [{ role: 'user', content: prompt }],
    }),
  });
  if (!r.ok) {
    console.error('Anthropic', r.status, await r.text().catch(() => ''));
    return null;
  }
  const data = await r.json();
  return data?.content?.[0]?.text?.trim() ?? null;
}
