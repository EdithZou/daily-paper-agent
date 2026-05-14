export function rankPapers(papers, keywords, topN) {
  const kw = (keywords || '')
    .split(/[,\n]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);

  const scored = papers.map((p) => {
    const title = (p.title || '').toLowerCase();
    const abs = (p.summary || '').toLowerCase();
    let score = 0;
    for (const k of kw) {
      if (title.includes(k)) score += 3;
      if (abs.includes(k)) score += 1;
    }
    return { ...p, score };
  });

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return (b.published || '').localeCompare(a.published || '');
  });

  return scored.slice(0, topN);
}
