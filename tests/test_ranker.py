"""Tests for relevance ranker."""
from src.db import Paper
from src.ranker import rank_paper

_INTERESTS = {
    "topics": [
        "video frame interpolation",
        "video super-resolution",
        "capsule endoscopy",
    ],
    "keywords": [
        "interpolation",
        "super-resolution",
        "upsampling",
        "capsule",
        "endoscopy",
        "ultrasound",
    ],
}


def _paper(title: str, abstract: str = "") -> Paper:
    return Paper(
        arxiv_id="test",
        title=title,
        authors=[],
        abstract=abstract,
        link="",
        published="2024-05-06",
        categories=[],
    )


def test_highly_relevant_paper_is_must_read():
    p = _paper(
        "Video Frame Interpolation via Optical Flow",
        "We propose a method for video frame interpolation using optical flow.",
    )
    result = rank_paper(p, _INTERESTS)
    assert result.priority == "Must Read"
    assert result.score >= 6.0


def test_moderately_relevant_is_worth_skim():
    p = _paper(
        "Efficient Upsampling for Low-Resolution Video",
        "We study upsampling techniques applied to video.",
    )
    result = rank_paper(p, _INTERESTS)
    assert result.priority in ("Worth Skim", "Must Read")
    assert result.score >= 2.5


def test_unrelated_paper_is_low_priority():
    p = _paper(
        "Quantum Computing for Protein Folding",
        "We apply quantum algorithms to predict protein structures.",
    )
    result = rank_paper(p, _INTERESTS)
    assert result.priority == "Low Priority"
    assert result.score < 2.5


def test_matched_keywords_recorded():
    p = _paper(
        "Capsule Endoscopy Super-Resolution",
        "We enhance capsule endoscopy images using super-resolution.",
    )
    result = rank_paper(p, _INTERESTS)
    assert len(result.matched_keywords) > 0


def test_score_bounded_0_to_10():
    # Even a paper hitting every keyword should not exceed 10
    p = _paper(
        "Video Frame Interpolation Super-Resolution Capsule Endoscopy Ultrasound Upsampling",
        "video frame interpolation super-resolution capsule endoscopy ultrasound upsampling " * 5,
    )
    result = rank_paper(p, _INTERESTS)
    assert 0.0 <= result.score <= 10.0
