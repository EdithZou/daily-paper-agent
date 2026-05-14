CREATE TABLE IF NOT EXISTS subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  telegram_chat_id TEXT,
  serverchan_key TEXT,
  categories TEXT NOT NULL,
  keywords TEXT,
  delivery_time TEXT NOT NULL,
  timezone TEXT NOT NULL,
  top_n INTEGER NOT NULL,
  summary_lang TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sends (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subscription_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  error TEXT,
  sent_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(subscription_id, paper_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_sends_sub ON sends(subscription_id);
CREATE INDEX IF NOT EXISTS idx_sends_paper ON sends(paper_id);
