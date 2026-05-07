"""Fetch recent papers from PubMed (medical / biomedical journals)."""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests

from src.db import Paper

logger = logging.getLogger(__name__)

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_BATCH = 20          # PMIDs per efetch call
_RATE_DELAY = 0.4    # NCBI asks for ≤3 req/s without API key


def _build_query(journals: list[str], topics: list[str], keywords: list[str], days_back: int) -> str:
    journal_q = " OR ".join(f'"{j}"[Journal]' for j in journals)
    kw_terms = topics[:4] + [k for k in keywords if len(k) > 3][:8]
    kw_q = " OR ".join(f'"{t}"[Title/Abstract]' for t in kw_terms)
    since = (date.today() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    date_q = f'("{since}"[Date - Publication] : "3000"[Date - Publication])'
    return f"({journal_q}) AND ({kw_q}) AND {date_q}"


def _parse_abstract(article_el: ET.Element) -> str:
    parts: list[str] = []
    abstract_el = article_el.find("Abstract")
    if abstract_el is not None:
        for node in abstract_el.findall("AbstractText"):
            label = node.get("Label")
            text = (node.text or "").strip()
            if text:
                parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts)


def _parse_date(article_el: ET.Element) -> str:
    # Try electronic publication date first, then journal issue date
    for path in [
        "ArticleDate",
        "Journal/JournalIssue/PubDate",
    ]:
        el = article_el.find(path)
        if el is None:
            continue
        year = (el.findtext("Year") or "").strip()
        month = (el.findtext("Month") or "01").strip().zfill(2)
        day = (el.findtext("Day") or "01").strip().zfill(2)
        # Month might be abbreviated text like "Apr"
        _months = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        }
        month = _months.get(month.lower()[:3], month)
        if year:
            return f"{year}-{month}-{day}"
    return ""


def _parse_article(pubmed_article: ET.Element) -> Paper | None:
    mc = pubmed_article.find("MedlineCitation")
    if mc is None:
        return None

    pmid = (mc.findtext("PMID") or "").strip()
    article = mc.find("Article")
    if article is None:
        return None

    title = (article.findtext("ArticleTitle") or "").strip()
    abstract = _parse_abstract(article)
    if not title or not abstract:
        return None

    authors: list[str] = []
    for auth in (article.find("AuthorList") or []):
        last = (auth.findtext("LastName") or "").strip()
        fore = (auth.findtext("ForeName") or "").strip()
        name = f"{fore} {last}".strip() if fore else last
        if name:
            authors.append(name)

    journal = (
        article.findtext("Journal/Title")
        or article.findtext("Journal/ISOAbbreviation")
        or ""
    ).strip()

    pub_date = _parse_date(article)

    # Collect external IDs
    doi = ""
    for aid in pubmed_article.findall("PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi":
            doi = (aid.text or "").strip()

    link = (
        f"https://doi.org/{doi}" if doi
        else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    )

    return Paper(
        arxiv_id=f"pmid:{pmid}",
        title=title,
        authors=authors,
        abstract=abstract,
        link=link,
        published=pub_date,
        categories=[journal] if journal else [],
    )


def fetch_papers(
    topics: list[str],
    keywords: list[str],
    journals: list[str],
    max_results: int = 30,
    days_back: int = 14,
) -> list[Paper]:
    """Return recent papers from PubMed-indexed journals matching the research interests."""
    if not journals:
        return []

    query = _build_query(journals, topics, keywords, days_back)
    logger.info("PubMed query: %s", query[:120])

    # Step 1: ESearch — get PMIDs
    try:
        resp = requests.get(
            _ESEARCH,
            params={
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "pub date",
            },
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error("PubMed ESearch failed: %s", exc)
        return []

    pmids: list[str] = resp.json().get("esearchresult", {}).get("idlist", [])
    if not pmids:
        logger.info("PubMed returned 0 results")
        return []

    logger.info("PubMed found %d PMIDs", len(pmids))

    # Step 2: EFetch in batches — get full records
    papers: list[Paper] = []
    for i in range(0, len(pmids), _BATCH):
        batch_ids = ",".join(pmids[i : i + _BATCH])
        time.sleep(_RATE_DELAY)
        try:
            resp = requests.get(
                _EFETCH,
                params={
                    "db": "pubmed",
                    "id": batch_ids,
                    "retmode": "xml",
                },
                timeout=30,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("PubMed EFetch failed: %s", exc)
            continue

        root = ET.fromstring(resp.text)
        for article_el in root.findall("PubmedArticle"):
            paper = _parse_article(article_el)
            if paper:
                papers.append(paper)

    logger.info("Fetched %d papers from PubMed", len(papers))
    return papers
