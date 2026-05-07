"""SQLite persistence — deduplication and paper history."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    link: str
    published: str          # ISO date string, e.g. "2024-05-06"
    categories: list[str]
    relevance_score: float = 0.0
    priority: str = ""      # Must Read | Worth Skim | Low Priority
    matched_keywords: list[str] = field(default_factory=list)
    summary_zh: str = ""
    deep_analysis: str = ""
    recommendation_date: str = ""


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id          TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    authors           TEXT NOT NULL,
    abstract          TEXT NOT NULL,
    link              TEXT NOT NULL,
    published         TEXT NOT NULL,
    categories        TEXT NOT NULL,
    relevance_score   REAL NOT NULL DEFAULT 0,
    priority          TEXT NOT NULL DEFAULT '',
    matched_keywords  TEXT NOT NULL DEFAULT '',
    summary_zh        TEXT NOT NULL DEFAULT '',
    deep_analysis     TEXT NOT NULL DEFAULT '',
    recommendation_date TEXT NOT NULL
);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE)
    # Migrate existing DBs that predate the deep_analysis column
    try:
        conn.execute("ALTER TABLE papers ADD COLUMN deep_analysis TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    return conn


def is_duplicate(db_path: str, arxiv_id: str) -> bool:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
        return row is not None


def save_paper(db_path: str, paper: Paper) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO papers
              (arxiv_id, title, authors, abstract, link, published,
               categories, relevance_score, priority, matched_keywords,
               summary_zh, deep_analysis, recommendation_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paper.arxiv_id,
                paper.title,
                "|".join(paper.authors),
                paper.abstract,
                paper.link,
                paper.published,
                "|".join(paper.categories),
                paper.relevance_score,
                paper.priority,
                "|".join(paper.matched_keywords),
                paper.summary_zh,
                paper.deep_analysis,
                paper.recommendation_date,
            ),
        )
        conn.commit()


def get_seen_ids(db_path: str) -> set[str]:
    try:
        with _connect(db_path) as conn:
            rows = conn.execute("SELECT arxiv_id FROM papers").fetchall()
            return {r["arxiv_id"] for r in rows}
    except Exception:
        return set()


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        arxiv_id=row["arxiv_id"],
        title=row["title"],
        authors=row["authors"].split("|") if row["authors"] else [],
        abstract=row["abstract"],
        link=row["link"],
        published=row["published"],
        categories=row["categories"].split("|") if row["categories"] else [],
        relevance_score=row["relevance_score"],
        priority=row["priority"],
        matched_keywords=row["matched_keywords"].split("|") if row["matched_keywords"] else [],
        summary_zh=row["summary_zh"],
        deep_analysis=row["deep_analysis"] if row["deep_analysis"] else "",
        recommendation_date=row["recommendation_date"],
    )


def get_paper_by_id(db_path: str, arxiv_id: str) -> Optional[Paper]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
        return _row_to_paper(row) if row else None


def get_recent_papers(
    db_path: str,
    priority: Optional[str] = None,
    limit: int = 20,
) -> list[Paper]:
    """Return recently recommended papers, optionally filtered by priority."""
    with _connect(db_path) as conn:
        if priority:
            rows = conn.execute(
                "SELECT * FROM papers WHERE priority = ? "
                "ORDER BY recommendation_date DESC, relevance_score DESC LIMIT ?",
                (priority, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM papers "
                "ORDER BY recommendation_date DESC, relevance_score DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_paper(r) for r in rows]
