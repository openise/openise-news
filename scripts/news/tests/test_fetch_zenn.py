#!/usr/bin/env python3
"""fetch_zenn.py の fetch_entries() テスト"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch_zenn


def _article(title, path, liked_count):
    return {"title": title, "path": path, "liked_count": liked_count, "article_type": "tech"}


API_RESPONSE = json.dumps({
    "articles": [
        _article("Docker Compose 活用術", "/example/articles/1", 10),
        _article("Claude Code Tips", "/example/articles/2", 300),
        _article("Astro 入門", "/example/articles/3", 50),
    ],
    "next_page": 2,
})


def _mock_response(body: str | bytes):
    """urlopen のコンテキストマネージャ応答を模したモックを返す。"""
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8") if isinstance(body, str) else body
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def _fetch(body, **kwargs):
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(body)) as urlopen:
        entries = fetch_zenn.fetch_entries(**kwargs)
    return entries, urlopen


def test_fetch_entries_requests_daily_ranking_api():
    _, urlopen = _fetch(API_RESPONSE, limit=0)

    assert urlopen.call_args.args[0].full_url == "https://zenn.dev/api/articles?order=daily"


def test_fetch_entries_returns_title_url_and_likes_ordered_by_likes():
    entries, _ = _fetch(API_RESPONSE, limit=0)

    assert entries == [
        {"title": "Claude Code Tips", "url": "https://zenn.dev/example/articles/2", "liked_count": 300},
        {"title": "Astro 入門", "url": "https://zenn.dev/example/articles/3", "liked_count": 50},
        {"title": "Docker Compose 活用術", "url": "https://zenn.dev/example/articles/1", "liked_count": 10},
    ]


def test_fetch_entries_keeps_api_order_for_same_likes():
    body = json.dumps({"articles": [_article("B", "/x/articles/b", 5), _article("A", "/x/articles/a", 5)]})

    entries, _ = _fetch(body, limit=0)

    assert [e["title"] for e in entries] == ["B", "A"]


def test_fetch_entries_respects_limit_after_sorting():
    entries, _ = _fetch(API_RESPONSE, limit=2)

    assert [e["title"] for e in entries] == ["Claude Code Tips", "Astro 入門"]


def test_fetch_entries_filters_by_keywords():
    entries, _ = _fetch(API_RESPONSE, limit=10, keywords=["astro", "docker"])

    assert [e["title"] for e in entries] == ["Astro 入門", "Docker Compose 活用術"]


def test_fetch_entries_skips_malformed_articles():
    body = json.dumps({"articles": [
        "not a dict",
        _article("path なし", None, 1),
        _article("相対 path", "example/articles/x", 1),
        _article("いいね数が文字列", "/x/articles/str", "1"),
        _article("いいね数が bool", "/x/articles/bool", True),
        _article(None, "/x/articles/notitle", 2),
        _article("正常", "/x/articles/ok", 1),
    ]})

    entries, _ = _fetch(body, limit=0)

    assert entries == [
        {"title": "(タイトルなし)", "url": "https://zenn.dev/x/articles/notitle", "liked_count": 2},
        {"title": "正常", "url": "https://zenn.dev/x/articles/ok", "liked_count": 1},
    ]


def test_fetch_entries_returns_empty_list_for_invalid_json(capsys):
    entries, _ = _fetch(b"\xff not json", limit=0)

    assert entries == []
    assert "[WARN] Zenn" in capsys.readouterr().err


def test_fetch_entries_returns_empty_list_for_unexpected_shape(capsys):
    for body in ['[]', '{"articles": {}}', '{}']:
        entries, _ = _fetch(body, limit=0)
        assert entries == []
    assert "[WARN] Zenn: articles の形式が不正です" in capsys.readouterr().err


def test_fetch_entries_returns_empty_list_when_request_fails():
    with patch("fetch_zenn.fetch_url", return_value=None):
        assert fetch_zenn.fetch_entries(limit=0) == []
