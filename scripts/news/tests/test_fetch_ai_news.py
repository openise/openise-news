#!/usr/bin/env python3
"""fetch_ai_news.py のセクション生成テスト"""
import re
import sys
import pytest
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import constants
import fetch_ai_news


@pytest.mark.parametrize("explicit_output", [False, True])
def test_main_does_not_overwrite_existing_output(tmp_path, monkeypatch, capsys, explicit_output):
    monkeypatch.setattr(fetch_ai_news, "BASE_DIR", str(tmp_path))
    output = tmp_path / datetime.now(constants.JST).strftime("%Y%m%d") / "index.md"
    output.parent.mkdir()
    original = "---\ntitle: 手動編集\n---\n## 今日のピックアップ\n保存する本文\n"
    output.write_text(original)
    argv = ["fetch_ai_news.py"]
    if explicit_output:
        argv.extend(["--output", str(output)])
    with patch.object(sys, "argv", argv), \
            patch("fetch_ai_news.build_markdown", side_effect=AssertionError("取得してはいけない")):
        fetch_ai_news.main()
    assert output.read_text() == original
    assert "[WARN]" in capsys.readouterr().err


def _install_save_failure(monkeypatch, output, temporary_path, failure_stage):
    class FailingFile:
        def __init__(self, path):
            self.path = path
            self.name = str(path)

        def __enter__(self):
            self.path.write_bytes(b"partial")
            return self

        def write(self, content):
            if failure_stage == "write":
                raise OSError(28, "No space left on device")
            self.path.write_text(content, encoding="utf-8")

        def __exit__(self, *_args):
            if failure_stage == "close":
                raise OSError(5, "Input/output error")
            return False

    monkeypatch.setattr(
        fetch_ai_news,
        "tempfile",
        SimpleNamespace(NamedTemporaryFile=lambda *_args, **_kwargs: FailingFile(temporary_path)),
        raising=False,
    )
    original_open = open

    def fail_direct_output_write(file, mode="r", *args, **kwargs):
        if str(file) == str(output) and mode in {"w", "x"}:
            return FailingFile(output)
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fail_direct_output_write)


def test_main_preserves_existing_bytes_when_forced_write_fails(
    tmp_path, monkeypatch, capsys
):
    output = tmp_path / "index.md"
    original = "手動編集された News\n".encode("utf-8")
    output.write_bytes(original)
    temporary_path = tmp_path / ".index.md.partial"
    _install_save_failure(monkeypatch, output, temporary_path, "write")

    with patch.object(
        sys, "argv", ["fetch_ai_news.py", "--output", str(output), "--force"]
    ), patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        fetch_ai_news.main()

    assert output.read_bytes() == original
    assert not temporary_path.exists()
    assert "保存に失敗しました" in capsys.readouterr().err


def test_main_does_not_publish_partial_new_output_on_io_failure(
    tmp_path, monkeypatch, capsys
):
    output = tmp_path / "index.md"
    temporary_path = tmp_path / ".index.md.partial"
    _install_save_failure(monkeypatch, output, temporary_path, "write")

    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output)]), \
            patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        fetch_ai_news.main()

    assert not output.exists()
    assert not temporary_path.exists()
    assert "保存に失敗しました" in capsys.readouterr().err


def test_main_preserves_existing_bytes_when_forced_close_fails(
    tmp_path, monkeypatch, capsys
):
    output = tmp_path / "index.md"
    original = "手動編集された News\n".encode("utf-8")
    output.write_bytes(original)
    temporary_path = tmp_path / ".index.md.partial"
    _install_save_failure(monkeypatch, output, temporary_path, "close")

    with patch.object(
        sys, "argv", ["fetch_ai_news.py", "--output", str(output), "--force"]
    ), patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        fetch_ai_news.main()

    assert output.read_bytes() == original
    assert not temporary_path.exists()
    assert "保存に失敗しました" in capsys.readouterr().err


def test_main_preserves_existing_bytes_when_forced_publish_fails(
    tmp_path, capsys
):
    output = tmp_path / "index.md"
    original = "手動編集された News\n".encode("utf-8")
    output.write_bytes(original)

    with patch.object(
        sys, "argv", ["fetch_ai_news.py", "--output", str(output), "--force"]
    ), patch("fetch_ai_news.build_markdown", return_value="新しい News\n"), \
            patch.object(fetch_ai_news.os, "replace", side_effect=OSError(5, "Input/output error")):
        fetch_ai_news.main()

    assert output.read_bytes() == original
    assert not list(tmp_path.glob(".index.md.*.tmp"))
    assert "保存に失敗しました" in capsys.readouterr().err


