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
