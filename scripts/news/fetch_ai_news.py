#!/usr/bin/env python3
"""
fetch_ai_news.py - はてなブックマーク・Hacker News・Reddit・GitHub Trend・Qiita・Zenn から
                   AI 関連トピック Top N を取得して1ファイルにまとめる

使い方:
    python3 fetch_ai_news.py
    python3 fetch_ai_news.py --limit 10 --period day
    python3 fetch_ai_news.py --output /path/to/output.md
"""

import sys
import os
import re
import tempfile
from datetime import datetime, timedelta
from itertools import zip_longest
from pathlib import Path
import argparse

BASE_DIR = str(Path(__file__).resolve().parents[2] / "src/content/news")

# 同じ scripts/ ディレクトリにある既存モジュールを import
sys.path.insert(0, os.path.dirname(__file__))
import fetch_hb
import fetch_hn
import fetch_reddit
import fetch_github_trend
import fetch_qiita
import fetch_zenn
from constants import AI_KEYWORDS, JST, filter_by_keywords, render_external_link

LIMIT = 10
# タグ別人気エントリーのページには数日分の記事が並ぶため、それより長い期間を見て重複を除く
HB_HISTORY_DAYS = 7
HB_HEADING = "## はてなブックマーク"

# render_external_link が出力するリンク。タイトル内の ] は \] にエスケープ済み
_LINK_RE = re.compile(r"\[((?:\\.|[^\]\\])*)\]\(([^)\s]+)\)")


# -----------------------------------------------------------------------
# セクション生成
# -----------------------------------------------------------------------

def recent_hb_urls(now: datetime, base_dir: str) -> set[str]:
    """対象日の前日から 7 日前まで（両端を含む）の News のはてなブックマークの表にある URL を返す。"""
    urls = set()
    for days in range(1, HB_HISTORY_DAYS + 1):
        path = os.path.join(base_dir, (now - timedelta(days=days)).strftime("%Y%m%d"), "index.md")
        if not os.path.exists(path):
            continue
        in_hb = False
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    in_hb = line.startswith(HB_HEADING)
                    continue
                if in_hb:
                    urls.update(m.group(2) for m in _LINK_RE.finditer(line))
    return urls


def hb_section(limit: int, excluded_urls: set[str] = frozenset()) -> list[str]:
    """はてなブックマーク AI×プログラミング関連 Top N（プログラミングタグの人気エントリーから AI キーワード一致で抽出、重複記事と excluded_urls の記事は除外、ブックマーク数の多い順）"""
    entries = fetch_hb.fetch_hotentry_tag_entries(category="it", tag="プログラミング", limit=50)

    filtered = []
    seen_titles = set()
    for e in filter_by_keywords(entries, AI_KEYWORDS):
        if e["title"] in seen_titles:
            continue
        # 過去の表と同じ形で比べるため、表に書き出すときのリンクから URL を取り出す
        link = _LINK_RE.fullmatch(render_external_link(e["title"], e["url"]))
        if link and link.group(2) in excluded_urls:
            continue
        seen_titles.add(e["title"])
        filtered.append(e)
    # sorted は安定ソートなので、同数の記事は取得元ページの順のまま残る
    filtered = sorted(filtered, key=lambda e: -e["bookmark_count"])[:limit]

    lines = [
        HB_HEADING,
        "",
        "| # | タイトル | ブックマーク数 |",
        "|---|---|---|",
    ]
    if filtered:
        for i, e in enumerate(filtered, 1):
            link = render_external_link(e["title"], e["url"])
            lines.append(f"| {i} | {link} | {e['bookmark_count']} |")
    else:
        lines.append("| — | (該当なし) | — |")
    return lines