def test_main_overwrites_existing_output_with_force(tmp_path):
    output = tmp_path / "index.md"
    output.write_text("手動編集")
    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output), "--force"]), \
            patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        fetch_ai_news.main()
    assert output.read_text() == "新しい News\n"


def test_main_saves_complete_output_and_cleans_up_temporary_files(tmp_path):
    output = tmp_path / "index.md"
    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output)]), \
            patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        fetch_ai_news.main()
    assert output.read_text() == "新しい News\n"
    assert not list(tmp_path.glob(".index.md.*.tmp"))


def test_main_preserves_output_created_during_fetch(tmp_path, capsys):
    output = tmp_path / "index.md"

    def generate_news(*args):
        output.write_text("別実行の News\n")
        return "上書きしてはいけない News\n"

    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output)]), \
            patch("fetch_ai_news.build_markdown", side_effect=generate_news):
        fetch_ai_news.main()
    assert output.read_text() == "別実行の News\n"
    assert "[WARN]" in capsys.readouterr().err


def _entry(title, url, count):
    return {"title": title, "url": url, "tags": [], "bookmark_count": count}


def test_hb_section_uses_word_boundary_filter():
    entries = [
        _entry("Explain the maintainers tradeoffs", "https://example.com/1", 30),
        _entry("Digital legacy and legit email", "https://example.com/2", 20),
        _entry("LLMs と AIエージェント", "https://example.com/3", 10),
        _entry("LLMs と AIエージェント", "https://example.com/4", 5),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(1))
    assert "Explain" not in body
    assert "Digital" not in body
    assert body.count("LLMs と AIエージェント") == 1


def test_hb_section_keeps_only_titles_matching_ai_keywords():
    entries = [
        _entry("Claude駆動開発の技術的負債について", "https://example.com/a", 10),
        _entry("Mac用ランチャーアプリの新機能", "https://example.com/b", 20),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert "Claude駆動開発の技術的負債について" in body
    assert "Mac用ランチャーアプリの新機能" not in body


def test_hb_section_removes_duplicate_titles():
    entries = [
        _entry("Claude記事タイトル", "https://a.example.com/1", 10),
        _entry("Claude記事タイトル", "https://b.example.com/1", 5),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert body.count("Claude記事タイトル") == 1


def test_hb_section_escapes_script_in_title():
    entries = [
        _entry('<script>alert(1)</script> Claude記事', "https://example.com/xss", 5),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_hb_section_generates_output_when_source_returns_empty(capsys):
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=[]):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert "該当なし" in body


def _hb_rows(lines):
    return [line for line in lines if line.startswith("| ") and "](" in line]


def test_hb_section_orders_rows_by_bookmark_count():
    entries = [
        _entry("Claude a", "https://example.com/a", 10),
        _entry("Claude b", "https://example.com/b", 143),
        _entry("Claude c", "https://example.com/c", 47),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        rows = _hb_rows(fetch_ai_news.hb_section(10))
    assert rows == [
        "| 1 | [Claude b](https://example.com/b) | 143 |",
        "| 2 | [Claude c](https://example.com/c) | 47 |",
        "| 3 | [Claude a](https://example.com/a) | 10 |",
    ]


def test_hb_section_keeps_source_order_for_same_bookmark_count():
    entries = [
        _entry("Claude first", "https://example.com/1", 20),
        _entry("Claude second", "https://example.com/2", 20),
        _entry("Claude third", "https://example.com/3", 20),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        rows = _hb_rows(fetch_ai_news.hb_section(10))
    assert [r.split("](")[1].split(")")[0] for r in rows] == [
        "https://example.com/1", "https://example.com/2", "https://example.com/3",
    ]


def test_hb_section_takes_top_n_after_sorting():
    entries = [
        _entry("Claude low1", "https://example.com/low1", 1),
        _entry("Claude low2", "https://example.com/low2", 2),
        _entry("Claude high", "https://example.com/high", 100),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(2))
    assert "https://example.com/high" in body
    assert "https://example.com/low2" in body
    assert "https://example.com/low1" not in body


def _write_news(base_dir, date, body):
    path = base_dir / date / "index.md"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")


_NOW = datetime(2026, 11, 4, 7, 0, tzinfo=constants.JST)


def test_hb_section_excludes_urls_listed_in_recent_hb_tables(tmp_path):
    _write_news(tmp_path, "20261103", (
        "---\ntitle: x\n---\n## はてなブックマーク\n\n| # | タイトル | ブックマーク数 |\n|---|---|---|\n"
        "| 1 | [Claude 昨日の記事](https://example.com/old) | 10 |\n"
    ))
    # frontmatter が無い News も読める
    _write_news(tmp_path, "20261028", (
        "## はてなブックマーク\n\n| 1 | [Claude 7 日前の記事 \\(GitHub\\)](https://example.com/a_%28b%29) | 5 |\n"
    ))
    entries = [
        _entry("Claude 昨日の記事", "https://example.com/old", 30),
        _entry("Claude 7 日前の記事 (GitHub)", "https://example.com/a_(b)", 20),
        _entry("Claude 新しい記事", "https://example.com/new", 10),
    ]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(10, fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.HB_HEADING)))
    assert "https://example.com/old" not in body
    assert "7 日前の記事" not in body
    assert "| 1 | [Claude 新しい記事](https://example.com/new) | 10 |" in body


def test_hb_section_fills_limit_after_exclusion(tmp_path):
    _write_news(tmp_path, "20261103", "## はてなブックマーク\n\n| 1 | [Claude 0](https://example.com/0) | 1 |\n")
    entries = [_entry(f"Claude {i}", f"https://example.com/{i}", 1) for i in range(3)]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(2, fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.HB_HEADING)))
    assert "https://example.com/0" not in body
    assert "https://example.com/1" in body
    assert "https://example.com/2" in body


