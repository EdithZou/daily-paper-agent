"""Tests for SQLite deduplication."""
import tempfile
import os

import pytest

from src.db import Paper, get_seen_ids, is_duplicate, save_paper


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


def _make_paper(arxiv_id: str = "2405.00001") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title="Test Paper",
        authors=["Alice", "Bob"],
        abstract="This is a test abstract.",
        link=f"https://arxiv.org/abs/{arxiv_id}",
        published="2024-05-06",
        categories=["cs.CV"],
        relevance_score=5.0,
        priority="Worth Skim",
        matched_keywords=["super-resolution"],
        summary_zh="测试摘要",
        recommendation_date="2024-05-07",
    )


def test_new_paper_not_duplicate(tmp_db):
    assert not is_duplicate(tmp_db, "2405.00001")


def test_saved_paper_is_duplicate(tmp_db):
    paper = _make_paper("2405.00001")
    save_paper(tmp_db, paper)
    assert is_duplicate(tmp_db, "2405.00001")


def test_different_id_not_duplicate(tmp_db):
    paper = _make_paper("2405.00001")
    save_paper(tmp_db, paper)
    assert not is_duplicate(tmp_db, "2405.00002")


def test_get_seen_ids_empty(tmp_db):
    assert get_seen_ids(tmp_db) == set()


def test_get_seen_ids_after_save(tmp_db):
    for i in range(3):
        save_paper(tmp_db, _make_paper(f"2405.0000{i}"))
    seen = get_seen_ids(tmp_db)
    assert seen == {"2405.00000", "2405.00001", "2405.00002"}


def test_insert_or_ignore_does_not_raise(tmp_db):
    paper = _make_paper("2405.00001")
    save_paper(tmp_db, paper)
    save_paper(tmp_db, paper)   # should not raise
    assert len(get_seen_ids(tmp_db)) == 1
