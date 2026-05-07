"""Fetch recent papers from the arXiv API (Atom XML)."""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Optional

import requests

from src.db import Paper

logger = logging.getLogger(__name__)

_ATOM = "http://www.w3.org/2005/Atom"
_ARXIV = "http://arxiv.org/schemas/atom"
_API_BASE = "http://export.arxiv.org/api/query"
_PAGE_SIZE = 100
_RATE_DELAY = 3.0   # seconds between paginated requests (arXiv rate limit)


def _build_query(categories: list[str]) -> str:
    return " OR ".join(f"cat:{c}" for c in categories)


def _parse_entry(entry: ET.Element) -> Optional[Paper]:
    def txt(tag: str, ns: str = _ATOM) -> str:
        el = entry.find(f"{{{ns}}}{tag}")
        return el.text.strip() if el is not None and el.text else ""

    arxiv_id_raw = txt("id")
    # id looks like: http://arxiv.org/abs/2405.12345v1
    arxiv_id = arxiv_id_raw.split("/abs/")[-1].split("v")[0].strip()
    if not arxiv_id:
        return None

    title = txt("title").replace("\n", " ").strip()
    abstract = txt("summary").replace("\n", " ").strip()
    link = f"https://arxiv.org/abs/{arxiv_id}"

    authors = [
        (a.find(f"{{{_ATOM}}}name").text or "").strip()
        for a in entry.findall(f"{{{_ATOM}}}author")
        if a.find(f"{{{_ATOM}}}name") is not None
    ]

    published_raw = txt("published")
    try:
        published = datetime.fromisoformat(
            published_raw.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d")
    except Exception:
        published = published_raw[:10]

    categories = [
        t.get("term", "")
        for t in entry.findall(f"{{{_ATOM}}}category")
    ]

    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        abstract=abstract,
        link=link,
        published=published,
        categories=[c for c in categories if c],
    )


def fetch_papers(
    categories: list[str],
    max_results: int = 100,
    target_date: Optional[date] = None,
) -> list[Paper]:
    """Return up to *max_results* papers from arXiv, sorted by submission date."""
    query = _build_query(categories)
    papers: list[Paper] = []
    start = 0
    batch = min(_PAGE_SIZE, max_results)

    while len(papers) < max_results:
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": start,
            "max_results": batch,
        }
        try:
            logger.info("Fetching arXiv batch start=%d size=%d", start, batch)
            resp = requests.get(_API_BASE, params=params, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("arXiv request failed: %s", exc)
            break

        root = ET.fromstring(resp.text)
        entries = root.findall(f"{{{_ATOM}}}entry")
        if not entries:
            break

        for entry in entries:
            paper = _parse_entry(entry)
            if paper is None:
                continue
            # Optional date filter: keep papers published on target_date
            if target_date and paper.published != str(target_date):
                continue
            papers.append(paper)

        if len(entries) < batch:
            break   # no more results from API

        start += batch
        if len(papers) < max_results and start < max_results * 3:
            time.sleep(_RATE_DELAY)
        else:
            break

    logger.info("Fetched %d papers from arXiv", len(papers))
    return papers[:max_results]