def test_recent_urls_ignores_other_sections_and_old_news(tmp_path):
    _write_news(tmp_path, "20261103", (
        "## はてなブックマーク\n\n| 1 | [Claude](https://example.com/hb) | 1 |\n\n---\n\n"
        "## Qiita\n\n| 1 | [Claude](https://example.com/qiita) |\n"
    ))
    _write_news(tmp_path, "20261027", "## はてなブックマーク\n\n| 1 | [Claude](https://example.com/8days) | 1 |\n")
    _write_news(tmp_path, "20261104", "## はてなブックマーク\n\n| 1 | [Claude](https://example.com/today) | 1 |\n")
    assert fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.HB_HEADING) == {"https://example.com/hb"}


def test_hb_section_outputs_without_past_news(tmp_path):
    entries = [_entry("Claude 記事", "https://example.com/x", 1)]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(10, fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.HB_HEADING)))
    assert "https://example.com/x" in body


def test_hb_section_shows_placeholder_when_all_entries_excluded(tmp_path):
    _write_news(tmp_path, "20261103", "## はてなブックマーク\n\n| 1 | [Claude](https://example.com/x) | 1 |\n")
    entries = [_entry("Claude 記事", "https://example.com/x", 1)]
    with patch("fetch_hb.fetch_entrylist_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(10, fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.HB_HEADING)))
    assert "(該当なし)" in body


# -------------------------
# GitHub Trending / Qiita のセクション
# -------------------------

def _repo(title, description="", stars_today=None):
    return {
        "title": title,
        "url": f"https://github.com/{title}",
        "description": description,
        "stars_today": stars_today,
    }


def test_github_trend_section_renders_repository_table():
    entries = [_repo("awesome/repo", "AI agent toolkit", 1234)]
    with patch("fetch_github_trend.fetch_entries", return_value=entries):
        lines = fetch_ai_news.github_trend_section(10)

    assert lines == [
        "## GitHub Trending",
        "",
        "| # | リポジトリ | Star |",
        "|---|---|---|",
        "| 1 | [awesome/repo](https://github.com/awesome/repo) | 1234 |",
        "",
    ]


def test_github_trend_section_omits_description_column():
    entries = [_repo("awesome/repo", "A | B <script>", 5)]
    with patch("fetch_github_trend.fetch_entries", return_value=entries):
        row = fetch_ai_news.github_trend_section(10)[4]

    assert row == "| 1 | [awesome/repo](https://github.com/awesome/repo) | 5 |"
    assert len(table_cells(row)) == 3


def test_github_trend_section_keeps_columns_without_stars():
    with patch("fetch_github_trend.fetch_entries", return_value=[_repo("awesome/repo")]):
        row = fetch_ai_news.github_trend_section(10)[4]

    assert row == "| 1 | [awesome/repo](https://github.com/awesome/repo) | — |"
    assert len(table_cells(row)) == 3


def table_cells(row):
    return re.split(r"(?<!\\)\|", row)[1:-1]


def test_qiita_section_renders_title_table():
    entries = [{"title": "Claude 記事", "url": "https://qiita.com/example/items/1"}]
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        lines = fetch_ai_news.qiita_section(10)

    assert lines == [
        "## Qiita",
        "",
        "| # | タイトル |",
        "|---|---|",
        "| 1 | [Claude 記事](https://qiita.com/example/items/1) |",
        "",
    ]


def test_qiita_section_filters_by_keywords():
    entries = [
        {"title": "営業こそコミュニティでは No sell", "url": "https://qiita.com/x/items/1"},
        {"title": "Claude 記事", "url": "https://qiita.com/x/items/2"},
    ]
    with patch("fetch_qiita.fetch_entries", return_value=entries) as fetch:
        body = "\n".join(fetch_ai_news.qiita_section(10))

    # 除外してから件数を絞るため、全件を受け取る
    assert fetch.call_args.kwargs["limit"] == 0
    assert "items/1" not in body
    assert "| 1 | [Claude 記事](https://qiita.com/x/items/2) |" in body


def test_qiita_section_excludes_urls_listed_in_recent_qiita_tables(tmp_path):
    utm = "?utm_campaign=popular_items&utm_medium=feed&utm_source=popular_items"
    _write_news(tmp_path, "20261103", (
        "## はてなブックマーク\n\n| 1 | [Claude](https://qiita.com/x/items/hb) | 1 |\n\n---\n\n"
        f"## Qiita\n\n| # | タイトル |\n|---|---|\n| 1 | [Claude 昨日](https://qiita.com/x/items/old{utm}) |\n"
    ))
    _write_news(tmp_path, "20261028", "## Qiita\n\n| 1 | [Claude 7 日前](https://qiita.com/x/items/7days) |\n")
    _write_news(tmp_path, "20261027", "## Qiita\n\n| 1 | [Claude 8 日前](https://qiita.com/x/items/8days) |\n")
    entries = [
        {"title": "Claude 昨日", "url": "https://qiita.com/x/items/old"},
        {"title": "Claude 7 日前", "url": "https://qiita.com/x/items/7days"},
        {"title": "Claude 8 日前", "url": "https://qiita.com/x/items/8days"},
        {"title": "Claude はてなにも載った", "url": "https://qiita.com/x/items/hb"},
        {"title": "Claude 新しい", "url": "https://qiita.com/x/items/new"},
    ]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.QIITA_HEADING)
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.qiita_section(10, excluded))

    assert "items/old" not in body
    assert "items/7days" not in body
    assert "| 1 | [Claude 8 日前](https://qiita.com/x/items/8days) |" in body
    assert "| 2 | [Claude はてなにも載った](https://qiita.com/x/items/hb) |" in body
    assert "| 3 | [Claude 新しい](https://qiita.com/x/items/new) |" in body


