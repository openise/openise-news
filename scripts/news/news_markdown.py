"""News の履歴ファイル読み込みと Markdown リンク解析。"""

import os
import re
from collections.abc import Iterator
from datetime import datetime, timedelta

# render_external_link が出力するリンク。タイトル内の ] は \] にエスケープ済み
MARKDOWN_LINK_RE = re.compile(r"\[((?:\\.|[^\]\\])*)\]\(([^)\s]+)\)")


def extract_link_urls(text: str) -> set[str]:
    """Markdown リンクの URL を、エスケープや percent-encode を保ったまま返す。"""
    return {match.group(2) for match in MARKDOWN_LINK_RE.finditer(text)}


def iter_history_news(date: datetime, base_dir: str, history_days: int) -> Iterator[tuple[str, str]]:
    """前日から history_days 日前まで（両端を含む）の存在する News のパスと内容を返す。"""
    for days in range(1, history_days + 1):
        path = os.path.join(base_dir, (date - timedelta(days=days)).strftime("%Y%m%d"), "index.md")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        yield path, text
