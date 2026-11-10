const ENDPOINT = 'https://export.arxiv.org/api/query';
const UA = 'daily-paper-agent/0.1 (mailto:tzouu2002@gmail.com)';
const BACKOFFS_MS = [5000, 12000, 25000];
const MAX_RETRY_AFTER_MS = 30000;

export async function fetchArxivPapers(categories, maxResults = 100) {
  const query = categories.map((c) => `cat:${c}`).join('+OR+');
  const url = `${ENDPOINT}?search_query=${query}&sortBy=submittedDate&sortOrder=descending&max_results=${maxResults}`;
  const totalAttempts = BACKOFFS_MS.length + 1;

  let lastStatus = null;
  for (let attempt = 0; attempt < totalAttempts; attempt++) {
    const r = await fetch(url, {
      headers: { 'User-Agent': UA, 'Accept': 'application/atom+xml' },
      cf: { cacheTtl: 600, cacheEverything: true },
    });
    if (r.ok) return parseAtom(await r.text());
    lastStatus = r.status;
    if (r.status !== 429 && r.status < 500) {
      throw new Error(`arXiv ${r.status} (non-retryable) for ${url}`);
    }
    if (attempt === totalAttempts - 1) break;
    const wait = resolveBackoff(r, attempt);
    console.warn(`arXiv ${r.status}, retry in ${wait}ms (attempt ${attempt + 1}/${totalAttempts})`);
    await new Promise((res) => setTimeout(res, wait));
  }
  throw new Error(`arXiv ${lastStatus} after ${totalAttempts} attempts for ${url}`);
}

function resolveBackoff(response, attempt) {
  const retryAfter = response.headers.get('Retry-After');
  if (retryAfter) {
    const secs = Number(retryAfter);
    if (Number.isFinite(secs) && secs > 0) {
      return Math.min(secs * 1000, MAX_RETRY_AFTER_MS);
    }
  }
  const base = BACKOFFS_MS[attempt];
  const jitter = Math.floor(Math.random() * (base * 0.2));
  return base + jitter;
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