def test_qiita_section_fills_limit_after_exclusion(tmp_path):
    _write_news(tmp_path, "20261103", "## Qiita\n\n| 1 | [Claude 0](https://qiita.com/x/0) |\n")
    entries = [{"title": f"Claude {i}", "url": f"https://qiita.com/x/{i}"} for i in range(3)]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.QIITA_HEADING)
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.qiita_section(2, excluded))

    assert "https://qiita.com/x/0" not in body
    assert "https://qiita.com/x/1" in body
    assert "https://qiita.com/x/2" in body


def test_qiita_section_shows_placeholder_when_all_entries_excluded(tmp_path):
    _write_news(tmp_path, "20261103", "## Qiita\n\n| 1 | [Claude](https://qiita.com/x/1) |\n")
    entries = [{"title": "Claude 記事", "url": "https://qiita.com/x/1"}]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.QIITA_HEADING)
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        lines = fetch_ai_news.qiita_section(10, excluded)

    assert "| — | (該当なし) |" in lines


def _zenn(title, url, liked_count=1):
    return {"title": title, "url": url, "liked_count": liked_count}


def test_zenn_section_renders_title_and_likes_table():
    entries = [_zenn("AI 記事", "https://zenn.dev/example/articles/1", 120)]
    with patch("fetch_zenn.fetch_entries", return_value=entries):
        lines = fetch_ai_news.zenn_section(10)

    assert lines == [
        "## Zenn",
        "",
        "| # | タイトル | いいね |",
        "|---|---|---|",
        "| 1 | [AI 記事](https://zenn.dev/example/articles/1) | 120 |",
        "",
    ]


def test_zenn_section_shows_placeholder_when_source_returns_empty():
    with patch("fetch_zenn.fetch_entries", return_value=[]):
        lines = fetch_ai_news.zenn_section(10)

    assert "| — | (取得できませんでした) | — |" in lines


