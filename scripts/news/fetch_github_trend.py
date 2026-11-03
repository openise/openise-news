#!/usr/bin/env python3
"""
GitHub 公式 daily Trending 取得スクリプト
ソース: https://github.com/trending?since=daily

使い方:
    python3 fetch_github_trend.py
    python3 fetch_github_trend.py --limit 10
    python3 fetch_github_trend.py --ai-only               # AI 関連トピックのみ抽出
    python3 fetch_github_trend.py --keywords AI LLM GPT   # 独自キーワードで抽出
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser

from constants import USER_AGENT, fetch_url, filter_by_keywords, run_feed_cli

TRENDING_URL = "https://github.com/trending?since=daily"


class _TrendingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.entries: list[dict] = []
        self.in_card = False
        self.in_heading = False
        self.in_description = False
        self.repo = ""
        self.description: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "article" and "Box-row" in classes:
            self.in_card = True
            self.in_heading = False
            self.in_description = False
            self.repo = ""
            self.description = []
        if not self.in_card:
            return
        if tag == "h2":
            self.in_heading = True
        elif tag == "a" and self.in_heading:
            href = attributes.get("href") or ""
            if re.fullmatch(r"/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", href):
                self.repo = href[1:]
        elif tag == "p" and "col-9" in classes:
            self.in_description = True

    def handle_endtag(self, tag: str):
        if tag == "h2":
            self.in_heading = False
        elif tag == "p":
            self.in_description = False
        elif tag == "article" and self.in_card:
            if self.repo:
                self.entries.append({
                    "title": self.repo,
                    "url": f"https://github.com/{self.repo}",
                    "description": " ".join("".join(self.description).split()),
                })
            self.in_card = False

    def handle_data(self, data: str):
        if self.in_card and self.in_description:
            self.description.append(data)


def parse_trending_html(html: str) -> list[dict]:
    parser = _TrendingParser()
    parser.feed(html)
    parser.close()
    return parser.entries


def fetch_entries(limit: int = 10, keywords: list[str] | None = None) -> list[dict]:
    """名前と説明文で絞り込み、表示用のリポジトリ名と URL を返す。"""
    print(f"[INFO] GitHub Trending 取得中 ... {TRENDING_URL}")
    raw = fetch_url(TRENDING_URL, user_agent=USER_AGENT, source_label="GitHub Trend")
    if raw is None:
        return []

    entries = parse_trending_html(raw.decode("utf-8"))
    if not entries:
        print("[WARN] GitHub Trend: リポジトリのカードを認識できません — スキップします", file=sys.stderr)
        return []
    if keywords:
        searchable = [
            {"title": f"{entry['title']} {entry['description']}", "entry": entry}
            for entry in entries
        ]
        entries = [match["entry"] for match in filter_by_keywords(searchable, keywords)]
    if limit != 0:
        entries = entries[:limit]
    return [{"title": entry["title"], "url": entry["url"]} for entry in entries]


def main():
    run_feed_cli("GitHub 公式 daily Trending からリポジトリを取得して表示", fetch_entries)


if __name__ == "__main__":
    main()
