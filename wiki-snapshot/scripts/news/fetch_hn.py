#!/usr/bin/env python3
"""
fetch_hn.py - Algolia HN API で Show HN / Ask HN Top 10 (過去24h・人気順) を取得して Markdown で保存

`src/content/news/` への書き込みは fetch_ai_news.py だけが行う。このスクリプトの
既定出力先は `constants.MANUAL_OUTPUT_DIR` （content collection の外）。

使い方:
    python3 fetch_hn.py
    python3 fetch_hn.py --limit 20
    python3 fetch_hn.py --output /path/to/output.md
    python3 fetch_hn.py --ai-only               # AI 関連トピックのみ抽出
    python3 fetch_hn.py --keywords AI LLM GPT   # 独自キーワードで抽出
"""

import json
import os
import sys
from datetime import datetime, timedelta
import argparse

from constants import AI_KEYWORDS, JST, MANUAL_OUTPUT_DIR, USER_AGENT, fetch_url, filter_by_keywords, render_external_link

ALGOLIA_BASE = "https://hn.algolia.com/api/v1/search"
HN_BASE = "https://news.ycombinator.com/item?id="


def fetch_hits(tag: str, since: int, limit: int) -> list[dict]:
    """Algolia HN API から指定タグの記事を取得する。エラー時は空リストを返す。"""
    url = f"{ALGOLIA_BASE}?tags={tag}&numericFilters=created_at_i%3E{since}&hitsPerPage={limit}"
    raw = fetch_url(url, user_agent=USER_AGENT, source_label="Hacker News")
    if raw is None:
        return []

    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"[WARN] Hacker News: response の decode / JSON パース失敗 {e} — スキップします", file=sys.stderr)
        return []

    if not isinstance(data, dict):
        print("[WARN] Hacker News: response の形式が不正です — スキップします", file=sys.stderr)
        return []

    hits = data.get("hits")
    if not isinstance(hits, list) or not all(isinstance(hit, dict) for hit in hits):
        print("[WARN] Hacker News: hits の形式が不正です — スキップします", file=sys.stderr)
        return []

    return hits


def section_md(emoji: str, label: str, hits: list[dict]) -> list[str]:
    lines = [
        f"## {emoji} {label}",
        "",
        "| # | タイトル | Points | Comments |",
        "|---|---------|--------|----------|",
    ]
    for i, h in enumerate(hits, 1):
        title = h.get("title") or "(タイトルなし)"
        url = HN_BASE + h.get("objectID", "")
        link = render_external_link(title, url)
        points = h.get("points") or 0
        comments = h.get("num_comments") or 0
        lines.append(f"| {i} | {link} | {points} | {comments} |")
    return lines


def to_markdown(show_hits: list[dict], ask_hits: list[dict], now: datetime, filter_label: str = "") -> str:
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
    title_suffix = f" [{filter_label}]" if filter_label else ""

    lines = [
        f"# Hacker News Top 10 (過去24h・人気順){title_suffix} - {date_str}",
        f"*取得日時: {datetime_str} JST | Source: [Algolia HN Search](https://hn.algolia.com/)*",
        "",
        *section_md("🚀", "Show HN", show_hits),
        "",
        *section_md("🙋", "Ask HN", ask_hits),
        "",
    ]
    return "\n".join(lines)


def _default_output_path(now: datetime) -> str:
    """--output 省略時のデフォルト出力先を計算する。"""
    filename = f"hn_top_{now.strftime('%Y%m%d_%H%M%S')}.md"
    return os.path.join(MANUAL_OUTPUT_DIR, filename)


def main():
    parser = argparse.ArgumentParser(
        description="Algolia HN API で Show HN / Ask HN Top N を Markdown で保存"
    )
    parser.add_argument("--limit",    "-n", type=int, default=10,  help="取得件数 (default: 10)")
    parser.add_argument("--output",   "-o", default="",            help="出力ファイルパス (省略時は自動生成)")
    parser.add_argument("--ai-only",        action="store_true",   help="AI 関連キーワードでフィルタリング")
    parser.add_argument("--keywords", "-k", nargs="+", default=[], help="独自キーワードでフィルタリング (スペース区切り, --ai-only と併用可)")
    args = parser.parse_args()

    now = datetime.now(JST)
    since = int((now - timedelta(hours=24)).timestamp())

    output = args.output
    if not output:
        output = _default_output_path(now)
        os.makedirs(os.path.dirname(output), exist_ok=True)

    # フィルタリングキーワードを決定
    keywords = list(args.keywords)
    if args.ai_only:
        keywords = AI_KEYWORDS + keywords
    filter_label = "AI" if args.ai_only and not args.keywords else (", ".join(args.keywords) if args.keywords else "")

    print("[INFO] Show HN 取得中 ...")
    show_hits = fetch_hits("show_hn", since, args.limit)
    print("[INFO] Ask HN 取得中 ...")
    ask_hits = fetch_hits("ask_hn", since, args.limit)

    if keywords:
        show_hits = filter_by_keywords(show_hits, keywords)
        ask_hits  = filter_by_keywords(ask_hits,  keywords)
        print(f"[INFO] フィルタ後: Show HN {len(show_hits)}件 / Ask HN {len(ask_hits)}件")

    md = to_markdown(show_hits, ask_hits, now, filter_label=filter_label)
    with open(output, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"✅ 保存完了: {output}")


if __name__ == "__main__":
    main()