def test_zenn_section_excludes_urls_listed_in_recent_zenn_tables(tmp_path):
    _write_news(tmp_path, "20261103", (
        "## はてなブックマーク\n\n| 1 | [Claude](https://zenn.dev/x/articles/hb) | 1 |\n\n---\n\n"
        "## Zenn\n\n| # | タイトル |\n|---|---|\n| 1 | [Claude 昨日](https://zenn.dev/x/articles/old) |\n"
    ))
    _write_news(tmp_path, "20261028", "## Zenn\n\n| 1 | [Claude 7 日前](https://zenn.dev/x/articles/7days) | 3 |\n")
    _write_news(tmp_path, "20261027", "## Zenn\n\n| 1 | [Claude 8 日前](https://zenn.dev/x/articles/8days) | 3 |\n")
    entries = [
        _zenn("Claude 昨日", "https://zenn.dev/x/articles/old", 50),
        _zenn("Claude 7 日前", "https://zenn.dev/x/articles/7days", 40),
        _zenn("Claude 8 日前", "https://zenn.dev/x/articles/8days", 30),
        _zenn("Claude はてなにも載った", "https://zenn.dev/x/articles/hb", 20),
        _zenn("Claude 新しい", "https://zenn.dev/x/articles/new", 10),
    ]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.ZENN_HEADING)
    with patch("fetch_zenn.fetch_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.zenn_section(10, excluded))

    assert "articles/old" not in body
    assert "articles/7days" not in body
    assert "| 1 | [Claude 8 日前](https://zenn.dev/x/articles/8days) | 30 |" in body
    assert "| 2 | [Claude はてなにも載った](https://zenn.dev/x/articles/hb) | 20 |" in body
    assert "| 3 | [Claude 新しい](https://zenn.dev/x/articles/new) | 10 |" in body


def test_zenn_section_fills_limit_after_exclusion(tmp_path):
    _write_news(tmp_path, "20261103", "## Zenn\n\n| 1 | [Claude 0](https://zenn.dev/x/0) | 1 |\n")
    entries = [_zenn(f"Claude {i}", f"https://zenn.dev/x/{i}") for i in range(3)]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.ZENN_HEADING)
    with patch("fetch_zenn.fetch_entries", return_value=entries) as fetch:
        body = "\n".join(fetch_ai_news.zenn_section(2, excluded))

    # 除外してから件数を絞るため、全件を受け取る
    assert fetch.call_args.kwargs["limit"] == 0
    assert "https://zenn.dev/x/0" not in body
    assert "https://zenn.dev/x/1" in body
    assert "https://zenn.dev/x/2" in body


def test_qiita_section_shows_placeholder_when_source_returns_empty():
    with patch("fetch_qiita.fetch_entries", return_value=[]):
        lines = fetch_ai_news.qiita_section(10)

    assert "| — | (該当なし) |" in lines


def test_zenn_section_escapes_script_in_title():
    entries = [_zenn("<script>alert(1)</script>", "https://zenn.dev/x")]
    with patch("fetch_zenn.fetch_entries", return_value=entries):
        lines = fetch_ai_news.zenn_section(10)

    body = "\n".join(lines)
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def _build_markdown_with_empty_sources(limit: int) -> str:
    source_functions = [
        "fetch_hb.fetch_entrylist_tag_entries",
        "fetch_hn.fetch_hits_or_none",
        "fetch_hn.filter_by_keywords",
        "fetch_github_trend.fetch_entries",
        "fetch_qiita.fetch_entries",
        "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_reddit.fetch_top_posts_ranked", return_value=[]))
        return fetch_ai_news.build_markdown(
            limit, "day", datetime(2026, 8, 20, tzinfo=fetch_ai_news.JST)
        )


def test_sections_use_service_name_as_heading():
    markdown = _build_markdown_with_empty_sources(10)

    assert "description:" not in markdown
    headings = {line for line in markdown.splitlines() if line.startswith("## ")}
    assert {
        "## はてなブックマーク",
        "## Hacker News",
        "## Reddit",
        "## GitHub Trending",
        "## Qiita",
        "## Zenn",
    } <= headings


def test_sections_are_ordered_hb_zenn_qiita_github_hn_reddit():
    markdown = _build_markdown_with_empty_sources(10)

    positions = [
        markdown.index(heading)
        for heading in [
            "## はてなブックマーク",
            "## Zenn",
            "## Qiita",
            "## GitHub Trending",
            "## Hacker News",
            "## Reddit",
        ]
    ]
    assert positions == sorted(positions)


def test_build_markdown_uses_fixed_title_with_weekday():
    # 2026-08-20 は木曜日
    markdown = _build_markdown_with_empty_sources(10)

    assert 'title: "2026 年 08 月 20 日（木）"' in markdown


@pytest.mark.parametrize(
    ("day", "weekday"),
    [(1, "日"), (2, "月"), (3, "火"), (4, "水"), (5, "木"), (6, "金"), (7, "土")],
)
def test_news_title_uses_japanese_weekday(day, weekday):
    now = datetime(2026, 11, day, tzinfo=constants.JST)

    assert fetch_ai_news.news_title(now) == f"2026 年 11 月 {day:02d} 日（{weekday}）"