def hn_section(limit: int) -> list[str]:
    """Hacker News AI 関連 Show HN / Ask HN 合算 Top N"""
    since = int((datetime.now(JST) - timedelta(hours=24)).timestamp())

    # 多めに取得してから AI フィルタ
    show_raw = fetch_hn.fetch_hits("show_hn", since, limit=50)
    ask_raw  = fetch_hn.fetch_hits("ask_hn",  since, limit=50)
    show = fetch_hn.filter_by_keywords(show_raw, fetch_hn.AI_KEYWORDS)
    ask  = fetch_hn.filter_by_keywords(ask_raw,  fetch_hn.AI_KEYWORDS)

    # タグを付与して合算し、Points 降順 → Comments 降順で Top N
    for h in show: h["_tag"] = "Show HN"
    for h in ask:  h["_tag"] = "Ask HN"
    ranked = sorted(show + ask, key=lambda h: (-(h.get("points") or 0), -(h.get("num_comments") or 0)))[:limit]

    lines = [
        "## Hacker News",
        "*対象: Show HN + Ask HN の合算ランキング*",
        "",
        "| # | 種別 | タイトル | Points | Comments |",
        "|---|---|---|---|---|",
    ]
    if ranked:
        for i, h in enumerate(ranked, 1):
            url = fetch_hn.HN_BASE + h.get("objectID", "")
            link = render_external_link(h.get("title") or "", url)
            lines.append(f"| {i} | {h['_tag']} | {link} | {h.get('points') or 0} | {h.get('num_comments') or 0} |")
    else:
        lines.append("| — | — | (該当なし) | — | — |")
    lines.append("")

    return lines


def reddit_section(limit: int, period: str) -> list[str]:
    """Reddit AI 関連サブレディット ピックアップ（RSS フィード経由、サブレディットごとに均等割り）"""
    posts_by_subreddit_dict = fetch_reddit.fetch_top_posts_multi(fetch_reddit.AI_SUBREDDITS, limit, period)
    posts_by_subreddit = []
    for sub in fetch_reddit.AI_SUBREDDITS:
        posts = posts_by_subreddit_dict[sub]
        for p in posts:
            p["subreddit"] = sub
        posts_by_subreddit.append(posts)

    # サブレディットを 1 件ずつ巡回して拾う。単純連結だと先頭のサブレディットが
    # limit 件の枠を占有し、後続のサブレディットが 1 件も載らなくなるため。
    interleaved = [p for row in zip_longest(*posts_by_subreddit) for p in row if p is not None]
    top = interleaved[:limit]

    lines = [
        "## Reddit",
        f"*対象: {', '.join('r/' + s for s in fetch_reddit.AI_SUBREDDITS)} から均等に抽出*",
        "",
        "| # | サブレディット | タイトル |",
        "|---|---|---|",
    ]
    if top:
        for i, p in enumerate(top, 1):
            link = render_external_link(p["title"], p["url"])
            lines.append(f"| {i} | r/{p['subreddit']} | {link} |")
    else:
        lines.append("| — | — | (取得できませんでした) |")
    lines.append("")

    return lines


def simple_table_section(heading: str, column: str, entries: list[dict]) -> list[str]:
    """「見出し + 番号・リンクの 2 列テーブル」形式のセクションを生成する。"""
    lines = [
        heading,
        "",
        f"| # | {column} |",
        "|---|---|",
    ]
    if entries:
        for i, e in enumerate(entries, 1):
            link = render_external_link(e["title"], e["url"])
            lines.append(f"| {i} | {link} |")
    else:
        lines.append("| — | (取得できませんでした) |")
    lines.append("")
    return lines


def github_trend_section(limit: int) -> list[str]:
    """GitHub Trending AI 関連 Top N"""
    entries = fetch_github_trend.fetch_entries(limit=limit, keywords=AI_KEYWORDS)
    return simple_table_section("## GitHub Trending", "リポジトリ", entries)


def qiita_section(limit: int) -> list[str]:
    """Qiita AI 関連人気記事 Top N"""
    entries = fetch_qiita.fetch_entries(limit=limit, keywords=AI_KEYWORDS)
    return simple_table_section("## Qiita", "タイトル", entries)


