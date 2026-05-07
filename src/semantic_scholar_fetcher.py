"""Fetch papers from Semantic Scholar API, filtered by venue (conference/journal)."""
from __future__ import annotations

import logging
import os
import time
from datetime import date, timedelta

import requests

from src.db import Paper

logger = logging.getLogger(__name__)

_BASE = "https://api.semanticscholar.org/graph/v1"
_FIELDS = (
    "paperId,title,abstract,authors,year,venue,"
    "externalIds,publicationDate,openAccessPdf,url"
)
_RATE_DELAY = 1.5   # seconds between requests (free tier: ~1 req/s)


def _to_paper(item: dict) -> Paper | None:
    title = (item.get("title") or "").strip()
    abstract = (item.get("abstract") or "").strip()
    if not title or not abstract:
        return None

    # Prefer arXiv ID so the deduplication overlaps with the arXiv fetcher
    ext = item.get("externalIds") or {}
    arxiv_raw = ext.get("ArXiv", "")
    if arxiv_raw:
        uid = arxiv_raw.split("v")[0].strip()
        link = f"https://arxiv.org/abs/{uid}"
    else:
        uid = f"s2:{item.get('paperId', '')}"
        link = (
            (item.get("openAccessPdf") or {}).get("url")
            or item.get("url")
            or f"https://www.semanticscholar.org/paper/{item.get('paperId','')}"
        )

    authors = [
        a.get("name", "") for a in (item.get("authors") or [])
        if a.get("name")
    ]

    pub_date = (item.get("publicationDate") or "")[:10]
    if not pub_date:
        year = item.get("year")
        pub_date = f"{year}-01-01" if year else ""

    venue = (item.get("venue") or "").strip()

    return Paper(
        arxiv_id=uid,
        title=title,
        authors=authors,
        abstract=abstract,
        link=link,
        published=pub_date,
        categories=[venue] if venue else [],
    )


def fetch_papers(
    topics: list[str],
    keywords: list[str],
    venues: list[str],
    max_results: int = 50,
    days_back: int = 60,
) -> list[Paper]:
    """Search Semantic Scholar for recent papers from the given venues."""
    if not venues:
        return []

    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"x-api-key": api_key} if api_key else {}

    # Build query from the most discriminative terms
    query_terms = topics[:4] + [k for k in keywords if len(k) > 4][:6]
    query = " | ".join(query_terms[:8])   # S2 supports | as OR

    since = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    venue_str = ",".join(venues)

    papers: list[Paper] = []
    offset = 0
    batch = min(100, max(max_results, 20))

    while len(papers) < max_results:
        params = {
            "query": query,
            "venue": venue_str,
            "fields": _FIELDS,
            "limit": batch,
            "offset": offset,
            "publicationDateOrYear": f"{since}:",
        }
        try:
            logger.info(
                "Semantic Scholar fetch: offset=%d venues=%s", offset, venue_str
            )
            resp = requests.get(
                f"{_BASE}/paper/search",
                headers=headers,
                params=params,
                timeout=20,
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "10"))
                logger.warning("Semantic Scholar rate-limited; waiting %ds", retry_after)
                time.sleep(retry_after)
                resp = requests.get(
                    f"{_BASE}/paper/search",
                    headers=headers,
                    params=params,
                    timeout=20,
                )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Semantic Scholar request failed: %s", exc)
            break

        data = resp.json()
        items = data.get("data") or []
        if not items:
            break

        for item in items:
            p = _to_paper(item)
            if p:
                papers.append(p)

        total = data.get("total", 0)
        offset += batch
        if offset >= total or offset >= max_results * 3:
            break
        time.sleep(_RATE_DELAY)

    logger.info("Fetched %d papers from Semantic Scholar", len(papers))
    return papers[:max_results]