def test_build_markdown_completes_when_one_source_fails():
    """1 ソースが非 UTF-8 応答を返しても、最後まで完走して他ソースのセクションが残る。"""
    source_functions = [
        "fetch_hn.fetch_hits_or_none",
        "fetch_hn.filter_by_keywords",
        "fetch_github_trend.fetch_entries",
        "fetch_qiita.fetch_entries",
        "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_reddit.fetch_top_posts_ranked", return_value=[]))
        stack.enter_context(patch("fetch_hb._wait_for_crawl_delay"))
        stack.enter_context(patch("fetch_hb.fetch_url", return_value=b"\xff\xfe invalid utf-8"))
        markdown = fetch_ai_news.build_markdown(
            10, "day", datetime(2026, 8, 20, tzinfo=fetch_ai_news.JST)
        )

    assert "## はてなブックマーク" in markdown
    assert "| — | (該当なし) | — |" in markdown
    assert "## Zenn" in markdown


def test_build_markdown_continues_other_feeds_after_invalid_hn_response():
    source_functions = [
        ("fetch_hb.fetch_entrylist_tag_entries", []),
        ("fetch_hn.fetch_url", [b"\xff", b'{"hits": []}']),
        ("fetch_reddit.fetch_top_posts_ranked", []),
        ("fetch_github_trend.fetch_entries", []),
        ("fetch_qiita.fetch_entries", []),
        (
            "fetch_zenn.fetch_entries",
            [{"title": "Claude AI follow up", "url": "https://zenn.dev/example/articles/hn-continued", "liked_count": 1}],
        ),
    ]
    with ExitStack() as stack:
        for function, response in source_functions:
            if function == "fetch_hn.fetch_url":
                stack.enter_context(patch(function, side_effect=response))
            else:
                stack.enter_context(patch(function, return_value=response))
        markdown = fetch_ai_news.build_markdown(
            10, "day", datetime(2026, 8, 20, tzinfo=constants.JST)
        )

    assert "## Zenn" in markdown
    assert "[Claude AI follow up](https://zenn.dev/example/articles/hn-continued)" in markdown


def test_build_markdown_completes_with_empty_reddit_title():
    feed = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><category term="ClaudeCode"/><title/><link href="https://reddit.com/1"/></entry><entry><category term="ClaudeCode"/><title>Next post</title><link href="https://reddit.com/2"/></entry></feed>'
    source_functions = [
        "fetch_hb.fetch_entrylist_tag_entries", "fetch_hn.fetch_hits_or_none",
        "fetch_github_trend.fetch_entries", "fetch_qiita.fetch_entries", "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_reddit.fetch_url", return_value=feed))
        markdown = fetch_ai_news.build_markdown(10, "day", datetime(2026, 10, 3, tzinfo=constants.JST))
    assert "タイトルなし" in markdown
    assert "Next post" in markdown
    assert "## Zenn" in markdown


# -------------------------
# reddit_section
# -------------------------

def _ranked(*rows: tuple[str, int]) -> list[tuple[str, dict]]:
    """(subreddit, 番号) の並びから、fetch_top_posts_ranked の戻り値（フィードの順）を作る。"""
    return [
        (sub, {"title": f"AI post {sub} {i}", "url": f"https://reddit.com/{sub}/{i}"})
        for sub, i in rows
    ]


def _reddit_urls(lines: list[str]) -> list[str]:
    return re.findall(r"\]\((https://reddit\.com/[^)]+)\) \|", "\n".join(lines))


def _ranked_round_robin(count: int) -> list[tuple[str, dict]]:
    return _ranked(*[(sub, i) for i in range(1, count + 1) for sub in fetch_ai_news.fetch_reddit.AI_SUBREDDITS])


def test_reddit_section_limits_rows_to_requested_number():
    with patch("fetch_reddit.fetch_top_posts_ranked", return_value=_ranked_round_robin(12)):
        lines = fetch_ai_news.reddit_section(3, "day")

    body = "\n".join(lines)
    assert "| 3 | " in body
    assert "| 4 | " not in body


def test_reddit_section_includes_entries_from_every_subreddit():
    """先頭の subreddit がフィードの上位を占めても、後続の subreddit の記事が載る。"""
    ranked = _ranked(*[("ClaudeCode", i) for i in range(1, 13)], ("LocalLLaMA", 1), ("ChatGPTCoding", 1))
    with patch("fetch_reddit.fetch_top_posts_ranked", return_value=ranked):
        lines = fetch_ai_news.reddit_section(6, "day")

    body = "\n".join(lines)
    assert "| # | タイトル |" in body
    for subreddit in fetch_ai_news.fetch_reddit.AI_SUBREDDITS:
        assert f"](https://reddit.com/{subreddit}/1) |" in body


