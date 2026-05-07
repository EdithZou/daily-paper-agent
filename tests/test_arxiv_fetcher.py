"""Tests for arXiv XML parser (offline, no network)."""
import textwrap
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest

from src.arxiv_fetcher import _parse_entry, fetch_papers

_ATOM = "http://www.w3.org/2005/Atom"

_SAMPLE_ENTRY_XML = """\
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:arxiv="http://arxiv.org/schemas/atom">
  <id>http://arxiv.org/abs/2405.12345v2</id>
  <title>Video Super-Resolution via Temporal Alignment</title>
  <summary>We propose a novel approach to video super-resolution
using sparse temporal context.</summary>
  <author><name>Alice Smith</name></author>
  <author><name>Bob Jones</name></author>
  <published>2024-05-06T00:00:00Z</published>
  <category term="cs.CV"/>
  <category term="eess.IV"/>
</entry>
"""


def _parse_sample() -> object:
    root = ET.fromstring(_SAMPLE_ENTRY_XML)
    return _parse_entry(root)


def test_arxiv_id_stripped():
    paper = _parse_sample()
    assert paper.arxiv_id == "2405.12345"


def test_title_parsed():
    paper = _parse_sample()
    assert "Video Super-Resolution" in paper.title


def test_authors_parsed():
    paper = _parse_sample()
    assert "Alice Smith" in paper.authors
    assert len(paper.authors) == 2


def test_published_date_format():
    paper = _parse_sample()
    assert paper.published == "2024-05-06"


def test_categories_parsed():
    paper = _parse_sample()
    assert "cs.CV" in paper.categories
    assert "eess.IV" in paper.categories


def test_link_formed_correctly():
    paper = _parse_sample()
    assert paper.link == "https://arxiv.org/abs/2405.12345"


def test_fetch_papers_returns_list_on_http_error():
    """Should return empty list on network failure, not raise."""
    with patch("src.arxiv_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Exception("network error")
        result = fetch_papers(["cs.CV"], max_results=5)
    assert isinstance(result, list)
