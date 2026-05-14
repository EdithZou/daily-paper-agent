# Daily Paper Agent

A lightweight, local-first academic paper recommendation agent for macOS.
Fetches recent arXiv papers, ranks them against your research interests, and
generates a daily Markdown report with optional Chinese summaries via Claude.

---

## Overview

| Feature | Details |
|---------|---------|
| Data source | arXiv API (cs.CV, eess.IV, cs.AI by default) |
| Ranking | Keyword/rule-based — transparent and configurable |
| Summaries | Claude (Haiku) if `ANTHROPIC_API_KEY` is set, otherwise template |
| Deduplication | SQLite — never re-recommends the same paper |
| Scheduling | macOS launchd (9 AM daily) |
| Dependencies | Python 3.10+, no Docker, no database server |

---

## Local Deployment on macOS

### 1. Clone the repo

```bash
git clone <repo-url>
cd daily-paper-agent
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your config

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to adjust categories, keywords, and LLM settings.

### 5. (Optional) Add your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add that line to your `~/.zshrc` to make it permanent, or put it in a
`.env` file and source it in `scripts/run_daily.sh`.

---

## Configuration

`config.yaml` controls all behaviour. The file is git-ignored; only
`config.example.yaml` is committed.

Key sections:

| Section | Purpose |
|---------|---------|
| `arxiv.categories` | arXiv category codes to query |
| `arxiv.max_results` | Max papers fetched per run |
| `research_interests.topics` | Multi-word topic phrases (higher weight) |
| `research_interests.keywords` | Single keywords (lower weight) |
| `llm.provider` | `anthropic` or `none` |
| `llm.model` | Claude model ID |
| `output.db_path` | SQLite path (default `data/papers.db`) |
| `output.reports_dir` | Report directory (default `data/reports/`) |

API keys must be set as environment variables — never in `config.yaml`:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Running Manually

```bash
source .venv/bin/activate

# Dry-run: fetch and rank, print report, nothing written to disk
python -m src.main --dry-run

# Run for today and save results
python -m src.main --date today

# Run for a specific date
python -m src.main --date 2024-05-06

# Use a custom config path
python -m src.main --config /path/to/config.yaml
```

Reports are saved to `data/reports/YYYY-MM-DD.md`.

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

The test suite is fully offline — no network requests are made.

---

## Scheduling with launchd (Recommended on macOS)

launchd is macOS's native job scheduler and is more reliable than cron
because it runs jobs even after a reboot without requiring a login shell.

### Install the 9 AM daily job

```bash
chmod +x scripts/install_launchd.sh
./scripts/install_launchd.sh
```

The script:
1. Fills in your username and project path in the plist template.
2. Writes the plist to `~/Library/LaunchAgents/`.
3. Loads the job immediately.

### Verify

```bash
launchctl list | grep daily-paper-agent
```

### Trigger a manual run via launchd

```bash
launchctl start com.$(whoami).daily-paper-agent
```

### View logs

```bash
tail -f logs/launchd.out.log
tail -f logs/launchd.err.log
```

### Uninstall

```bash
LABEL="com.$(whoami).daily-paper-agent"
launchctl unload ~/Library/LaunchAgents/${LABEL}.plist
rm ~/Library/LaunchAgents/${LABEL}.plist
```

---

## Optional Cron Fallback

If you prefer cron, add this to your crontab (`crontab -e`):

```cron
0 9 * * * /path/to/daily-paper-agent/scripts/run_daily.sh
```

Note: cron on macOS may not inherit your shell environment (PATH, API keys).
You may need to add `export ANTHROPIC_API_KEY=...` at the top of
`scripts/run_daily.sh`. launchd is recommended because it handles
environment and missed runs more gracefully.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'src'`**
Run from the project root with `python -m src.main`, not `python src/main.py`.
Make sure `.venv` is activated.

**arXiv fetching returns 0 papers**
arXiv rate-limits unauthenticated API calls. Try again after a few minutes,
or reduce `max_results` in `config.yaml`.

**No LLM summary (falls back to template)**
Ensure `ANTHROPIC_API_KEY` is exported in the shell where the agent runs.
The template fallback is always safe to use.