def test_reddit_section_keeps_top_two_of_each_subreddit_and_fills_rest_in_feed_order():
    ranked = _ranked(
        ("ClaudeCode", 1), ("ClaudeCode", 2), ("ClaudeCode", 3), ("LocalLLaMA", 1),
        ("ClaudeCode", 4), ("ClaudeCode", 5), ("LocalLLaMA", 2), ("ClaudeCode", 6),
        ("LocalLLaMA", 3), ("ChatGPTCoding", 1), ("ChatGPTCoding", 2), ("ClaudeCode", 7),
    )
    with patch("fetch_reddit.fetch_top_posts_ranked", return_value=ranked):
        lines = fetch_ai_news.reddit_section(8, "day")

    # 各サブレディットの上位 2 件（6 件）を確保し、残り 2 枠はフィードの順で ClaudeCode 3・4 が入る。
    # 表はフィードの順に並ぶ
    assert _reddit_urls(lines) == [
        f"https://reddit.com/{sub}/{i}"
        for sub, i in [
            ("ClaudeCode", 1), ("ClaudeCode", 2), ("ClaudeCode", 3), ("LocalLLaMA", 1),
            ("ClaudeCode", 4), ("LocalLLaMA", 2), ("ChatGPTCoding", 1), ("ChatGPTCoding", 2),
        ]
    ]


def test_reddit_section_fills_up_to_limit_when_a_subreddit_has_few_posts():
    ranked = _ranked(
        ("ClaudeCode", 1), ("LocalLLaMA", 1), ("ClaudeCode", 2), ("ClaudeCode", 3),
        ("LocalLLaMA", 2), ("ClaudeCode", 4), ("LocalLLaMA", 3), ("ChatGPTCoding", 1),
        ("ClaudeCode", 5), ("LocalLLaMA", 4), ("ClaudeCode", 6),
    )
    with patch("fetch_reddit.fetch_top_posts_ranked", return_value=ranked):
        lines = fetch_ai_news.reddit_section(10, "day")

    urls = _reddit_urls(lines)
    assert len(urls) == 10
    assert "https://reddit.com/ChatGPTCoding/1" in urls
    # 選ばれなかったのは、フィードの最後の 1 件だけ
    assert "https://reddit.com/ClaudeCode/6" not in urls


def test_reddit_section_prefers_first_post_of_every_subreddit_when_limit_is_small():
    ranked = _ranked(
        ("ClaudeCode", 1), ("ClaudeCode", 2), ("LocalLLaMA", 1), ("LocalLLaMA", 2), ("ChatGPTCoding", 1),
    )
    with patch("fetch_reddit.fetch_top_posts_ranked", return_value=ranked):
        lines = fetch_ai_news.reddit_section(3, "day")

    assert _reddit_urls(lines) == [
        "https://reddit.com/ClaudeCode/1", "https://reddit.com/LocalLLaMA/1", "https://reddit.com/ChatGPTCoding/1",
    ]


def test_reddit_section_lists_developer_subreddits_and_excludes_media_and_crossposts():
    media = "&lt;a href=&quot;https://i.redd.it/a.png&quot;&gt;[link]&lt;/a&gt;"
    feed = (
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        f'<entry><category term="ClaudeCode"/><title>Meme</title><content type="html">{media}</content>'
        '<link href="https://reddit.com/1"/></entry>'
        '<entry><category term="ClaudeCode"/><title>Same title</title><link href="https://reddit.com/2"/></entry>'
        '<entry><category term="LocalLLaMA"/><title>Same title</title><link href="https://reddit.com/3"/></entry>'
        '<entry><category term="ChatGPTCoding"/><title>Coding post</title><link href="https://reddit.com/4"/></entry>'
        '</feed>'
    ).encode()
    with patch("fetch_reddit.fetch_url", return_value=feed):
        body = "\n".join(fetch_ai_news.reddit_section(10, "day"))

    assert "*対象: r/ClaudeCode, r/LocalLLaMA, r/ChatGPTCoding（スコア順。各サブレディットから 2 件以上）*" in body
    assert "Meme" not in body
    assert body.count("Same title") == 1
    assert "| 2 | [Coding post](https://reddit.com/4) |" in body


# -------------------------
# タイムゾーン
# -------------------------

def test_main_uses_jst_timestamp_under_non_jst_timezone(
    tmp_path, monkeypatch, local_timezone
):
    monkeypatch.setattr(fetch_ai_news, "BASE_DIR", str(tmp_path))
    captured = {}

    def fake_build_markdown(limit, period, now):
        captured["now"] = now
        return "# dummy\n"

    with local_timezone("UTC"), \
            patch.object(sys, "argv", ["fetch_ai_news.py"]), \
            patch("fetch_ai_news.build_markdown", side_effect=fake_build_markdown):
        fetch_ai_news.main()

    # ローカル TZ が UTC でも JST 基準の時刻・出力先になる（naive datetime なら utcoffset() は None）
    assert captured["now"].utcoffset() == timedelta(hours=9)
    assert (tmp_path / datetime.now(constants.JST).strftime("%Y%m%d") / "index.md").exists()



