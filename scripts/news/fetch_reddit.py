#!/usr/bin/env python3
"""
Reddit サブレディット Top N 取得スクリプト
取得情報: タイトル、URL（RSS フィード経由）
出力: Markdown 形式ファイル（サブレディットごとにセクション分割）

`src/content/news/` への書き込みは fetch_ai_news.py だけが行う。このスクリプトの
既定出力先は `constants.MANUAL_OUTPUT_DIR` （content collection の外）。

使い方:
    python3 fetch_reddit.py                          # r/ClaudeCode のみ
    python3 fetch_reddit.py --ai                     # AI 関連サブレディット一括
    python3 fetch_reddit.py -s LocalLLaMA ChatGPT   # 個別指定（複数可）
    python3 fetch_reddit.py --ai --period week
    python3 fetch_reddit.py --output my_output.md
"""

import os
import re
from collections.abc import Callable
import urllib.parse
from datetime import datetime
import argparse
import xml.etree.ElementTree as ET

from constants import JST, MANUAL_OUTPUT_DIR, USER_AGENT, fetch_url, parse_xml, render_external_link

REDDIT_BASE = "https://www.reddit.com"
ATOM_NS = "http://www.w3.org/2005/Atom"

AI_SUBREDDITS = [
    "ClaudeCode",
    "LocalLLaMA",
    "ChatGPTCoding",
]

# 画像・動画・ギャラリーだけの投稿のリンク先。本文も外部記事も無く、ミームや
# スクリーンショットが大半で技術的な話題にならないため除く
MEDIA_HOSTS = ("i.redd.it", "v.redd.it", "preview.redd.it", "imgur.com")
# Atom entry の content（HTML）にある、投稿のリンク先を指す "[link]" のアンカー
_CONTENT_LINK_RE = re.compile(r'<a href="([^"]+)">\[link\]</a>')

PERIOD_LABEL = {
    "day": "過去24時間", "week": "過去1週間",
    "month": "過去1ヶ月", "year": "過去1年", "all": "全期間",
}


def _parse_entry(entry: ET.Element) -> dict:
    """Atom entry の title と URL を取り出し、空 title は表示用の値に置き換える。"""
    title_el = entry.find(f"{{{ATOM_NS}}}title")
    link_el = entry.find(f"{{{ATOM_NS}}}link")
    title = (title_el.text or "").strip() if title_el is not None else ""
    return {
        "title": title or "(タイトルなし)",
        "url": link_el.attrib.get("href", "") if link_el is not None else "",
    }


def _is_media_entry(entry: ET.Element) -> bool:
    """投稿のリンク先が画像・動画・ギャラリーなら True を返す。"""
    content_el = entry.find(f"{{{ATOM_NS}}}content")
    match = _CONTENT_LINK_RE.search(content_el.text or "") if content_el is not None else None
    if match is None:
        return False
    parsed = urllib.parse.urlparse(match.group(1))
    host = (parsed.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in MEDIA_HOSTS):
        return True
    return (host == "reddit.com" or host.endswith(".reddit.com")) and parsed.path.startswith("/gallery/")


def fetch_top_posts(subreddit: str, limit: int, period: str) -> list[dict]:
    """Reddit RSS フィードでサブレディットの Top N を取得する。エラー時は空リストを返す。"""
    url = f"{REDDIT_BASE}/r/{subreddit}/top.rss?t={period}&limit={limit}"
    print(f"[INFO] 取得中 ... r/{subreddit}")

    raw = fetch_url(url, user_agent=USER_AGENT, source_label=f"r/{subreddit}")
    if raw is None:
        return []

    ns = {"atom": ATOM_NS}
    root = parse_xml(raw, f"r/{subreddit}")
    if root is None:
        return []
    return [_parse_entry(entry) for entry in root.findall("atom:entry", ns)[:limit]]


# 統合 URL の応答は subreddit 別ソートではなく、全 subreddit 横断のスコア順になる
# （Reddit 仕様）。ある subreddit だけ投稿数・スコアが高いと、他の subreddit の記事が
# 上位 limit 件に入らず 0 件になりうる。`limit` パラメータの上限は明文化されていない
# が、100 件のリクエストで安定して成功する実績があるため固定で採用し、
# `limit * len(subreddits)` を超えて偏りに強くする（厳密な subreddit 別 top N は
# 保証しない。トレードオフとして 429 回避を優先する）。
REDDIT_MULTI_FETCH_SIZE = 100


