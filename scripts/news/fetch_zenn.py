#!/usr/bin/env python3
"""
Zenn 最新記事 RSS フィード取得スクリプト
ソース: https://zenn.dev/feed

使い方:
    python3 fetch_zenn.py
    python3 fetch_zenn.py --limit 10
    python3 fetch_zenn.py --ai-only               # AI 関連トピックのみ抽出
    python3 fetch_zenn.py --keywords AI LLM GPT   # 独自キーワードで抽出
"""

from __future__ import annotations

from constants import fetch_feed_entries, parse_rss_items, run_feed_cli

FEED_URL = "https://zenn.dev/feed"


def fetch_entries(limit: int = 10, keywords: list[str] | None = None) -> list[dict]:
    """Zenn RSS フィードからエントリーを取得する。エラー時は空リストを返す。"""
    return fetch_feed_entries(FEED_URL, parse_rss_items, "Zenn", limit, keywords)


def main():
    run_feed_cli("Zenn 最新記事フィードから記事を取得して表示", fetch_entries)


if __name__ == "__main__":
    main()