def test_github_trend_section_renders_repository_links():
    html = b"""<html><body>
    <article class="Box-row"><h2><a href="/example/chair">example / chair</a></h2>
      <p class="col-9">Furniture</p></article>
    <article class="Box-row"><h2><a href="/example/tool">example / tool</a></h2>
      <p class="col-9">LLM assistant</p><span><svg></svg> 1,234 stars today</span></article>
    <article class="Box-row"><h2><a href="/example/agent">example / agent</a></h2>
      <p class="col-9">AI agents</p></article>
    </body></html>"""
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = html
    with patch("constants.urllib.request.urlopen", return_value=response):
        lines = fetch_ai_news.github_trend_section(1)
    assert lines == [
        "## GitHub Trending", "", "| # | リポジトリ | Star |", "|---|---|---|",
        "| 1 | [example/tool](https://github.com/example/tool) | 1234 |", "",
    ]


def test_github_trend_section_keeps_empty_result_placeholder():
    with patch("fetch_github_trend.fetch_entries", return_value=[]):
        assert "| — | (取得できませんでした) | — |" in fetch_ai_news.github_trend_section(1)


# -------------------------
# hn_section
# -------------------------

HN_NOW = datetime(2026, 11, 4, 2, 47, tzinfo=constants.JST)


def test_hn_section_queries_posts_created_24_to_48_hours_before_now():
    with patch("fetch_hn.fetch_url", return_value=b'{"hits": []}') as mock_fetch:
        fetch_ai_news.hn_section(10, HN_NOW)

    since = int((HN_NOW - timedelta(hours=48)).timestamp())
    until = int((HN_NOW - timedelta(hours=24)).timestamp())
    urls = [call.args[0] for call in mock_fetch.call_args_list]
    assert urls == [
        "https://hn.algolia.com/api/v1/search"
        f"?tags={tag}&numericFilters=created_at_i%3E{since}%2Ccreated_at_i%3C%3D{until}&hitsPerPage=50"
        for tag in ["show_hn", "ask_hn"]
    ]


def test_hn_section_describes_target_period():
    with patch("fetch_hn.fetch_hits_or_none", return_value=[]):
        lines = fetch_ai_news.hn_section(10, HN_NOW)

    assert "*対象: Show HN + Ask HN の合算ランキング（24 〜 48 時間前の投稿）*" in lines


def test_hn_section_renders_title_and_points_columns():
    hits = [{"title": "Ask HN: How do you use Claude?", "objectID": "1", "points": 10, "num_comments": 2}]
    with patch("fetch_hn.fetch_hits_or_none", side_effect=[[], hits]):
        lines = fetch_ai_news.hn_section(10, HN_NOW)

    assert "| # | タイトル | Points |" in lines
    assert "| 1 | [Ask HN: How do you use Claude?](https://news.ycombinator.com/item?id=1) | 10 |" in lines


def test_hn_section_shows_fetch_failure_when_both_fetches_fail():
    with patch("fetch_hn.fetch_url", return_value=None):
        lines = fetch_ai_news.hn_section(10, HN_NOW)

    assert "| — | (取得できませんでした) | — |" in lines


def test_hn_section_shows_no_match_when_fetch_succeeds_with_no_hits():
    with patch("fetch_hn.fetch_url", return_value=b'{"hits": []}'):
        lines = fetch_ai_news.hn_section(10, HN_NOW)

    assert "| — | (該当なし) | — |" in lines


def test_hn_section_uses_hits_from_successful_fetch_when_other_fails():
    hits = [{"title": "Show HN: My Claude tool", "objectID": "1", "points": 5, "num_comments": 0}]
    with patch("fetch_hn.fetch_hits_or_none", side_effect=[hits, None]):
        lines = fetch_ai_news.hn_section(10, HN_NOW)

    assert "| 1 | [Show HN: My Claude tool](https://news.ycombinator.com/item?id=1) | 5 |" in lines


def test_build_markdown_passes_its_now_to_hn_section():
    now = datetime(2026, 8, 20, tzinfo=constants.JST)
    with patch("fetch_ai_news.hn_section", return_value=[]) as mock_hn, \
         patch("fetch_ai_news.hb_section", return_value=[]), \
         patch("fetch_ai_news.reddit_section", return_value=[]), \
         patch("fetch_ai_news.github_trend_section", return_value=[]), \
         patch("fetch_ai_news.qiita_section", return_value=[]), \
         patch("fetch_ai_news.zenn_section", return_value=[]):
        fetch_ai_news.build_markdown(10, "day", now)

    mock_hn.assert_called_once_with(10, now)