def fetch_top_posts_ranked(
    subreddits: list[str], limit: int, period: str, exclude: Callable[[dict], bool] | None = None,
) -> list[tuple[str, dict]]:
    """複数 subreddit を 1 HTTP リクエストに統合して取得し、(subreddit, 投稿) を応答の順に返す。

    Reddit は 2026年6月に匿名 RSS アクセスを IP あたり約 1 QPM まで絞る仕様変更を
    行い、subreddit ごとに逐次リクエストすると 1 件目以外が HTTP 429 になる
    （issue #0113 で実測）。`r/{sub1}+{sub2}+...` の統合 URL であれば 1 リクエスト
    で済むため、この制限を回避できる。エラー時は空リストを返す。

    応答は全 subreddit 横断のスコア順。各 subreddit から最大 limit 件を返す。
    画像・動画・ギャラリーだけの投稿と、先に出たものと同じタイトルの投稿（クロスポスト）
    は除き、空いた枠は同じ subreddit の次の投稿で埋める。応答はスコア順なので、
    同じタイトルでは最もスコアの高い投稿が残る。exclude が True を返す投稿も同じように除く。
    """
    combined = "+".join(subreddits)
    fetch_size = max(limit * len(subreddits), REDDIT_MULTI_FETCH_SIZE)
    url = f"{REDDIT_BASE}/r/{combined}/top.rss?t={period}&limit={fetch_size}"
    print(f"[INFO] 取得中 ... r/{combined}")

    raw = fetch_url(url, user_agent=USER_AGENT, source_label=f"r/{combined}")
    if raw is None:
        return []

    ns = {"atom": ATOM_NS}
    root = parse_xml(raw, f"r/{combined}")
    if root is None:
        return []

    counts = {sub: 0 for sub in subreddits}
    ranked: list[tuple[str, dict]] = []
    seen_titles: set[str] = set()
    for entry in root.findall("atom:entry", ns):
        category_el = entry.find("atom:category", ns)
        subreddit = category_el.attrib.get("term", "") if category_el is not None else ""
        if subreddit not in counts or counts[subreddit] >= limit:
            continue
        if _is_media_entry(entry):
            continue
        post = _parse_entry(entry)
        if exclude is not None and exclude(post):
            continue
        if post["title"] in seen_titles:
            continue
        seen_titles.add(post["title"])
        counts[subreddit] += 1
        ranked.append((subreddit, post))
    return ranked


def fetch_top_posts_multi(subreddits: list[str], limit: int, period: str) -> dict[str, list[dict]]:
    """fetch_top_posts_ranked の結果を subreddit ごとにまとめる。エラー時は全 subreddit が空リストになる。"""
    results: dict[str, list[dict]] = {sub: [] for sub in subreddits}
    for subreddit, post in fetch_top_posts_ranked(subreddits, limit, period):
        results[subreddit].append(post)
    return results


def section_md(subreddit: str, posts: list[dict]) -> list[str]:
    lines = [
        f"## r/{subreddit}",
        "",
        "| # | タイトル |",
        "|---|---|",
    ]
    if posts:
        for i, p in enumerate(posts, 1):
            link = render_external_link(p["title"], p["url"])
            lines.append(f"| {i} | {link} |")
    else:
        lines.append("| — | (取得できませんでした) |")
    return lines


def to_markdown(results: list[tuple[str, list[dict]]], period: str, now: datetime) -> str:
    period_label = PERIOD_LABEL.get(period, period)
    subreddit_names = " + ".join(f"r/{s}" for s, _ in results)
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# Reddit AI Top Posts ({period_label}) - {now.strftime('%Y-%m-%d')}",
        f"*取得日時: {datetime_str} | 対象: {subreddit_names}*",
        "",
        "---",
        "",
    ]

    for subreddit, posts in results:
        lines.extend(section_md(subreddit, posts))
        lines.append("")

    return "\n".join(lines)


def _default_output_path(period: str, now: datetime) -> str:
    """--output 省略時のデフォルト出力先を計算する。"""
    filename = f"reddit_ai_{period}_{now.strftime('%Y%m%d_%H%M%S')}.md"
    return os.path.join(MANUAL_OUTPUT_DIR, filename)


def main():
    parser = argparse.ArgumentParser(
        description="Reddit サブレディット Top N を Markdown で保存"
    )
    parser.add_argument("--subreddit", "-s", nargs="+", default=[],
                        metavar="SUBREDDIT",   help="サブレディット名（複数指定可）")
    parser.add_argument("--ai",               action="store_true", help="AI 関連サブレディット一括取得")
    parser.add_argument("--limit",     "-n",  type=int, default=10,  help="各サブレディットの取得件数 (default: 10)")
    parser.add_argument("--period",    "-p",  default="day",
                        choices=["day", "week", "month", "year", "all"],
                        help="集計期間 (default: day)")
    parser.add_argument("--output",    "-o",  default="", help="出力ファイルパス (省略時は自動生成)")
    args = parser.parse_args()

    # 対象サブレディット決定
    subreddits = list(args.subreddit)
    if args.ai:
        for s in AI_SUBREDDITS:
            if s not in subreddits:
                subreddits.append(s)
    if not subreddits:
        subreddits = ["ClaudeCode"]

    now = datetime.now(JST)
    if args.output:
        output = args.output
    else:
        output = _default_output_path(args.period, now)
        os.makedirs(os.path.dirname(output), exist_ok=True)

    # 単一 subreddit は 1 リクエストで完結し 429 リスクが無いため、統合 URL の
    # 偏りトレードオフ（fetch_top_posts_multi の docstring 参照）を持ち込まず
    # 既存の fetch_top_posts() をそのまま使う。
    if len(subreddits) > 1:
        multi_results = fetch_top_posts_multi(subreddits, args.limit, args.period)
        results = [(s, multi_results[s]) for s in subreddits]
    else:
        results = [(s, fetch_top_posts(s, args.limit, args.period)) for s in subreddits]
    total = sum(len(posts) for _, posts in results)
    print(f"[INFO] 合計 {total} 件取得しました ({len(subreddits)} サブレディット)")

    md = to_markdown(results, args.period, now)
    with open(output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[INFO] 保存完了 → {output}")
    print("[DONE]")


if __name__ == "__main__":
    main()
