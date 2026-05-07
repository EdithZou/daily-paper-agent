"""On-demand deep paper analysis CLI.

Usage examples:
  python -m src.analyze --arxiv-id 2405.12345
  python -m src.analyze --arxiv-id 2405.12345 --save
  python -m src.analyze --latest-must-read
  python -m src.analyze --latest-must-read --limit 3 --save
  python -m src.analyze --list
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from src.analyzer import analyze_paper, save_analysis
from src.arxiv_fetcher import fetch_papers
from src.db import Paper, get_paper_by_id, get_recent_papers

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _fetch_from_arxiv(arxiv_id: str) -> Paper | None:
    """Fetch a single paper from arXiv by ID."""
    import requests
    import xml.etree.ElementTree as ET

    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("arXiv fetch failed: %s", exc)
        return None

    _ATOM = "http://www.w3.org/2005/Atom"
    root = ET.fromstring(resp.text)
    entries = root.findall(f"{{{_ATOM}}}entry")
    if not entries:
        return None

    from src.arxiv_fetcher import _parse_entry
    return _parse_entry(entries[0])


def _resolve_paper(arxiv_id: str, db_path: str) -> Paper | None:
    """Look up paper in DB first, fall back to arXiv API."""
    paper = get_paper_by_id(db_path, arxiv_id)
    if paper:
        logger.info("Found %s in local DB", arxiv_id)
        return paper
    logger.info("%s not in DB — fetching from arXiv...", arxiv_id)
    return _fetch_from_arxiv(arxiv_id)


def _print_list(db_path: str, limit: int) -> None:
    papers = get_recent_papers(db_path, limit=limit)
    if not papers:
        print("数据库为空，请先运行 python -m src.main --date today")
        return
    print(f"\n最近 {len(papers)} 篇已推荐论文：\n")
    for p in papers:
        print(f"  [{p.priority:11s}] {p.arxiv_id}  {p.recommendation_date}  {p.title[:60]}")
    print()


def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="深度解读指定论文（需要 ANTHROPIC_API_KEY）"
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--arxiv-id",
        metavar="ID",
        help="解读指定 arXiv ID，如 2405.12345",
    )
    parser.add_argument(
        "--latest-must-read",
        action="store_true",
        help="解读数据库中最近的 Must Read 论文",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出数据库中最近的已推荐论文",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="--latest-must-read / --list 显示/处理的论文数量（默认 1）",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="将分析结果保存到 data/analyses/ 目录",
    )
    args = parser.parse_args()

    config = _load_config(args.config)
    db_path = config.get("output", {}).get("db_path", "data/papers.db")
    analyses_dir = config.get("output", {}).get("analyses_dir", "data/analyses")
    analysis_config = config.get("analysis", {})

    # --list
    if args.list:
        _print_list(db_path, limit=max(args.limit, 20))
        return

    # Collect papers to analyse
    papers: list[Paper] = []

    if args.arxiv_id:
        paper = _resolve_paper(args.arxiv_id, db_path)
        if paper is None:
            print(f"找不到论文：{args.arxiv_id}")
            sys.exit(1)
        papers.append(paper)

    elif args.latest_must_read:
        papers = get_recent_papers(db_path, priority="Must Read", limit=args.limit)
        if not papers:
            print("数据库中没有 Must Read 论文，请先运行推荐流程。")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(0)

    # Analyse each paper
    for paper in papers:
        print(f"\n{'='*70}")
        print(f"解读论文：{paper.title}")
        print(f"arXiv ID：{paper.arxiv_id}  |  {paper.link}")
        print(f"{'='*70}\n")

        try:
            result = analyze_paper(paper, analysis_config)
        except Exception as exc:
            print(f"解读失败：{exc}")
            continue

        print(result)

        if args.save:
            path = save_analysis(result, paper, analyses_dir)
            print(f"\n已保存到：{path}")


if __name__ == "__main__":
    main()
