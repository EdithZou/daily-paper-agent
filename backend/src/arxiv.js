const ENDPOINT = 'https://export.arxiv.org/api/query';
const UA = 'daily-paper-agent/0.1 (mailto:tzouu2002@gmail.com)';

export async function fetchArxivPapers(categories, maxResults = 100) {
  const query = categories.map((c) => `cat:${c}`).join('+OR+');
  const url = `${ENDPOINT}?search_query=${query}&sortBy=submittedDate&sortOrder=descending&max_results=${maxResults}`;

  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await fetch(url, {
      headers: { 'User-Agent': UA, 'Accept': 'application/atom+xml' },
      cf: { cacheTtl: 600, cacheEverything: true },
    });
    if (r.ok) return parseAtom(await r.text());
    if (r.status === 429 || r.status >= 500) {
      const wait = 3000 * (attempt + 1);
      console.warn(`arXiv ${r.status}, retry in ${wait}ms (attempt ${attempt + 1}/3)`);
      await new Promise((res) => setTimeout(res, wait));
      continue;
    }
    throw new Error(`arXiv ${r.status}`);
  }
  throw new Error('arXiv 429 after 3 retries');
}

function parseAtom(xml) {
  const entries = [];
  const re = /<entry>([\s\S]*?)<\/entry>/g;
  let m;
  while ((m = re.exec(xml))) {
    const block = m[1];
    const idRaw = take(block, 'id');
    if (!idRaw) continue;
    entries.push({
      id: idRaw,
      title: clean(take(block, 'title')),
      summary: clean(take(block, 'summary')),
      published: take(block, 'published'),
      updated: take(block, 'updated'),
      authors: [...block.matchAll(/<author>\s*<name>([^<]+)<\/name>\s*<\/author>/g)].map((x) => x[1].trim()),
      categories: [...block.matchAll(/<category\s+term="([^"]+)"/g)].map((x) => x[1]),
    });
  }
  return entries;
}

function take(block, tag) {
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`);
  const m = block.match(re);
  return m ? m[1].trim() : '';
}

function clean(s) {
  return s.replace(/\s+/g, ' ').trim();
}
