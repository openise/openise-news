"""収集・キュレーションの履歴除外とリンク解析の回帰テスト。"""

from datetime import datetime, timedelta

import pytest

import curate_news
import fetch_ai_news
from constants import JST, render_external_link
from news_markdown import extract_link_urls


@pytest.mark.parametrize("history_days,reader", [
    (7, lambda date, base: fetch_ai_news.recent_urls(date, base, fetch_ai_news.HB_HEADING)),
    (30, curate_news.recent_picked_urls),
])
def test_history_boundaries_and_section_filters(tmp_path, history_days, reader):
    date = datetime(2026, 1, 3, tzinfo=JST)
    for days in (0, 1, history_days, history_days + 1):
        path = tmp_path / (date - timedelta(days=days)).strftime("%Y%m%d") / "index.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            '---\ntitle: x\n---\n'
            f'## 今日のピックアップ\n1. [選定](https://example.com/pick/{days})\n'
            f'## はてなブックマーク\n| 1 | [記事](https://example.com/hb/{days}) | 10 |\n'
            f'## Qiita\n| 1 | [他ソース](https://example.com/qiita/{days}) | 5 |\n',
            encoding="utf-8",
        )
    section = "hb" if history_days == 7 else "pick"
    assert reader(date, str(tmp_path)) == {
        f"https://example.com/{section}/1",
        f"https://example.com/{section}/{history_days}",
    }


@pytest.mark.parametrize("frontmatter", ["", "---\ntitle: x\n"])
def test_history_preserves_invalid_frontmatter_policy(tmp_path, capsys, frontmatter):
    path = tmp_path / "20261102" / "index.md"
    path.parent.mkdir()
    path.write_text(
        frontmatter + '## 今日のピックアップ\n1. [選定](https://example.com/pick)\n'
        '## はてなブックマーク\n| 1 | [記事](https://example.com/hb) | 1 |\n',
        encoding="utf-8",
    )
    date = datetime(2026, 11, 3, tzinfo=JST)
    assert fetch_ai_news.recent_urls(date, str(tmp_path), fetch_ai_news.HB_HEADING) == {"https://example.com/hb"}
    assert curate_news.recent_picked_urls(date, str(tmp_path)) == set()
    assert capsys.readouterr().err == f"[WARN] frontmatter が無いため重複除外の対象外にします: {path}\n"


def test_escaped_link_round_trip_through_both_history_readers(tmp_path):
    title = r"Claude [入門] (実践) | C:\tools"
    url = "https://example.com/a_(b)?q=(x)&lang=ja#part"
    expected_url = "https://example.com/a_%28b%29?q=%28x%29&lang=ja#part"
    link = render_external_link(title, url)
    assert extract_link_urls(f"{link} {link}") == {expected_url}
    body = f"## はてなブックマーク\n| 1 | {link} | 10 |\n"
    candidate = curate_news.parse_candidates(body)[0]
    assert candidate["url"] == expected_url
    assert curate_news.plain_title(candidate["link_text"]) == title
    path = tmp_path / "20261102" / "index.md"
    path.parent.mkdir()
    path.write_text(
        f"---\ntitle: x\n---\n## 今日のピックアップ\n1. **{link}**\n{body}",
        encoding="utf-8",
    )
    date = datetime(2026, 11, 3, tzinfo=JST)
    fetched = fetch_ai_news.recent_urls(date, str(tmp_path), fetch_ai_news.HB_HEADING)
    assert fetched == curate_news.recent_picked_urls(date, str(tmp_path)) == {expected_url}
    assert fetch_ai_news._is_excluded({"title": title, "url": url}, fetched)
