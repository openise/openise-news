#!/usr/bin/env python3
"""
Zenn Daily ランキング取得スクリプト
ソース: https://zenn.dev/api/articles?order=daily （非公式 API）

使い方:
    python3 fetch_zenn.py
    python3 fetch_zenn.py --limit 10
    python3 fetch_zenn.py --ai-only               # AI 関連トピックのみ抽出
    python3 fetch_zenn.py --keywords AI LLM GPT   # 独自キーワードで抽出
"""

from __future__ import annotations

import json
import sys

from constants import USER_AGENT, fetch_url, filter_by_keywords, run_feed_cli

API_URL = "https://zenn.dev/api/articles?order=daily"
BASE_URL = "https://zenn.dev"


def _parse_articles(raw: bytes) -> list[dict] | None:
    """API の応答から title / url / liked_count を取り出す。形式が不正なら None を返す。"""
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"[WARN] Zenn: response の decode / JSON パース失敗 {e} — スキップします", file=sys.stderr)
        return None

    articles = data.get("articles") if isinstance(data, dict) else None
    if not isinstance(articles, list):
        print("[WARN] Zenn: articles の形式が不正です — スキップします", file=sys.stderr)
        return None

    results = []
    for a in articles:
        # 非公式 API のため、1 件の形が崩れていても他の記事は残す
        if not isinstance(a, dict):
            continue
        title, path, liked = a.get("title"), a.get("path"), a.get("liked_count")
        if not isinstance(path, str) or not path.startswith("/"):
            continue
        if not isinstance(liked, int) or isinstance(liked, bool):
            continue
        title = title.strip() if isinstance(title, str) else ""
        results.append({"title": title or "(タイトルなし)", "url": BASE_URL + path, "liked_count": liked})
    return results


def fetch_entries(limit: int = 10, keywords: list[str] | None = None) -> list[dict]:
    """Zenn の Daily ランキングを、いいね数の多い順に返す。limit=0 のとき全件返す。エラー時は空リストを返す。"""
    print(f"[INFO] API 取得中 ... {API_URL}")
    raw = fetch_url(API_URL, user_agent=USER_AGENT, source_label="Zenn")
    if raw is None:
        return []

    entries = _parse_articles(raw)
    if entries is None:
        return []

    if keywords:
        entries = filter_by_keywords(entries, keywords)
    # API の並びはいいね数の順ではないため並べ替える。同数は API の順のまま残す
    entries = sorted(entries, key=lambda e: -e["liked_count"])
    return entries if limit == 0 else entries[:limit]


def main():
    run_feed_cli("Zenn の Daily ランキングから記事を取得して表示", fetch_entries)


if __name__ == "__main__":
    main()
