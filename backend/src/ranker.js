export function rankPapers(papers, keywords, topN) {
  const kw = (keywords || '')
    .split(/[,\n]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);

  const scored = papers.map((p) => {
    const title = (p.title || '').toLowerCase();
    const abs = (p.summary || '').toLowerCase();
    let score = 0;
    const matches = [];
    for (const k of kw) {
      if (title.includes(k)) {
        score += 3;
        matches.push({ keyword: k, where: 'title' });
      }
      if (abs.includes(k)) {
        score += 1;
        matches.push({ keyword: k, where: 'abstract' });
      }
    }
    return { ...p, score, matches };
  });

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return (b.published || '').localeCompare(a.published || '');
  });

  return scored.slice(0, topN);
}
