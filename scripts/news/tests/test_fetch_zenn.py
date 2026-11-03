#!/usr/bin/env python3
"""fetch_zenn.py の fetch_entries() テスト"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch_zenn

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Zenn</title>
    <item>
      <title>Claude Code Tips</title>
      <link>https://zenn.dev/example/articles/1</link>
    </item>
    <item>
      <title>Astro 入門</title>
      <link>https://zenn.dev/example/articles/2</link>
    </item>
    <item>
      <title>Docker Compose 活用術</title>
      <link>https://zenn.dev/example/articles/3</link>
    </item>
  </channel>
</rss>
"""

EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Zenn</title>
  </channel>
</rss>
"""


def _mock_response(body: str):
    """urlopen のコンテキストマネージャ応答を模したモックを返す。"""
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_fetch_entries_returns_all_entries_with_title_and_url():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(RSS_FEED)):
        entries = fetch_zenn.fetch_entries(limit=0)

    assert entries == [
        {"title": "Claude Code Tips", "url": "https://zenn.dev/example/articles/1"},
        {"title": "Astro 入門", "url": "https://zenn.dev/example/articles/2"},
        {"title": "Docker Compose 活用術", "url": "https://zenn.dev/example/articles/3"},
    ]


def test_fetch_entries_respects_limit():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(RSS_FEED)):
        entries = fetch_zenn.fetch_entries(limit=2)

    assert len(entries) == 2
    assert [e["title"] for e in entries] == [
        "Claude Code Tips",
        "Astro 入門",
    ]


def test_fetch_entries_filters_by_keywords():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(RSS_FEED)):
        entries = fetch_zenn.fetch_entries(limit=10, keywords=["astro"])

    assert [e["title"] for e in entries] == ["Astro 入門"]


def test_fetch_entries_returns_empty_list_for_empty_feed():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(EMPTY_FEED)):
        entries = fetch_zenn.fetch_entries(limit=0)

    assert entries == []
