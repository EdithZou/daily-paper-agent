"""Keyword-based relevance ranker."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple

from src.db import Paper

# --- scoring weights ----------------------------------------------------------
_TITLE_WEIGHT = 3.0
_ABSTRACT_WEIGHT = 2.0   # raised: abstract mention should count more

# Priority thresholds (out of normalised 0–10 score)
_MUST_READ = 6.0
_WORTH_SKIM = 1.0        # lowered: one keyword in abstract is enough to skim

# Topic phrases (multi-word) score extra because they are very specific
_TOPIC_BONUS = 4.0
_KEYWORD_SCORE = 1.5


@dataclass
class RankResult:
    score: float
    priority: str       # Must Read | Worth Skim | Low Priority
    matched_keywords: list[str]


def _normalize(text: str) -> str:
    return text.lower()


def _count_matches(text: str, pattern: re.Pattern) -> int:
    return len(pattern.findall(text))


def rank_paper(paper: Paper, interests: dict) -> RankResult:
    topics: list[str] = interests.get("topics", [])
    keywords: list[str] = interests.get("keywords", [])

    title_n = _normalize(paper.title)
    abstract_n = _normalize(paper.abstract)
    matched: list[str] = []
    raw_score = 0.0

    # Score multi-word topic phrases
    for topic in topics:
        pattern = re.compile(re.escape(topic.lower()))
        t_hits = _count_matches(title_n, pattern)
        a_hits = _count_matches(abstract_n, pattern)
        if t_hits or a_hits:
            matched.append(topic)
            raw_score += t_hits * _TITLE_WEIGHT * _TOPIC_BONUS
            raw_score += a_hits * _ABSTRACT_WEIGHT * _TOPIC_BONUS

    # Score single keywords (only if not already captured by a topic phrase)
    already = " ".join(matched).lower()
    for kw in keywords:
        if kw.lower() in already:
            continue
        pattern = re.compile(r"\b" + re.escape(kw.lower()) + r"\b")
        t_hits = _count_matches(title_n, pattern)
        a_hits = _count_matches(abstract_n, pattern)
        if t_hits or a_hits:
            matched.append(kw)
            raw_score += t_hits * _TITLE_WEIGHT * _KEYWORD_SCORE
            raw_score += a_hits * _ABSTRACT_WEIGHT * _KEYWORD_SCORE

    # Normalise to 0–10
    score = min(raw_score, 10.0)

    if score >= _MUST_READ:
        priority = "Must Read"
    elif score >= _WORTH_SKIM:
        priority = "Worth Skim"
    else:
        priority = "Low Priority"

    return RankResult(score=round(score, 2), priority=priority, matched_keywords=matched)
