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
# はてなブックマークのタグ別新着エントリーのページにも Zenn の Daily ランキングにも Qiita の人気記事フィードにも数日分の記事が並ぶため、
# それより長い期間を見て重複を除く
HISTORY_DAYS = 7
HB_HEADING = "## はてなブックマーク"
ZENN_HEADING = "## Zenn"
QIITA_HEADING = "## Qiita"
HN_HEADING = "## Hacker News"
REDDIT_HEADING = "## Reddit"
REDDIT_MIN_POSTS_PER_SUBREDDIT = 2

# render_external_link が出力するリンク。タイトル内の ] は \] にエスケープ済み
_LINK_RE = re.compile(r"\[((?:\\.|[^\]\\])*)\]\(([^)\s]+)\)")


# -----------------------------------------------------------------------
# セクション生成
# -----------------------------------------------------------------------

def recent_urls(now: datetime, base_dir: str, heading: str) -> set[str]:
    """対象日の前日から 7 日前まで（両端を含む）の News で、heading の表にある URL を返す。"""
    urls = set()
    for days in range(1, HISTORY_DAYS + 1):
        path = os.path.join(base_dir, (now - timedelta(days=days)).strftime("%Y%m%d"), "index.md")
        if not os.path.exists(path):
            continue
        in_section = False
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    in_section = line.startswith(heading)
                    continue
                if in_section:
                    urls.update(m.group(2) for m in _LINK_RE.finditer(line))
    return urls


def _is_excluded(entry: dict, excluded_urls: set[str]) -> bool:
    # 過去の表と同じ形で比べるため、表に書き出すときのリンクから URL を取り出す
    link = _LINK_RE.fullmatch(render_external_link(entry["title"], entry["url"]))
    return bool(link) and link.group(2) in excluded_urls


def hb_section(limit: int, excluded_urls: set[str] = frozenset()) -> list[str]:
    """はてなブックマーク AI×プログラミング関連 Top N（プログラミングタグの新着エントリーから AI キーワード一致で抽出、重複記事と excluded_urls の記事は除外、ブックマーク数の多い順）"""
    entries = fetch_hb.fetch_entrylist_tag_entries(category="it", tag="プログラミング", limit=50)

    filtered = []
    seen_titles = set()
    for e in filter_by_keywords(entries, AI_KEYWORDS):
        if e["title"] in seen_titles:
            continue
        if _is_excluded(e, excluded_urls):
            continue
        seen_titles.add(e["title"])
        filtered.append(e)
    # sorted は安定ソートなので、同数の記事は取得元ページの順のまま残る
    filtered = sorted(filtered, key=lambda e: -e["bookmark_count"])[:limit]

    lines = [
        HB_HEADING,
        "",
        "| # | タイトル | BM |",
        "|---|---|---|",
    ]
    if filtered:
        for i, e in enumerate(filtered, 1):
            link = render_external_link(e["title"], e["url"])
            lines.append(f"| {i} | {link} | {e['bookmark_count']} |")
    else:
        lines.append("| — | (該当なし) | — |")
    return lines


def hn_section(limit: int, now: datetime, excluded_urls: set[str] = frozenset()) -> list[str]:
    """Hacker News AI 関連 Show HN / Ask HN 合算 Top N（now の日付の前々日 0:00 〜 前日 0:00 JST の投稿、excluded_urls の投稿は除外）"""
    # 投稿直後は points が付いていないため、1 日たった記事で比べる。取得した時刻から範囲を決めると、
    # 時刻が日によってずれたときに前日の範囲と重なったりすき間ができたりするため、日付で区切る
    end = now.astimezone(JST).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start = end - timedelta(days=1)
    # API の条件は「since より後・until 以下」なので、1 秒ずらして「start 以上・end 未満」にする
    since = int(start.timestamp()) - 1
    until = int(end.timestamp()) - 1

    # 多めに取得してから AI フィルタ
    show_raw = fetch_hn.fetch_hits_or_none("show_hn", since, limit=50, until=until)
    ask_raw  = fetch_hn.fetch_hits_or_none("ask_hn",  since, limit=50, until=until)
    hits = fetch_hn.filter_by_keywords((show_raw or []) + (ask_raw or []), fetch_hn.AI_KEYWORDS)
    # 日付で区切った範囲どうしは重ならないため、ここで除かれるのは、取得した時刻で範囲を決めていた頃の表と
    # 範囲が重なる切り替え直後の 7 日だけ。それより後は何も除かないので、外してよい
    hits = [
        h for h in hits
        if not _is_excluded({"title": h.get("title") or "", "url": fetch_hn.HN_BASE + h.get("objectID", "")}, excluded_urls)
    ]

    # Points 降順 → Comments 降順で Top N
    ranked = sorted(hits, key=lambda h: (-(h.get("points") or 0), -(h.get("num_comments") or 0)))[:limit]

    lines = [
        HN_HEADING,
        "",
        "| # | タイトル | Points |",
        "|---|---|---|",
    ]
    if ranked:
        for i, h in enumerate(ranked, 1):
            title = h.get("title") or ""
            url = fetch_hn.HN_BASE + h.get("objectID", "")
            link = render_external_link(title, url)
            lines.append(f"| {i} | {link} | {h.get('points') or 0} |")
    elif show_raw is None and ask_raw is None:
        lines.append("| — | (取得できませんでした) | — |")
    else:
        lines.append("| — | (該当なし) | — |")
    lines.append("")

    return lines


