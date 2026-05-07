"""Entry point: python -m src.main [options]"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

from src.analyzer import analyze_paper
from src.arxiv_fetcher import fetch_papers as arxiv_fetch
from src import semantic_scholar_fetcher as s2
from src import pubmed_fetcher as pubmed
from src.db import Paper, get_seen_ids, is_duplicate, save_paper
from src.ranker import rank_paper
from src.report_generator import generate_report, save_report
from src.summarizer import summarize

# Priority order for threshold filtering (highest first)
_PRIORITY_ORDER = ["Must Read", "Worth Skim", "Low Priority"]


def _setup_logging(log_path: str) -> None:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(log_path))
    except OSError:
        pass
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _parse_date(val: str) -> date:
    if val == "today":
        return date.today()
    return datetime.strptime(val, "%Y-%m-%d").date()


def run(config: dict, target_date: date, dry_run: bool, top_n: int = 0) -> str:
    logger = logging.getLogger("main")
    arxiv_cfg = config.get("arxiv", {})
    s2_cfg = config.get("semantic_scholar", {})
    pubmed_cfg = config.get("pubmed", {})
    interests = config.get("research_interests", {})
    llm_cfg = config.get("llm", {"provider": "none"})
    output_cfg = config.get("output", {})

    db_path = output_cfg.get("db_path", "data/papers.db")
    reports_dir = output_cfg.get("reports_dir", "data/reports")

    topics = interests.get("topics", [])
    keywords = interests.get("keywords", [])

    # ── arXiv ──────────────────────────────────────────────────────────────
    categories = arxiv_cfg.get("categories", ["cs.CV", "eess.IV", "cs.AI"])
    max_results = arxiv_cfg.get("max_results", 100)
    logger.info("Fetching from arXiv...")
    raw_papers: list[Paper] = arxiv_fetch(categories, max_results=max_results)

    # ── Semantic Scholar ────────────────────────────────────────────────────
    if s2_cfg.get("enabled", False):
        venues = s2_cfg.get("venues", [])
        s2_papers = s2.fetch_papers(
            topics=topics,
            keywords=keywords,
            venues=venues,
            max_results=s2_cfg.get("max_results", 50),
            days_back=s2_cfg.get("days_back", 60),
        )
        raw_papers.extend(s2_papers)

    # ── PubMed ─────────────────────────────────────────────────────────────
    if pubmed_cfg.get("enabled", False):
        pm_papers = pubmed.fetch_papers(
            topics=topics,
            keywords=keywords,
            journals=pubmed_cfg.get("journals", []),
            max_results=pubmed_cfg.get("max_results", 30),
            days_back=pubmed_cfg.get("days_back", 14),
        )
        raw_papers.extend(pm_papers)

    # Deduplicate within this batch (same paper from multiple sources)
    seen_in_batch: set[str] = set()
    deduped: list[Paper] = []
    for p in raw_papers:
        if p.arxiv_id not in seen_in_batch:
            seen_in_batch.add(p.arxiv_id)
            deduped.append(p)
    raw_papers = deduped
    logger.info("Total raw papers across all sources: %d", len(raw_papers))

    seen_ids = get_seen_ids(db_path)
    logger.info("Known papers in DB: %d", len(seen_ids))

    new_papers: list[Paper] = []
    for paper in raw_papers:
        if paper.arxiv_id in seen_ids:
            logger.debug("Skip duplicate: %s", paper.arxiv_id)
            continue
        new_papers.append(paper)

    logger.info("New papers after deduplication: %d", len(new_papers))

    ranked: list[Paper] = []
    for paper in new_papers:
        result = rank_paper(paper, interests)
        paper.relevance_score = result.score
        paper.priority = result.priority
        paper.matched_keywords = result.matched_keywords
        ranked.append(paper)

    ranked.sort(key=lambda p: p.relevance_score, reverse=True)
    if top_n > 0:
        ranked = ranked[:top_n]
        logger.info("Kept top %d papers by relevance score", top_n)

    for paper in ranked:
        paper.summary_zh = summarize(paper, llm_cfg)
        paper.recommendation_date = str(target_date)

    # Deep analysis (optional — controlled by analysis.run_in_daily in config)
    analysis_cfg = config.get("analysis", {})
    if analysis_cfg.get("run_in_daily", False):
        min_priority = analysis_cfg.get("min_priority", "Must Read")
        threshold_idx = _PRIORITY_ORDER.index(min_priority) if min_priority in _PRIORITY_ORDER else 0
        to_analyse = [p for p in ranked if _PRIORITY_ORDER.index(p.priority) <= threshold_idx]
        logger.info(
            "Deep analysis enabled (min_priority=%s): analysing %d paper(s)",
            min_priority, len(to_analyse),
        )
        for paper in to_analyse:
            try:
                paper.deep_analysis = analyze_paper(paper, analysis_cfg)
                logger.info("Analysed: %s", paper.arxiv_id)
            except Exception as exc:
                logger.warning("Deep analysis failed for %s: %s", paper.arxiv_id, exc)

    if not dry_run:
        for paper in ranked:
            save_paper(db_path, paper)
        logger.info("Saved %d papers to DB", len(ranked))

    report_content = generate_report(ranked, target_date, dry_run=dry_run)

    if not dry_run:
        out_path = save_report(report_content, reports_dir, target_date)
        logger.info("Report saved: %s", out_path)
    else:
        logger.info("Dry-run mode — report not saved")

    return report_content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily academic paper recommendation agent"
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--date", default="today", help="Target date: 'today' or YYYY-MM-DD"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and rank papers but do not write to DB or disk",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=0,
        metavar="N",
        help="Only keep the top N papers by relevance score (0 = no limit)",
    )
    args = parser.parse_args()

    config = _load_config(args.config)
    log_path = config.get("output", {}).get("log_path", "logs/daily.log")
    _setup_logging(log_path)

    target_date = _parse_date(args.date)
    report = run(config, target_date, dry_run=args.dry_run, top_n=args.top_n)
    print(report)


if __name__ == "__main__":
    main()
