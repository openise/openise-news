#!/usr/bin/env python3
"""
Qiita 人気記事 Atom フィード取得スクリプト
ソース: https://qiita.com/popular-items/feed.atom

使い方:
    python3 fetch_qiita.py
    python3 fetch_qiita.py --limit 10
    python3 fetch_qiita.py --ai-only               # AI 関連トピックのみ抽出
    python3 fetch_qiita.py --keywords AI LLM GPT   # 独自キーワードで抽出
"""

from __future__ import annotations
import xml.etree.ElementTree as ET

from constants import fetch_feed_entries, run_feed_cli

FEED_URL = "https://qiita.com/popular-items/feed.atom"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_atom_entries(root: ET.Element, limit: int = 0) -> list[dict]:
    """Atom フィードの <entry> から title / url を取り出す。limit=0 のとき全件返す。"""
    entries = root.findall("atom:entry", ATOM_NS)

    results = []
    for entry in (entries if limit == 0 else entries[:limit]):
        title_el = entry.find("atom:title", ATOM_NS)
        title = title_el.text.strip() if title_el is not None and title_el.text else "(タイトルなし)"

        # <link rel="alternate" href="...">
        url = ""
        for link_el in entry.findall("atom:link", ATOM_NS):
            if link_el.get("rel", "alternate") == "alternate":
                url = link_el.get("href", "")
                break

        results.append({"title": title, "url": url})

    return results


def fetch_entries(limit: int = 10, keywords: list[str] | None = None) -> list[dict]:
    """Qiita 人気記事フィードからエントリーを取得する。エラー時は空リストを返す。"""
    return fetch_feed_entries(FEED_URL, _parse_atom_entries, "Qiita", limit, keywords)


def main():
    run_feed_cli("Qiita 人気記事フィードから記事を取得して表示", fetch_entries)


if __name__ == "__main__":
    main()
