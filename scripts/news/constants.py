"""
scripts/news/constants.py - ニュース取得スクリプト共通定数・フィード取得共通処理
"""

import argparse
import http.client
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat
from collections.abc import Callable
from datetime import timedelta, timezone
from pathlib import Path

USER_AGENT = "OpeniseDailyFetcher/1.0"

JST = timezone(timedelta(hours=9))

# 単体 fetcher（fetch_hn.py・fetch_hb.py・fetch_reddit.py）の既定出力先。
# src/content/news/ は fetch_ai_news.py だけが書き込む対象であり、ここには置かない。
MANUAL_OUTPUT_DIR = str(Path(__file__).resolve().parents[2] / "vault" / "news-manual")

# 4 文字以上のキーワードは後ろに英字が続いても当たるため、muse（Museum）や loop（Loopback）のような
# 一般的な語の前方部分になる語は入れない。表記ゆれ（VS Code ・ Next.js ・ Neovim）は別のキーワードとして並べる
AI_KEYWORDS: list[str] = [
    # AI ・モデル・サービス
    "ai", "llm", "gpt", "claude", "gemini", "copilot", "chatgpt", "codex",
    "grok", "deepseek", "kimi", "qwen", "glm", "ollama", "opencode", "gemma",
    "openai", "anthropic",
    # AI 開発の用語
    "agent", "vibe", "skills", "api", "mcp", "harness", "superpowers", "jev",
    # 開発ツール
    "vscode", "vs code", "cursor", "devin", "vim", "neovim", "tmux", "ghostty",
    "git", "github", "gitlab", "cloudflare",
    # プログラミング
    "python", "javascript", "typescript", "node", "rust", "ruby", "rails",
    "nextjs", "next.js", "markdown", "mermaid", "css", "wordpress", "astro",
    "adr", "tdd", "sdd", "e2e", "playwright", "cve",
]


def filter_by_keywords(entries: list[dict], keywords: list[str]) -> list[dict]:
    """タイトルに指定キーワード（大文字小文字不問）を含む記事のみ返す。

    左側は全キーワードで ASCII 英数字の境界を必須とする。右側は 3 文字以下の
    キーワードのみ同じ境界を必須とし、複数形の s は許す。長いキーワードは
    ClaudeCode などの後方複合語も許す。GPT は数字・小数点付き番号も許す。
    日本語の隣接は境界として扱う。
    """
    patterns = []
    for k in keywords:
        suffix = r"s?(?![a-z0-9])" if len(k) <= 3 else ""
        if k.lower() == "gpt":
            # 小数点の先に数字が残る部分一致を防ぎ、GPT4.1server を除外する。
            suffix = r"(?:\d+(?:\.\d+)*)?s?(?![a-z0-9]|\.\d)"
        patterns.append(re.compile(r"(?<![a-z0-9])" + re.escape(k) + suffix, re.IGNORECASE | re.ASCII))
    return [e for e in entries if any(p.search(e.get("title") or "") for p in patterns)]


def fetch_url(url: str, user_agent: str, source_label: str, timeout: int = 20) -> bytes | None:
    """指定 URL を取得する。エラー時は [WARN] ログを出力して None を返す（sys.exit しない）。"""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"[WARN] {source_label}: HTTP {e.code} {e.reason} — スキップします", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"[WARN] {source_label}: 接続失敗 {e.reason} — スキップします", file=sys.stderr)
        return None
    except (OSError, http.client.IncompleteRead) as e:
        print(f"[WARN] {source_label}: レスポンス読み込み失敗 {e} — スキップします", file=sys.stderr)
        return None


class _DoctypeFound(Exception):
    """DOCTYPE 宣言を検出したことを示す内部シグナル（例外メッセージは使わない）。"""


def _raise_doctype_found(*_args: object) -> None:
    raise _DoctypeFound


def _contains_doctype(xml_bytes: bytes) -> bool:
    """DOCTYPE 宣言の有無を encoding に依存せず判定する。

    `StartDoctypeDeclHandler` は内部 DTD サブセット（エンティティ定義）がパースされる
    前に呼ばれるため、検出した時点で例外を送出しエンティティ展開そのものを防ぐ。
    バイト列の部分文字列一致と異なり、 UTF-16 等の feed でも expat 自身の
    encoding 自動検出に従って正しく判定できる。
    """
    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = _raise_doctype_found

    try:
        parser.Parse(xml_bytes, True)
    except _DoctypeFound:
        return True
    except expat.ExpatError:
        pass  # 壊れた XML は後段の ET.fromstring が同様に検出し [WARN] を出す

    return False