def reddit_section(limit: int, period: str, excluded_urls: set[str] = frozenset()) -> list[str]:
    """Reddit AI 関連サブレディット ピックアップ（RSS フィード経由、スコア順。各サブレディットに最低件数を確保、excluded_urls の投稿は除外）"""
    # 取得側でサブレディットごとに limit 件で打ち切るため、打ち切りより前に除くよう判定を渡す
    ranked = fetch_reddit.fetch_top_posts_ranked(
        fetch_reddit.AI_SUBREDDITS, limit, period, exclude=lambda p: _is_excluded(p, excluded_urls),
    )

    # スコア順だけで選ぶと、勢いのあるサブレディットが枠を占めてほかが 1 件も載らなく
    # なるため、各サブレディットの上位 REDDIT_MIN_POSTS_PER_SUBREDDIT 件を先に選ぶ。
    # 1 件目同士・2 件目同士を先に比べるので、limit が小さくても全サブレディットの
    # 1 件目が 2 件目より優先される
    rank_in_subreddit = {sub: 0 for sub in fetch_reddit.AI_SUBREDDITS}
    keyed = []
    for sub, feed_rank, post in ranked:
        priority = min(rank_in_subreddit[sub], REDDIT_MIN_POSTS_PER_SUBREDDIT)
        rank_in_subreddit[sub] += 1
        keyed.append((priority, feed_rank, post))
    chosen = sorted(keyed, key=lambda k: (k[0], k[1]))[:limit]
    top = [(feed_rank, post) for _, feed_rank, post in sorted(chosen, key=lambda k: k[1])]

    lines = [
        REDDIT_HEADING,
        "",
        "| # | タイトル | 順位 |",
        "|---|---|---|",
    ]
    if top:
        for i, (feed_rank, p) in enumerate(top, 1):
            link = render_external_link(p["title"], p["url"])
            lines.append(f"| {i} | {link} | {feed_rank} |")
    else:
        lines.append("| — | (取得できませんでした) | — |")
    lines.append("")

    return lines


def github_trend_section(limit: int) -> list[str]:
    """GitHub Trending AI 関連 Top N"""
    entries = fetch_github_trend.fetch_entries(limit=limit, keywords=AI_KEYWORDS)

    lines = [
        "## GitHub Trending",
        "",
        "| # | リポジトリ | Star |",
        "|---|---|---|",
    ]
    if entries:
        for i, e in enumerate(entries, 1):
            link = render_external_link(e["title"], e["url"])
            stars = "—" if e["stars_today"] is None else e["stars_today"]
            lines.append(f"| {i} | {link} | {stars} |")
    else:
        lines.append("| — | (取得できませんでした) | — |")
    lines.append("")
    return lines


def qiita_section(limit: int, excluded_urls: set[str] = frozenset()) -> list[str]:
    """Qiita 人気記事のうちキーワードに一致するもの Top N（excluded_urls の記事は除外、いいね数の多い順）"""
    # 過去の表には追跡パラメータ付きの URL が残っているため、外した形にそろえて比べる
    excluded_urls = {fetch_qiita.strip_query(u) for u in excluded_urls}
    entries = filter_by_keywords(fetch_qiita.fetch_entries(limit=0), AI_KEYWORDS)
    entries = [e for e in entries if not _is_excluded(e, excluded_urls)]
    # API の呼び出し回数を抑えるため、絞り込んで重複を除いた記事だけいいね数を取る
    token = os.environ.get("QIITA_ACCESS_TOKEN", "")
    entries = [{**e, "likes_count": fetch_qiita.fetch_likes_count(e["url"], token)} for e in entries]
    # 安定ソートなので、同数はフィードの順のまま残る。取れなかった記事は最後にする
    entries = sorted(
        entries, key=lambda e: (e["likes_count"] is None, -(e["likes_count"] or 0)),
    )[:limit]

    lines = [
        QIITA_HEADING,
        "",
        "| # | タイトル | いいね |",
        "|---|---|---|",
    ]
    if entries:
        for i, e in enumerate(entries, 1):
            link = render_external_link(e["title"], e["url"])
            likes = "—" if e["likes_count"] is None else e["likes_count"]
            lines.append(f"| {i} | {link} | {likes} |")
    else:
        lines.append("| — | (該当なし) | — |")
    lines.append("")
    return lines


def zenn_section(limit: int, excluded_urls: set[str] = frozenset()) -> list[str]:
    """Zenn AI 関連 Daily ランキング Top N（excluded_urls の記事は除外、いいね数の多い順）"""
    entries = fetch_zenn.fetch_entries(limit=0, keywords=AI_KEYWORDS)
    entries = [e for e in entries if not _is_excluded(e, excluded_urls)][:limit]

    lines = [
        ZENN_HEADING,
        "",
        "| # | タイトル | いいね |",
        "|---|---|---|",
    ]
    if entries:
        for i, e in enumerate(entries, 1):
            link = render_external_link(e["title"], e["url"])
            lines.append(f"| {i} | {link} | {e['liked_count']} |")
    else:
        lines.append("| — | (取得できませんでした) | — |")
    lines.append("")
    return lines


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
    hb = hb_section(limit, recent_urls(now, BASE_DIR, HB_HEADING))

    print("[INFO] Hacker News 取得中 ...")
    hn = hn_section(limit, now, recent_urls(now, BASE_DIR, HN_HEADING))

    print("[INFO] Reddit 取得中 ...")
    rd = reddit_section(limit, period, recent_urls(now, BASE_DIR, REDDIT_HEADING))

    print("[INFO] GitHub Trending 取得中 ...")
    gt = github_trend_section(limit)

    print("[INFO] Qiita 取得中 ...")
    qt = qiita_section(limit, recent_urls(now, BASE_DIR, QIITA_HEADING))

    print("[INFO] Zenn 取得中 ...")
    zn = zenn_section(limit, recent_urls(now, BASE_DIR, ZENN_HEADING))

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
