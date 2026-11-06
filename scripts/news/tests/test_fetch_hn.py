#!/usr/bin/env python3
"""fetch_hn.py の fetch_hits() / section_md() テスト"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch_hn


# -------------------------
# fetch_hits
# -------------------------

def test_fetch_hits_builds_algolia_query_url_from_tag_since_and_limit():
    with patch("fetch_hn.fetch_url", return_value=b'{"hits": []}') as mock_fetch:
        fetch_hn.fetch_hits("show_hn", since=1700000000, limit=25)

    url = mock_fetch.call_args.args[0]
    assert url == (
        "https://hn.algolia.com/api/v1/search"
        "?tags=show_hn&numericFilters=created_at_i%3E1700000000&hitsPerPage=25"
    )


def test_fetch_hits_returns_hits_from_response():
    hits = [{"title": "Show HN: My AI tool", "objectID": "123"}]
    payload = json.dumps({"hits": hits}).encode("utf-8")

    with patch("fetch_hn.fetch_url", return_value=payload):
        result = fetch_hn.fetch_hits("show_hn", since=0, limit=10)

    assert result == hits


@pytest.mark.parametrize("invalid", [
    None, 42,
    {"title": 42}, {"title": []},
    {"objectID": 123}, {"objectID": None},
    {"points": "42"}, {"points": []}, {"points": True}, {"points": 1.5},
    {"num_comments": "7"}, {"num_comments": {}}, {"num_comments": False},
])
def test_fetch_hits_skips_invalid_articles_and_keeps_valid_ones(invalid, capsys):
    valid = {"title": "Show HN: AI tool", "objectID": "123", "points": 42, "num_comments": 7}
    payload = json.dumps({"hits": [invalid, valid]}).encode()
    with patch("fetch_hn.fetch_url", return_value=payload):
        assert fetch_hn.fetch_hits_or_none("show_hn", since=0, limit=10) == [valid]
    assert "[WARN] Hacker News: 記事の形式が不正" in capsys.readouterr().err


def test_fetch_hits_preserves_missing_fields_and_nullable_title_and_counts():
    hits = [{}, {"title": None, "objectID": "123", "points": None, "num_comments": None}]
    with patch("fetch_hn.fetch_url", return_value=json.dumps({"hits": hits}).encode()):
        result = fetch_hn.fetch_hits_or_none("show_hn", since=0, limit=10)
    assert result == hits
    assert fetch_hn.section_md("🙋", "Ask HN", result)[-1].endswith("| 0 | 0 |")


def test_fetch_hits_sends_the_shared_user_agent(monkeypatch):
    monkeypatch.setattr(fetch_hn, "USER_AGENT", "TestAgent/9.9")

    with patch("fetch_hn.fetch_url", return_value=b'{"hits": []}') as mock_fetch:
        fetch_hn.fetch_hits("show_hn", since=0, limit=10)

    assert mock_fetch.call_args.kwargs["user_agent"] == "TestAgent/9.9"


def test_fetch_hits_returns_empty_list_when_fetch_fails():
    with patch("fetch_hn.fetch_url", return_value=None):
        assert fetch_hn.fetch_hits("ask_hn", since=0, limit=10) == []


def test_fetch_hits_returns_empty_list_on_malformed_json(capsys):
    with patch("fetch_hn.fetch_url", return_value=b"not-json"):
        result = fetch_hn.fetch_hits("show_hn", since=0, limit=10)

    assert result == []
    stderr = capsys.readouterr().err
    assert "[WARN] Hacker News" in stderr
    assert "JSON パース失敗" in stderr


def test_fetch_hits_returns_empty_list_and_warns_on_invalid_encoding(capsys):
    with patch("fetch_hn.fetch_url", return_value=b"\xff"):
        result = fetch_hn.fetch_hits("show_hn", since=0, limit=10)

    assert result == []
    assert "[WARN] Hacker News" in capsys.readouterr().err


@pytest.mark.parametrize(
    "payload",
    [
        b"[]",
        b"null",
        b'{"hits": null}',
        b'{"hits": {}}',
        b'{"hits": [null]}',
        b'{"hits": [42]}',
        b"{}",
    ],
)
def test_fetch_hits_handles_invalid_response_shapes_and_elements(payload, capsys):
    with patch("fetch_hn.fetch_url", return_value=payload):
        result = fetch_hn.fetch_hits("show_hn", since=0, limit=10)

    assert result == []
    assert "[WARN] Hacker News" in capsys.readouterr().err


# -------------------------
# section_md
# -------------------------

def test_section_md_renders_table_with_link_points_and_comments():
    hits = [{"title": "Show HN: My AI tool", "objectID": "123", "points": 42, "num_comments": 7}]

    lines = fetch_hn.section_md("🚀", "Show HN", hits)

    assert lines == [
        "## 🚀 Show HN",
        "",
        "| # | タイトル | Points | Comments |",
        "|---|---------|--------|----------|",
        "| 1 | [Show HN: My AI tool](https://news.ycombinator.com/item?id=123) | 42 | 7 |",
    ]


def test_section_md_falls_back_when_title_and_counts_are_missing():
    lines = fetch_hn.section_md("🙋", "Ask HN", [{"objectID": "1"}])

    # 括弧は Markdown エスケープされる（render_external_link の仕様）
    assert lines[-1] == "| 1 | [\\(タイトルなし\\)](https://news.ycombinator.com/item?id=1) | 0 | 0 |"


def test_section_md_escapes_script_in_title():
    hits = [{"title": "<script>alert(1)</script>", "objectID": "9"}]

    lines = fetch_hn.section_md("🚀", "Show HN", hits)

    assert "<script>" not in lines[-1]
    assert "&lt;script&gt;" in lines[-1]


def test_section_md_renders_header_only_for_empty_hits():
    lines = fetch_hn.section_md("🚀", "Show HN", [])

    assert lines == [
        "## 🚀 Show HN",
        "",
        "| # | タイトル | Points | Comments |",
        "|---|---------|--------|----------|",
    ]