**launchd job does not appear to run**
Check `logs/launchd.err.log` for errors. Common issues:
- `.venv` not present at the expected path — run setup again.
- `config.yaml` missing — copy from `config.example.yaml`.
- System sleep at 9 AM — launchd will not catch up by default
  (set `RunAtLoad` to `true` in the plist if you want it to run on next wake).

---

## How to Extend Later

| Extension | Where to add |
|-----------|-------------|
| Semantic Scholar citations | New `src/semantic_scholar.py` fetcher; merge into `run()` in `main.py` |
| Email delivery | New `src/notifier.py`; call after `save_report()` |
| Microsoft Teams webhook | Same `notifier.py`; Teams incoming webhook is one `requests.post` |
| Notion integration | Notion API client in `src/notifier.py`; use paper fields as page properties |
| Additional LLM providers | Extend `summarizer.py` with an `openai` branch |
| More arXiv categories | Add to `arxiv.categories` in `config.yaml` |

---

## Hosted Mode — Web Frontend + Cloudflare Worker + Email Push

In addition to the local Python CLI above, this repo ships a **cloud
deployment** that lets anyone subscribe through a web form and receive a
daily HTML email of ranked arXiv papers — no machine of their own needed.

Real delivery, 2026-05-13 — 5 cs.CV papers ranked and summarized in Chinese
by Claude Haiku 4.5, sent via Resend:

![Daily arXiv email — 2026-05-13](docs/screenshots/daily-email-2026-05-13.png)

```
web/ (static page) ──POST /api/subscribe──▶ backend/ (Cloudflare Worker + D1)
                                                  │
                                                  ▼ cron every minute
                                          fetch arXiv → rank by keywords
                                          → summarize via Claude Haiku
                                          → email via Resend (+ optional
                                            Telegram / Server酱)
```

### Layout

| Path | Purpose |
|------|---------|
| `web/index.html`, `web/app.js` | Static subscription form (Tailwind via CDN). Posts to the Worker. |
| `backend/src/index.js` | Worker entrypoint — HTTP routes + `scheduled()` cron handler |
| `backend/src/routes.js` | `POST /api/subscribe`, `POST /api/unsubscribe`, `GET /api/health` |
| `backend/src/scheduler.js` | Per-minute cron: matches `delivery_time` in each user's `timezone`, dispatches |
| `backend/src/arxiv.js` | arXiv Atom fetch with 3-retry backoff and edge cache |
| `backend/src/ranker.js` | Same keyword-weighted ranking as the Python CLI (title ×3, abstract ×1) |
| `backend/src/summarizer.js` | Claude Haiku 4.5 summary in zh / en (skipped if `summary_lang == none`) |
| `backend/src/push.js` | Email (Resend), Telegram, Server酱 senders |
| `backend/src/render.js` | HTML email layout + Markdown for chat channels |
| `backend/schema.sql` | D1 schema: `subscriptions` + `sends` (per-paper-per-channel dedup) |
| `backend/wrangler.toml` | D1 binding, cron trigger, non-secret vars (`EMAIL_FROM`, `ALLOWED_ORIGIN`) |

### Deploy the Worker