def zenn_section(limit: int) -> list[str]:
    """Zenn AI 関連最新記事 Top N"""
    entries = fetch_zenn.fetch_entries(limit=limit, keywords=AI_KEYWORDS)
    return simple_table_section("## Zenn", "タイトル", entries)


# -----------------------------------------------------------------------
# まとめ Markdown 生成
# -----------------------------------------------------------------------

WEEKDAYS = "月火水木金土日"


def news_title(now: datetime) -> str:
    """キュレーションの成否に関わらず同じタイトルにするため、日付だけで決める。"""
    return f"{now.year} 年 {now.month:02d} 月 {now.day:02d} 日（{WEEKDAYS[now.weekday()]}）"


def build_markdown(limit: int, period: str, now: datetime) -> str:
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y%m%d%H%M%S")

    print("[INFO] はてなブックマーク 取得中 ...")
    hb = hb_section(limit, recent_hb_urls(now, BASE_DIR))

    print("[INFO] Hacker News 取得中 ...")
    hn = hn_section(limit)

    print("[INFO] Reddit 取得中 ...")
    rd = reddit_section(limit, period)

    print("[INFO] GitHub Trending 取得中 ...")
    gt = github_trend_section(limit)

    print("[INFO] Qiita 取得中 ...")
    qt = qiita_section(limit)

    print("[INFO] Zenn 取得中 ...")
    zn = zenn_section(limit)

    lines = [
        "---",
        f'title: "{news_title(now)}"',
        f'createdDate: "{date_str}"',
        "---",
        "",
        *hb,
        "",
        "---",
        "",
        *zn,
        "---",
        "",
        *qt,
        "---",
        "",
        *gt,
        "---",
        "",
        *hn,
        "---",
        "",
        *rd,
        "---",
        "",
        f"*取得日時: {datetime_str} JST*",
    ]
    return "\n".join(lines) + "\n"


# -----------------------------------------------------------------------
# エントリーポイント
# -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="はてなブックマーク・HN・Reddit の AI 関連 Top N をまとめて Markdown で保存"
    )
    parser.add_argument("--limit",  "-n", type=int, default=LIMIT, help=f"各ソースの取得件数 (default: {LIMIT})")
    parser.add_argument("--period", "-p", default="day",
                        choices=["day", "week", "month", "year", "all"],
                        help="Reddit の集計期間 (default: day)")
    parser.add_argument("--output", "-o", default="", help="出力ファイルパス (省略時は自動生成)")
    parser.add_argument("--force", action="store_true", help="既存の出力ファイルを上書きする")
    args = parser.parse_args()

    now = datetime.now(JST)
    if args.output:
        output = args.output
    else:
        out_dir = os.path.join(BASE_DIR, now.strftime("%Y%m%d"))
        os.makedirs(out_dir, exist_ok=True)
        output = os.path.join(out_dir, "index.md")

    if not args.force and os.path.exists(output):
        print(f"[WARN] 出力ファイルが既に存在します: {output} — 上書きには --force を指定してください", file=sys.stderr)
        return

    md = build_markdown(args.limit, args.period, now)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(output) or ".",
            prefix=f".{os.path.basename(output)}.",
            suffix=".tmp",
            delete=False,
        ) as f:
            temporary_path = f.name
            if f.write(md) != len(md):
                raise OSError("内容を完全に書き込めませんでした")

        if args.force:
            os.replace(temporary_path, output)
            temporary_path = None
        else:
            try:
                os.link(temporary_path, output)
            except FileExistsError:
                print(f"[WARN] 出力ファイルが既に存在します: {output} — 上書きには --force を指定してください", file=sys.stderr)
                return
            os.unlink(temporary_path)
            temporary_path = None
    except OSError as error:
        print(f"[ERROR] 保存に失敗しました: {output} ({error})", file=sys.stderr)
        return
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            except OSError as error:
                print(f"[ERROR] 一時ファイルの削除に失敗しました: {temporary_path} ({error})", file=sys.stderr)
    print(f"✅ 保存完了: {output}")


if __name__ == "__main__":
    main()
