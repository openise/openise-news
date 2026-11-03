#!/usr/bin/env python3
"""fetch_qiita.py の fetch_entries() テスト"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch_qiita

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Claude Code の使い方まとめ</title>
    <link rel="alternate" href="https://qiita.com/example/items/1"/>
  </entry>
  <entry>
    <title>Python 入門</title>
    <link rel="alternate" href="https://qiita.com/example/items/2"/>
  </entry>
  <entry>
    <title>Rust で Web サーバー構築</title>
    <link rel="alternate" href="https://qiita.com/example/items/3"/>
  </entry>
</feed>
"""

EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>
"""


def _mock_response(body: str):
    """urlopen のコンテキストマネージャ応答を模したモックを返す。"""
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_fetch_entries_returns_all_entries_with_title_and_url():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(ATOM_FEED)):
        entries = fetch_qiita.fetch_entries(limit=0)

    assert entries == [
        {"title": "Claude Code の使い方まとめ", "url": "https://qiita.com/example/items/1"},
        {"title": "Python 入門", "url": "https://qiita.com/example/items/2"},
        {"title": "Rust で Web サーバー構築", "url": "https://qiita.com/example/items/3"},
    ]


def test_fetch_entries_respects_limit():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(ATOM_FEED)):
        entries = fetch_qiita.fetch_entries(limit=2)

    assert len(entries) == 2
    assert [e["title"] for e in entries] == [
        "Claude Code の使い方まとめ",
        "Python 入門",
    ]


def test_fetch_entries_filters_by_keywords():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(ATOM_FEED)):
        entries = fetch_qiita.fetch_entries(limit=10, keywords=["rust"])

    assert [e["title"] for e in entries] == ["Rust で Web サーバー構築"]


def test_fetch_entries_returns_empty_list_for_empty_feed():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(EMPTY_FEED)):
        entries = fetch_qiita.fetch_entries(limit=0)

    assert entries == []