Prereqs: a free Cloudflare account, a [Resend](https://resend.com) account
for the email channel, and Node 18+.

```bash
cd backend
npm install
npx wrangler login
```

Create the D1 database and copy the returned `database_id` into
`wrangler.toml` (`[[d1_databases]]`):

```bash
npx wrangler d1 create daily-paper
npm run db:init           # apply schema.sql to remote D1
```

Set the runtime secrets (these are NOT committed and not in `wrangler.toml`):

```bash
npx wrangler secret put RESEND_API_KEY      # required for email
npx wrangler secret put ANTHROPIC_API_KEY   # optional — enables zh/en summaries
npx wrangler secret put TELEGRAM_BOT_TOKEN  # optional — only if Telegram users subscribe
```

Verify `wrangler.toml` has:

```toml
[triggers]
crons = ["* * * * *"]   # every minute; scheduler filters by delivery_time

[vars]
EMAIL_FROM = "Daily Paper <onboarding@resend.dev>"   # change once you verify a domain in Resend
ALLOWED_ORIGIN = "*"                                  # tighten to your Pages origin in prod
```

Deploy and tail logs:

```bash
npm run deploy
npm run tail
```

### Deploy the Web Frontend

The form is a single static HTML file — host it anywhere (Cloudflare Pages,
GitHub Pages, Netlify). Before deploying, update one line in `web/app.js`:

```js
const API_BASE = 'https://daily-paper-agent.<your-subdomain>.workers.dev';
```

Cloudflare Pages (recommended, same account as the Worker):

```bash
npx wrangler pages deploy web --project-name daily-paper-web
```

For local preview just open `web/index.html` in a browser — the form will
still POST to the deployed Worker.

### How a Daily Email Is Built and Sent

End-to-end flow when a subscriber's `delivery_time` ticks in their `timezone`:

1. **Cron fires** (`* * * * *`) → `scheduled()` in `backend/src/index.js` runs
   `runDailyPush(env)` (`scheduler.js:9`).
2. **Match the minute** — for each row in `subscriptions WHERE active = 1`,
   `isDeliveryMinute()` formats `now` in the subscriber's IANA timezone and
   compares `HH:MM` to `delivery_time`. Non-matching subscriptions skip.
3. **Fetch arXiv** (`arxiv.js`) — last 100 papers across the subscriber's
   `categories`, with edge cache (`cf.cacheTtl: 600`) and retry on 429/5xx.
4. **Freshness + dedup** — keep papers published in the last 36 h
   (`FRESH_WINDOW_HOURS`), drop any `paper_id` already in `sends` for this
   subscription.
5. **Rank** (`ranker.js`) — keyword hits in title score 3, in abstract 1;
   tiebreak by `published`; slice to `top_n`.
6. **Summarize** (`summarizer.js`) — if `summary_lang` is `zh` or `en` and
   `ANTHROPIC_API_KEY` is set, call Claude Haiku 4.5 for a 1–2 sentence
   summary per paper. Falls back to no-summary if the key is missing or the
   call fails.
7. **Render the email** (`render.js → renderEmailHtml`) — inline-styled HTML
   list (one `<li>` per paper with title link, authors, summary, categories).
8. **Send** (`push.js → pushEmail`) — `POST https://api.resend.com/emails`
   with `from = EMAIL_FROM`, `to = sub.email`, subject
   `每日 arXiv · YYYY-MM-DD · N 篇`, body = the rendered HTML. The optional
   Telegram and Server酱 channels go out in parallel from the same loop.
9. **Record dispatch** — one row per `(subscription_id, paper_id, channel)`
   in `sends` with `status = 'ok' | 'fail'` and any error message. The UNIQUE
   index guarantees the same paper never re-sends on the same channel.

### Email Provider Setup (Resend)

1. Create a free Resend account; verify your sending domain (or just use
   the sandbox `onboarding@resend.dev` to test — deliverability is poor).
2. Create an API key with **Sending** scope.
3. `npx wrangler secret put RESEND_API_KEY` in `backend/`.
4. Edit `wrangler.toml` → `EMAIL_FROM = "Daily Paper <noreply@yourdomain>"`
   (must match a verified Resend domain) → `npm run deploy`.

### Local Dev for the Worker

```bash
cd backend
echo 'RESEND_API_KEY = "re_test_..."' > .dev.vars         # git-ignored
echo 'ANTHROPIC_API_KEY = "sk-ant-..."' >> .dev.vars
npm run db:init-local
npm run dev          # http://localhost:8787
```

Trigger the scheduled handler manually:

```bash
curl 'http://localhost:8787/__scheduled?cron=*+*+*+*+*'
```

### Security & Privacy Notes

- Subscribers' emails live only in your Cloudflare D1 database; nothing is
  shared with the Python CLI side or written to this repo.
- `RESEND_API_KEY`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN` are stored as
  Worker secrets (`wrangler secret put`), never in `wrangler.toml` or git.
- `wrangler.toml`'s `database_id` is safe to commit — it is not a credential
  per [Cloudflare docs](https://developers.cloudflare.com/d1/).
- Tighten `ALLOWED_ORIGIN` to your Pages URL before going public.
