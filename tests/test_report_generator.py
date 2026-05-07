"""Tests for Markdown report generation."""
from datetime import date

from src.db import Paper
from src.report_generator import generate_report


def _make_paper(priority: str, score: float = 5.0) -> Paper:
    return Paper(
        arxiv_id="2405.00001",
        title="A Great Paper on Video Super-Resolution",
        authors=["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank"],
        abstract="We study video super-resolution.",
        link="https://arxiv.org/abs/2405.00001",
        published="2024-05-06",
        categories=["cs.CV", "eess.IV"],
        relevance_score=score,
        priority=priority,
        matched_keywords=["video super-resolution", "super-resolution"],
        summary_zh="本文研究视频超分辨率。",
        recommendation_date="2024-05-07",
    )


def test_report_contains_date():
    report = generate_report([], date(2024, 5, 7))
    assert "2024-05-07" in report


def test_report_summary_counts():
    papers = [
        _make_paper("Must Read", 8.0),
        _make_paper("Worth Skim", 4.0),
        _make_paper("Low Priority", 1.0),
    ]
    report = generate_report(papers, date(2024, 5, 7))
    assert "Must Read: **1**" in report
    assert "Worth Skim: **1**" in report
    assert "Low Priority: **1**" in report
    assert "Total new papers: **3**" in report


def test_report_has_paper_title():
    papers = [_make_paper("Must Read", 8.0)]
    report = generate_report(papers, date(2024, 5, 7))
    assert "A Great Paper on Video Super-Resolution" in report


def test_report_has_chinese_summary():
    papers = [_make_paper("Must Read", 8.0)]
    report = generate_report(papers, date(2024, 5, 7))
    assert "本文研究视频超分辨率" in report


def test_report_truncates_long_author_list():
    papers = [_make_paper("Must Read", 8.0)]
    report = generate_report(papers, date(2024, 5, 7))
    assert "et al." in report


def test_dry_run_label_in_report():
    report = generate_report([], date(2024, 5, 7), dry_run=True)
    assert "dry-run" in report


def test_empty_papers_report():
    report = generate_report([], date(2024, 5, 7))
    assert "Total new papers: **0**" in report
