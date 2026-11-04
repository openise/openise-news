#!/usr/bin/env python3
"""
はてなブックマーク テクノロジーカテゴリ Top50 取得スクリプト
取得情報: タイトル、URL、タグ
出力: Markdown形式ファイル

`src/content/news/` への書き込みは fetch_ai_news.py だけが行う。このスクリプトの
既定出力先は `constants.MANUAL_OUTPUT_DIR` （content collection の外）。

使い方:
    python3 fetch_hb.py
    python3 fetch_hb.py --limit 30
    python3 fetch_hb.py --output my_output.md
"""

import html
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime
import argparse

from constants import AI_KEYWORDS, JST, MANUAL_OUTPUT_DIR, fetch_url, parse_xml, render_external_link

# -------------------------
# 共通: robots.txt の Crawl-delay: 5 を守るための待機
# -------------------------

CRAWL_DELAY_SECONDS = 5
_last_request_at: float | None = None


def _wait_for_crawl_delay() -> None:
    global _last_request_at
    if _last_request_at is not None:
        elapsed = time.monotonic() - _last_request_at
        if elapsed < CRAWL_DELAY_SECONDS:
            time.sleep(CRAWL_DELAY_SECONDS - elapsed)
    _last_request_at = time.monotonic()


# -------------------------
# RSS フィード取得
# -------------------------

RSS_NAMESPACES = {
    "rdf":     "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss":     "http://purl.org/rss/1.0/",
    "dc":      "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "hatena":  "http://www.hatena.ne.jp/info/xmlns#",
}


def fetch_entries(category: str = "it", limit: int = 50) -> list[dict]:
    """
    はてなブックマーク RSS フィードからエントリーを取得する。
    URL: https://b.hatena.ne.jp/hotentry/{category}.rss
    エラー時は空リストを返す。
    """
    url = f"https://b.hatena.ne.jp/hotentry/{category}.rss"
    print(f"[INFO] フィード取得中 ... {url}")

    _wait_for_crawl_delay()
    raw = fetch_url(url, user_agent="HatenaBookmarkFetcher/1.0", source_label="はてなブックマーク")
    if raw is None:
        return []

    return _parse_rss(raw, limit)


def _parse_rss(xml_bytes: bytes, limit: int) -> list[dict]:
    root = parse_xml(xml_bytes, "はてなブックマーク")
    if root is None:
        return []
    items = root.findall("rss:item", RSS_NAMESPACES)
    entries = []

    for item in items[:limit]:
        def text(tag):
            el = item.find(tag, RSS_NAMESPACES)
            return el.text.strip() if el is not None and el.text else ""

        tags_raw = item.findall("dc:subject", RSS_NAMESPACES)
        tags = [t.text.strip() for t in tags_raw if t.text]

        count_str = text("hatena:bookmarkcount")
        entries.append({
            "title":          text("rss:title") or "(タイトルなし)",
            "url":            text("rss:link"),
            "tags":           tags,
            "date":           text("dc:date"),
            "bookmark_count": int(count_str) if count_str.isdigit() else 0,
        })

    return entries


# -------------------------
# タグ別人気エントリー取得（HTML スクレイピング）
# -------------------------

_ENTRY_BLOCK_RE = re.compile(
    r'<h3 class="entrylist-contents-title">\s*<a href="([^"]+)"\s*title="([^"]+)".*?'
    r'<span class="entrylist-contents-users">\s*<a[^>]*><span>(\d+)</span>',
    re.S,
)


def fetch_hotentry_tag_entries(category: str, tag: str, limit: int = 50) -> list[dict]:
    """
    はてなブックマーク 人気エントリー（カテゴリ × タグ）を取得する。
    URL: https://b.hatena.ne.jp/hotentry/{category}/{tag}
    タグ別ページには RSS が存在しないため HTML をスクレイピングする。
    エラー時は空リストを返す。
    """
    url = f"https://b.hatena.ne.jp/hotentry/{category}/{urllib.parse.quote(tag)}"
    print(f"[INFO] タグ別人気エントリー取得中 ... {url}")

    _wait_for_crawl_delay()
    raw = fetch_url(url, user_agent="HatenaBookmarkFetcher/1.0", source_label="はてなブックマーク")
    if raw is None:
        return []

    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"[WARN] はてなブックマーク: レスポンスの UTF-8 デコード失敗 {e} — スキップします", file=sys.stderr)
        return []

    entries = []
    for entry_url, title, count_str in _ENTRY_BLOCK_RE.findall(body)[:limit]:
        entries.append({
            "title":          html.unescape(title),
            "url":            html.unescape(entry_url),
            "tags":           [],
            "bookmark_count": int(count_str),
        })

    return entries


# -------------------------
# Markdown 出力
# -------------------------

def to_markdown(entries: list[dict], category_label: str, category: str = "it") -> str:
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# はてなブックマーク {category_label} 抽出結果: {len(entries)}件",
        "",
        f"> 取得日時: {now}  ",
        f"> データソース: https://b.hatena.ne.jp/hotentry/{category}.rss",
        "",
        "---",
        "",
        "| # | タイトル | ブックマーク数 |",
        "|---|---|---|",
    ]

    for i, e in enumerate(entries, 1):
        link = render_external_link(e['title'], e['url'])
        lines.append(f"| {i} | {link} | {e['bookmark_count']} |")

    return "\n".join(lines) + "\n"


def save_markdown(content: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[INFO] 保存完了 → {path}")


# -------------------------
# メイン
# -------------------------

def _default_output_path(category: str, limit: int, now: datetime) -> str:
    """--output 省略時のデフォルト出力先を計算する。"""
    filename = f"hatena_{category}_top{limit}_{now.strftime('%Y%m%d_%H%M%S')}.md"
    return os.path.join(MANUAL_OUTPUT_DIR, filename)


def main():
    parser = argparse.ArgumentParser(
        description="はてなブックマーク テクノロジーTop N を Markdown で保存"
    )
    parser.add_argument("--category",      default="it", help="カテゴリ (default: it)")
    parser.add_argument("--limit",   "-n", type=int, default=50,  help="取得件数 (default: 50)")
    parser.add_argument("--output",  "-o", default="",            help="出力ファイルパス (省略時は自動生成)")
    parser.add_argument("--ai-only",        action="store_true",   help="AI 関連キーワードでフィルタリング")
    parser.add_argument("--tags",    "-t", nargs="*", default=[], help="抽出するタグ (複数指定時はOR検索, スペース区切りで指定)")
    args = parser.parse_args()

    if args.output:
        output = args.output
    else:
        output = _default_output_path(args.category, args.limit, datetime.now(JST))
        os.makedirs(os.path.dirname(output), exist_ok=True)

    entries = fetch_entries(category=args.category, limit=args.limit)

    # タグによるフィルタリング (OR検索)
    tags = list(args.tags)
    if args.ai_only:
        tags = AI_KEYWORDS + tags
    if tags:
        search_tags = [t.lower() for t in tags]
        print(f"[INFO] 抽出タグ: {', '.join(tags)}")
        filtered = []
        for e in entries:
            entry_tags = [t.lower() for t in e["tags"]]
            if any(st in entry_tags for st in search_tags):
                filtered.append(e)
        entries = filtered

    print(f"[INFO] {len(entries)} 件取得しました")

    md = to_markdown(entries, category_label="テクノロジー", category=args.category)
    save_markdown(md, output)
    print("[DONE]")


if __name__ == "__main__":
    main()
