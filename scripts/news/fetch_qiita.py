#!/usr/bin/env python3
"""
Qiita 人気記事 Atom フィード取得スクリプト
ソース: https://qiita.com/popular-items/feed.atom

使い方:
    python3 fetch_qiita.py
    python3 fetch_qiita.py --limit 10
    python3 fetch_qiita.py --ai-only               # AI 関連トピックのみ抽出
    python3 fetch_qiita.py --keywords AI LLM GPT   # 独自キーワードで抽出

環境変数:
    QIITA_ACCESS_TOKEN（任意）: いいね数を Qiita API で取るときに使う
"""

from __future__ import annotations
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from constants import USER_AGENT, fetch_feed_entries, run_feed_cli

FEED_URL = "https://qiita.com/popular-items/feed.atom"
# フィードにはいいね数が無いため、記事ごとに API で取る
ITEM_API = "https://qiita.com/api/v2/items/{item_id}"
_ITEM_PATH_RE = re.compile(r"/[^/]+/items/([0-9A-Za-z]+)")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# 人気記事を毎日まとめて紹介する記事。人気記事そのものではないため除く
DIGEST_TITLE_MARKER = "今日のQiitaトレンド記事"


def strip_query(url: str) -> str:
    """フィードの URL に付く utm_* の追跡パラメータ（クエリ文字列）と fragment を外す。"""
    return urllib.parse.urlsplit(url)._replace(query="", fragment="").geturl()


def _parse_atom_entries(root: ET.Element, limit: int = 0) -> list[dict]:
    """Atom フィードの <entry> から title / url（クエリ文字列を除く）を取り出す。

    紹介記事は除く。limit=0 のとき全件返す。
    """
    results = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        title = title_el.text.strip() if title_el is not None and title_el.text else "(タイトルなし)"
        if DIGEST_TITLE_MARKER in title:
            continue

        # <link rel="alternate" href="...">
        url = ""
        for link_el in entry.findall("atom:link", ATOM_NS):
            if link_el.get("rel", "alternate") == "alternate":
                url = strip_query(link_el.get("href", ""))
                break

        results.append({"title": title, "url": url})

    return results if limit == 0 else results[:limit]


def fetch_likes_count(url: str, token: str = "") -> int | None:
    """Qiita API で記事のいいね数を取る。取れなければ [WARN] を出して None を返す（表からは落とさない）。"""
    parts = urllib.parse.urlsplit(url)
    match = _ITEM_PATH_RE.fullmatch(parts.path) if parts.netloc == "qiita.com" else None
    if not match:
        print(f"[WARN] Qiita API: 記事の ID を URL から取れません {url} — いいね数なしで続けます", file=sys.stderr)
        return None

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    # 認証なしの上限（ IP ごとに 1 時間 60 回）は、取り直しや Actions の runner の共有で届きうるため
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(ITEM_API.format(item_id=match.group(1)), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[WARN] Qiita API: {url} のいいね数を取れません（ HTTP {e.code} ）— いいね数なしで続けます", file=sys.stderr)
        return None
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[WARN] Qiita API: {url} のいいね数を取れません（ {e} ）— いいね数なしで続けます", file=sys.stderr)
        return None
    likes = data.get("likes_count") if isinstance(data, dict) else None
    if not isinstance(likes, int) or isinstance(likes, bool):
        print(f"[WARN] Qiita API: {url} の likes_count の形式が不正です — いいね数なしで続けます", file=sys.stderr)
        return None
    return likes


def fetch_entries(limit: int = 10, keywords: list[str] | None = None) -> list[dict]:
    """Qiita 人気記事フィードからエントリーを取得する。エラー時は空リストを返す。"""
    return fetch_feed_entries(FEED_URL, _parse_atom_entries, "Qiita", limit, keywords)


def main():
    run_feed_cli("Qiita 人気記事フィードから記事を取得して表示", fetch_entries)


if __name__ == "__main__":
    main()