def parse_xml(xml_bytes: bytes, source_label: str) -> ET.Element | None:
    """XML をパースして root 要素を返す。パース失敗時は [WARN] ログを出力して None を返す。

    DOCTYPE 宣言を含む XML は billion laughs（内部エンティティの再帰展開による
    メモリ枯渇）を防ぐため拒否する。正当な RSS/Atom フィードは DOCTYPE を使わない。
    """
    if _contains_doctype(xml_bytes):
        print(f"[WARN] {source_label}: DOCTYPE 宣言を検出したため拒否します — スキップします", file=sys.stderr)
        return None

    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[WARN] {source_label}: XML パース失敗 {e} — スキップします", file=sys.stderr)
        return None


def parse_rss_items(root: ET.Element, limit: int = 0) -> list[dict]:
    """RSS 2.0 形式（<channel><item>）から title / url を取り出す。limit=0 のとき全件返す。"""
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall("item")

    results = []
    for item in (items if limit == 0 else items[:limit]):
        title_el = item.find("title")
        link_el = item.find("link")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        url = link_el.text.strip() if link_el is not None and link_el.text else ""
        results.append({"title": title or "(タイトルなし)", "url": url})

    return results


def fetch_feed_entries(
    url: str,
    parser: Callable[[ET.Element, int], list[dict]],
    source_label: str,
    limit: int = 10,
    keywords: list[str] | None = None,
) -> list[dict]:
    """フィードを取得し parser でエントリー化する。取得・パース失敗時は空リストを返す。"""
    print(f"[INFO] フィード取得中 ... {url}")

    raw = fetch_url(url, user_agent=USER_AGENT, source_label=source_label)
    if raw is None:
        return []

    root = parse_xml(raw, source_label)
    if root is None:
        return []

    parse_limit = 0 if keywords else limit  # キーワードあり: 全件パースしてからフィルタ
    entries = parser(root, parse_limit)
    if keywords:
        entries = filter_by_keywords(entries, keywords)[:limit]
    return entries


def run_feed_cli(description: str, fetch_entries: Callable[..., list[dict]]) -> None:
    """フィード取得スクリプト共通の CLI エントリーポイント（--limit / --ai-only / --keywords）。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--limit",    "-n", type=int, default=10,  help="取得件数 (default: 10)")
    parser.add_argument("--ai-only",        action="store_true",   help="AI 関連キーワードでフィルタリング")
    parser.add_argument("--keywords", "-k", nargs="+", default=[], help="独自キーワードでフィルタリング (スペース区切り, --ai-only と併用可)")
    args = parser.parse_args()

    keywords = list(args.keywords)
    if args.ai_only:
        keywords = AI_KEYWORDS + keywords

    entries = fetch_entries(limit=args.limit, keywords=keywords or None)

    if not entries:
        print("(該当記事なし)")
        return

    for i, e in enumerate(entries, 1):
        print(f"{i}. {e['title']}")
        print(f"   {e['url']}")


_MD_ESCAPE_RE = re.compile(r"([\\\[\]|()])")

# Markdown の link destination 内で表・リンク構文を壊しうる文字の percent-encode 表。
# `%` 自体は encode しない（percent-encode 済みの URL を二重エンコードしないため）。
_URL_UNSAFE_CHARS = {
    " ":  "%20",
    "(":  "%28",
    ")":  "%29",
    "<":  "%3C",
    ">":  "%3E",
    "|":  "%7C",
}


def _sanitize_url(parsed: urllib.parse.ParseResult) -> str:
    """検証済みの URL を Markdown の link destination として安全な形に整える。

    `urlparse` は ASCII の改行（CR / LF）・タブを除去して解析するため、解析結果から
    `urlunparse` で組み直すことで元の文字列に残っていたそれらを確実に落とす。
    """
    safe_url = urllib.parse.urlunparse(parsed)
    for char, encoded in _URL_UNSAFE_CHARS.items():
        safe_url = safe_url.replace(char, encoded)
    return safe_url


def render_external_link(title: str, url: str) -> str:
    """外部由来の title / url を Markdown リンクに安全に変換する。

    - HTML タグをエスケープして実行不可にする
    - Markdown の backslash, brackets, pipe, parens をエスケープして表・リンク構文の崩れを防止
    - URL の改行・タブを除去し、空白・括弧・山括弧・パイプを percent-encode して link destination の崩れを防止
    - HTTP(S) 以外のスキーム（javascript: 等）はリンク化しない
    - URL が空・スキーム欠損の場合もリンク化しない
    """
    safe_title = html.escape(title, quote=True)
    safe_title = _MD_ESCAPE_RE.sub(r"\\\1", safe_title)
    safe_title = re.sub(r"[\r\n]+", " ", safe_title)

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return f"[{safe_title}]({_sanitize_url(parsed)})"
    return safe_title
