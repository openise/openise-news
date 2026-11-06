#!/usr/bin/env python3
"""fetch_ai_news.py のセクション生成テスト"""
import re
import json
import runpy
import sys
import pytest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import constants
import fetch_ai_news


@pytest.fixture(autouse=True)
def qiita_likes(monkeypatch):
    """既定では Qiita API を呼ばず、いいね数なしとして扱う。テストでは likes に URL → いいね数を入れる。"""
    likes = {}
    calls = []

    def fake(url, token=""):
        calls.append((url, token))
        return likes.get(url)

    monkeypatch.setattr(fetch_ai_news.fetch_qiita, "fetch_likes_count", fake)
    return SimpleNamespace(likes=likes, calls=calls)


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
        assert fetch_ai_news.main() == 0
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
            return len(content)

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
        assert fetch_ai_news.main() == 1

    assert output.read_bytes() == original
    assert not temporary_path.exists()
    assert "保存に失敗しました" in capsys.readouterr().err


@pytest.mark.parametrize("failure_stage", ["write", "close"])
def test_main_does_not_publish_partial_new_output_on_io_failure(
    tmp_path, monkeypatch, capsys, failure_stage
):
    output = tmp_path / "index.md"
    temporary_path = tmp_path / ".index.md.partial"
    _install_save_failure(monkeypatch, output, temporary_path, failure_stage)

    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output)]), \
            patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        assert fetch_ai_news.main() == 1

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
        assert fetch_ai_news.main() == 1

    assert output.read_bytes() == original
    assert not temporary_path.exists()
    assert "保存に失敗しました" in capsys.readouterr().err


@pytest.mark.parametrize("force", [False, True])
def test_main_preserves_output_when_publish_fails(
    tmp_path, capsys, force
):
    output = tmp_path / "index.md"
    original = "手動編集された News\n".encode("utf-8")
    if force:
        output.write_bytes(original)

    with patch.object(
        sys, "argv", ["fetch_ai_news.py", "--output", str(output)] + (["--force"] if force else [])
    ), patch("fetch_ai_news.build_markdown", return_value="新しい News\n"), \
            patch.object(fetch_ai_news.os, "replace" if force else "link", side_effect=OSError(5, "Input/output error")):
        assert fetch_ai_news.main() == 1

    if force:
        assert output.read_bytes() == original
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".index.md.*.tmp"))
    assert "保存に失敗しました" in capsys.readouterr().err


def test_main_overwrites_existing_output_with_force(tmp_path):
    output = tmp_path / "index.md"
    output.write_text("手動編集")
    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output), "--force"]), \
            patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        assert fetch_ai_news.main() == 0
    assert output.read_text() == "新しい News\n"


def test_main_saves_complete_output_and_cleans_up_temporary_files(tmp_path):
    output = tmp_path / "index.md"
    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output)]), \
            patch("fetch_ai_news.build_markdown", return_value="新しい News\n"):
        assert fetch_ai_news.main() == 0
    assert output.read_text() == "新しい News\n"
    assert not list(tmp_path.glob(".index.md.*.tmp"))


def test_main_preserves_output_created_during_fetch(tmp_path, capsys):
    output = tmp_path / "index.md"

    def generate_news(*args):
        output.write_text("別実行の News\n")
        return "上書きしてはいけない News\n"

    with patch.object(sys, "argv", ["fetch_ai_news.py", "--output", str(output)]), \
            patch("fetch_ai_news.build_markdown", side_effect=generate_news):
        assert fetch_ai_news.main() == 0
    assert output.read_text() == "別実行の News\n"
    assert "[WARN]" in capsys.readouterr().err


@pytest.mark.parametrize("fails", [False, True])
def test_cli_exits_with_status_for_existing_file_or_directory_creation_failure(tmp_path, fails, capsys):
    output = tmp_path / "index.md"
    output.write_text("既存の News\n", encoding="utf-8")
    argv = ["fetch_ai_news.py"] if fails else ["fetch_ai_news.py", "--output", str(output)]
    with patch.object(sys, "argv", argv), \
            patch("os.makedirs", side_effect=OSError("保存先を作れません")), \
            pytest.raises(SystemExit) as exc:
        runpy.run_path(fetch_ai_news.__file__, run_name="__main__")

    assert exc.value.code == (1 if fails else 0)
    assert output.read_text(encoding="utf-8") == "既存の News\n"
    stderr = capsys.readouterr().err
    assert ("[ERROR] 保存に失敗しました" if fails else "[WARN]") in stderr


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


def test_qiita_section_renders_likes_table(qiita_likes):
    entries = [{"title": "Claude 記事", "url": "https://qiita.com/example/items/1"}]
    qiita_likes.likes["https://qiita.com/example/items/1"] = 42
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        lines = fetch_ai_news.qiita_section(10)

    assert lines == [
        "## Qiita",
        "",
        "| # | タイトル | いいね |",
        "|---|---|---|",
        "| 1 | [Claude 記事](https://qiita.com/example/items/1) | 42 |",
        "",
    ]


def test_qiita_section_sorts_by_likes_and_puts_unknown_last(qiita_likes):
    urls = [f"https://qiita.com/x/items/{i}" for i in range(5)]
    entries = [{"title": f"Claude {i}", "url": u} for i, u in enumerate(urls)]
    # 0: 取れない、1: 5、2: 20、3: 5、4: 取れない
    qiita_likes.likes.update({urls[1]: 5, urls[2]: 20, urls[3]: 5})
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        lines = fetch_ai_news.qiita_section(10)

    rows = [line for line in lines if re.match(r"^\| \d+ \|", line)]
    assert rows == [
        f"| 1 | [Claude 2]({urls[2]}) | 20 |",
        f"| 2 | [Claude 1]({urls[1]}) | 5 |",
        f"| 3 | [Claude 3]({urls[3]}) | 5 |",
        f"| 4 | [Claude 0]({urls[0]}) | — |",
        f"| 5 | [Claude 4]({urls[4]}) | — |",
    ]


def test_qiita_section_ranks_by_likes_before_limit(qiita_likes):
    urls = [f"https://qiita.com/x/items/{i}" for i in range(3)]
    entries = [{"title": f"Claude {i}", "url": u} for i, u in enumerate(urls)]
    qiita_likes.likes.update({urls[0]: 1, urls[1]: 2, urls[2]: 3})
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.qiita_section(2))

    assert f"| 1 | [Claude 2]({urls[2]}) | 3 |" in body
    assert f"| 2 | [Claude 1]({urls[1]}) | 2 |" in body
    assert urls[0] not in body


def test_qiita_section_fetches_likes_only_for_filtered_entries(tmp_path, qiita_likes, monkeypatch):
    monkeypatch.setenv("QIITA_ACCESS_TOKEN", "qiita-token")
    _write_news(tmp_path, "20261103", "## Qiita\n\n| 1 | [Claude 昨日](https://qiita.com/x/items/old) |\n")
    entries = [
        {"title": "営業の話", "url": "https://qiita.com/x/items/sales"},
        {"title": "Claude 昨日", "url": "https://qiita.com/x/items/old"},
        {"title": "Claude 新しい", "url": "https://qiita.com/x/items/new"},
    ]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.QIITA_HEADING)
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        fetch_ai_news.qiita_section(10, excluded)

    assert qiita_likes.calls == [("https://qiita.com/x/items/new", "qiita-token")]


def test_qiita_section_passes_empty_token_without_env(qiita_likes, monkeypatch):
    monkeypatch.delenv("QIITA_ACCESS_TOKEN", raising=False)
    entries = [{"title": "Claude 記事", "url": "https://qiita.com/x/items/1"}]
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        fetch_ai_news.qiita_section(10)

    assert qiita_likes.calls == [("https://qiita.com/x/items/1", "")]


def test_qiita_section_excludes_urls_in_recent_three_column_tables(tmp_path):
    _write_news(tmp_path, "20261103", (
        "## Qiita\n\n| # | タイトル | いいね |\n|---|---|---|\n"
        "| 1 | [Claude 昨日](https://qiita.com/x/items/old) | 12 |\n"
        "| 2 | [Claude 不明](https://qiita.com/x/items/unknown) | — |\n"
    ))
    entries = [
        {"title": "Claude 昨日", "url": "https://qiita.com/x/items/old"},
        {"title": "Claude 不明", "url": "https://qiita.com/x/items/unknown"},
        {"title": "Claude 新しい", "url": "https://qiita.com/x/items/new"},
    ]
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.QIITA_HEADING)
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.qiita_section(10, excluded))

    assert "items/old" not in body
    assert "items/unknown" not in body
    assert "| 1 | [Claude 新しい](https://qiita.com/x/items/new) | — |" in body


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

    assert "| — | (該当なし) | — |" in lines


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

    assert "| — | (該当なし) | — |" in lines


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


def test_hn_section_skips_invalid_articles_before_filtering_and_ranking(capsys):
    hits = [
        {"title": "Claude invalid points", "objectID": "bad", "points": "42"},
        {"title": ["Claude invalid title"], "objectID": "bad-title"},
        {"title": "Claude lower comments", "objectID": "1", "points": 42, "num_comments": 1},
        {"title": "Claude highest", "objectID": "2", "points": 43, "num_comments": None},
        {"title": "Claude higher comments", "objectID": "3", "points": 42, "num_comments": 2},
    ]
    with patch("fetch_hn.fetch_url", side_effect=[json.dumps({"hits": hits}).encode(), b'{"hits": []}']):
        rows = [line for line in fetch_ai_news.hn_section(10, _NOW) if line.startswith("| ")][1:]

    assert rows == [
        "| 1 | [Claude highest](https://news.ycombinator.com/item?id=2) | 43 |",
        "| 2 | [Claude higher comments](https://news.ycombinator.com/item?id=3) | 42 |",
        "| 3 | [Claude lower comments](https://news.ycombinator.com/item?id=1) | 42 |",
    ]
    assert capsys.readouterr().err.count("[WARN] Hacker News") == 2


def test_build_markdown_continues_after_non_utf8_github_trending_response(capsys):
    with ExitStack() as stack:
        for function in [
            "fetch_hb.fetch_entrylist_tag_entries", "fetch_hn.fetch_hits_or_none",
            "fetch_reddit.fetch_top_posts_ranked", "fetch_qiita.fetch_entries",
        ]:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_github_trend.fetch_url", return_value=b"\xff"))
        stack.enter_context(patch("fetch_zenn.fetch_entries", return_value=[{
            "title": "Claude AI follow up", "url": "https://zenn.dev/example/articles/continued", "liked_count": 1,
        }]))
        markdown = fetch_ai_news.build_markdown(10, "day", _NOW)

    assert "## GitHub Trending\n\n| # | リポジトリ | Star |\n|---|---|---|\n| — | (取得できませんでした) | — |" in markdown
    assert "[Claude AI follow up](https://zenn.dev/example/articles/continued)" in markdown
    assert "[WARN] GitHub Trend: response の decode 失敗" in capsys.readouterr().err


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

def _ranked(*rows: tuple[str, int]) -> list[tuple[str, int, dict]]:
    """(subreddit, 番号) の並びから、fetch_top_posts_ranked の戻り値（フィードの順、順位は 1 始まりの位置）を作る。"""
    return [
        (sub, feed_rank, {"title": f"AI post {sub} {i}", "url": f"https://reddit.com/{sub}/{i}"})
        for feed_rank, (sub, i) in enumerate(rows, 1)
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
    assert "| # | タイトル | 順位 |" in body
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

    assert "対象:" not in body
    assert "Meme" not in body
    assert body.count("Same title") == 1
    assert "| 2 | [Coding post](https://reddit.com/4) |" in body


def test_reddit_section_shows_feed_rank_before_exclusion():
    media = "&lt;a href=&quot;https://i.redd.it/a.png&quot;&gt;[link]&lt;/a&gt;"
    feed = (
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<entry><category term="ClaudeCode"/><title>First</title><link href="https://reddit.com/1"/></entry>'
        f'<entry><category term="ClaudeCode"/><title>Meme</title><content type="html">{media}</content>'
        '<link href="https://reddit.com/2"/></entry>'
        '<entry><category term="Other"/><title>Other sub</title><link href="https://reddit.com/3"/></entry>'
        '<entry><category term="LocalLLaMA"/><title>Fourth</title><link href="https://reddit.com/4"/></entry>'
        '</feed>'
    ).encode()
    with patch("fetch_reddit.fetch_url", return_value=feed):
        lines = fetch_ai_news.reddit_section(10, "day")

    # 除いた画像の投稿・対象外のサブレディットの投稿も数えるので、順位は詰まらない
    assert "| # | タイトル | 順位 |" in lines
    assert "| 1 | [First](https://reddit.com/1) | 1 |" in lines
    assert "| 2 | [Fourth](https://reddit.com/4) | 4 |" in lines


def test_reddit_section_keeps_three_columns_when_fetch_fails():
    with patch("fetch_reddit.fetch_url", return_value=None):
        lines = fetch_ai_news.reddit_section(10, "day")

    assert "| — | (取得できませんでした) | — |" in lines

def _reddit_feed(*rows: tuple[str, int]) -> bytes:
    """(subreddit, 番号) の並びから、統合 URL の応答を模した Atom feed を作る（並び順がスコア順）。"""
    entries = "".join(
        f'<entry><category term="{sub}"/><title>AI post {sub} {i}</title>'
        f'<link href="https://reddit.com/{sub}/{i}"/></entry>'
        for sub, i in rows
    )
    return f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'.encode()


def test_reddit_section_excludes_urls_listed_in_recent_reddit_tables_and_keeps_minimum(tmp_path):
    _write_news(tmp_path, "20261103", (
        "## Hacker News\n\n| 1 | [Other](https://reddit.com/ChatGPTCoding/2) | 1 |\n\n---\n\n"
        "## Reddit\n\n| # | タイトル |\n|---|---|\n"
        "| 1 | [AI post ClaudeCode 1](https://reddit.com/ClaudeCode/1) |\n"
    ))
    _write_news(tmp_path, "20261028", "## Reddit\n\n| 1 | [AI post LocalLLaMA 2](https://reddit.com/LocalLLaMA/2) |\n")
    feed = _reddit_feed(
        ("ClaudeCode", 1), ("ClaudeCode", 2), ("ClaudeCode", 3), ("LocalLLaMA", 1),
        ("LocalLLaMA", 2), ("LocalLLaMA", 3), ("ChatGPTCoding", 1), ("ChatGPTCoding", 2),
    )
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.REDDIT_HEADING)
    with patch("fetch_reddit.fetch_url", return_value=feed):
        lines = fetch_ai_news.reddit_section(6, "day", excluded)

    # 除いた ClaudeCode 1・LocalLLaMA 2 の代わりに各サブレディットの次の投稿で 2 件ずつ確保する。
    # Hacker News の表にだけある ChatGPTCoding 2 は除かない
    assert _reddit_urls(lines) == [
        f"https://reddit.com/{sub}/{i}"
        for sub, i in [
            ("ClaudeCode", 2), ("ClaudeCode", 3), ("LocalLLaMA", 1),
            ("LocalLLaMA", 3), ("ChatGPTCoding", 1), ("ChatGPTCoding", 2),
        ]
    ]


def test_reddit_section_excludes_before_capping_each_subreddit_at_limit(tmp_path):
    _write_news(tmp_path, "20261103", (
        "## Reddit\n\n| 1 | [a](https://reddit.com/ClaudeCode/1) |\n| 2 | [b](https://reddit.com/ClaudeCode/2) |\n"
    ))
    feed = _reddit_feed(("ClaudeCode", 1), ("ClaudeCode", 2), ("ClaudeCode", 3), ("LocalLLaMA", 1), ("ChatGPTCoding", 1))
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.REDDIT_HEADING)
    with patch("fetch_reddit.fetch_url", return_value=feed):
        lines = fetch_ai_news.reddit_section(2, "day", excluded)

    # 取得側で ClaudeCode を limit(2) 件で打ち切ってから除くと、ClaudeCode が 1 件も載らなくなる
    assert _reddit_urls(lines) == ["https://reddit.com/ClaudeCode/3", "https://reddit.com/LocalLLaMA/1"]


def test_reddit_section_outputs_without_past_news(tmp_path):
    feed = _reddit_feed(("ClaudeCode", 1), ("LocalLLaMA", 1))
    excluded = fetch_ai_news.recent_urls(_NOW, str(tmp_path), fetch_ai_news.REDDIT_HEADING)
    with patch("fetch_reddit.fetch_url", return_value=feed):
        lines = fetch_ai_news.reddit_section(10, "day", excluded)

    assert _reddit_urls(lines) == ["https://reddit.com/ClaudeCode/1", "https://reddit.com/LocalLLaMA/1"]


def test_build_markdown_excludes_reddit_posts_in_previous_news(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_ai_news, "BASE_DIR", str(tmp_path))
    _write_news(tmp_path, "20261103", "## Reddit\n\n| 1 | [a](https://reddit.com/ClaudeCode/1) |\n")
    source_functions = [
        "fetch_hb.fetch_entrylist_tag_entries", "fetch_hn.fetch_hits_or_none",
        "fetch_github_trend.fetch_entries", "fetch_qiita.fetch_entries", "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_reddit.fetch_url", return_value=_reddit_feed(("ClaudeCode", 1), ("ClaudeCode", 2))))
        markdown = fetch_ai_news.build_markdown(10, "day", _NOW)

    assert "https://reddit.com/ClaudeCode/1" not in markdown
    assert "https://reddit.com/ClaudeCode/2" in markdown


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


def _hn_query_range(now: datetime) -> tuple[int, int]:
    """hn_section が Algolia に渡す numericFilters の (since, until) を返す。"""
    with patch("fetch_hn.fetch_url", return_value=b'{"hits": []}') as mock_fetch:
        fetch_ai_news.hn_section(10, now)
    ranges = {
        tuple(int(v) for v in re.search(r"created_at_i%3E(\d+)%2Ccreated_at_i%3C%3D(\d+)", call.args[0]).groups())
        for call in mock_fetch.call_args_list
    }
    assert len(ranges) == 1
    return ranges.pop()


def test_hn_section_queries_posts_created_from_two_days_before_to_previous_day():
    with patch("fetch_hn.fetch_url", return_value=b'{"hits": []}') as mock_fetch:
        fetch_ai_news.hn_section(10, HN_NOW)

    # 11/04 の News は 11/02 0:00 以上・11/03 0:00 未満（JST）の投稿。API の条件は「since より後・until 以下」
    start = int(datetime(2026, 11, 2, tzinfo=constants.JST).timestamp())
    end = int(datetime(2026, 11, 3, tzinfo=constants.JST).timestamp())
    since, until = start - 1, end - 1
    urls = [call.args[0] for call in mock_fetch.call_args_list]
    assert urls == [
        "https://hn.algolia.com/api/v1/search"
        f"?tags={tag}&numericFilters=created_at_i%3E{since}%2Ccreated_at_i%3C%3D{until}&hitsPerPage=50"
        for tag in ["show_hn", "ask_hn"]
    ]


@pytest.mark.parametrize("hour, minute", [(0, 0), (0, 47), (14, 22), (23, 59)])
def test_hn_section_query_range_does_not_depend_on_time_of_day(hour, minute):
    now = datetime(2026, 11, 4, hour, minute, tzinfo=constants.JST)
    assert _hn_query_range(now) == _hn_query_range(HN_NOW)


def test_hn_section_query_range_uses_jst_date_for_non_jst_now():
    # 11/03 16:00 UTC は 11/04 1:00 JST なので、11/04 の News と同じ範囲になる
    now = datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc)
    assert _hn_query_range(now) == _hn_query_range(HN_NOW)


# 前日より遅く取得するとすき間が、早く取得すると重なりができていた時刻の組み合わせ
@pytest.mark.parametrize("previous, current", [
    (datetime(2026, 11, 3, 18, 1, tzinfo=constants.JST), datetime(2026, 11, 4, 23, 39, tzinfo=constants.JST)),
    (datetime(2026, 11, 3, 23, 39, tzinfo=constants.JST), datetime(2026, 11, 4, 14, 22, tzinfo=constants.JST)),
])
def test_hn_section_query_ranges_of_consecutive_days_are_contiguous(previous, current):
    _, until_previous = _hn_query_range(previous)
    since_current, _ = _hn_query_range(current)
    # 前日の範囲は until 以下、当日の範囲は since より後なので、同じ値ならすき間も重なりもない
    assert since_current == until_previous


def test_hn_section_has_no_target_line():
    # 取得範囲は About ページで説明するため、表の上には書かない
    with patch("fetch_hn.fetch_hits_or_none", return_value=[]):
        lines = fetch_ai_news.hn_section(10, HN_NOW)

    assert lines[:2] == ["## Hacker News", ""]
    assert not any("対象:" in line for line in lines)


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


def _hn_hit(object_id: str, points: int) -> dict:
    return {"title": f"Show HN: Claude tool {object_id}", "objectID": object_id, "points": points, "num_comments": 0}


def _hn_urls(lines: list[str]) -> list[str]:
    return re.findall(r"\((https://news\.ycombinator\.com/item\?id=\d+)\)", "\n".join(lines))


def test_hn_section_excludes_urls_listed_in_recent_hn_tables_before_limit(tmp_path):
    _write_news(tmp_path, "20261103", (
        "## Reddit\n\n| 1 | [x](https://news.ycombinator.com/item?id=3) | 1 |\n\n---\n\n"
        "## Hacker News\n\n| # | タイトル | Points |\n|---|---|---|\n"
        "| 1 | [Show HN: Claude tool 1](https://news.ycombinator.com/item?id=1) | 50 |\n"
    ))
    hits = [_hn_hit("1", 100), _hn_hit("2", 90), _hn_hit("3", 80)]
    excluded = fetch_ai_news.recent_urls(HN_NOW, str(tmp_path), fetch_ai_news.HN_HEADING)
    with patch("fetch_hn.fetch_hits_or_none", side_effect=[hits, []]):
        lines = fetch_ai_news.hn_section(2, HN_NOW, excluded)

    # 除いた 1 の代わりに次の順位の 3 が入る。Reddit の表にだけある 3 は除かない
    assert _hn_urls(lines) == ["https://news.ycombinator.com/item?id=2", "https://news.ycombinator.com/item?id=3"]
    assert "| 1 | [Show HN: Claude tool 2](https://news.ycombinator.com/item?id=2) | 90 |" in lines


def test_hn_section_shows_no_match_when_all_hits_excluded():
    with patch("fetch_hn.fetch_hits_or_none", side_effect=[[_hn_hit("1", 10)], []]):
        lines = fetch_ai_news.hn_section(10, HN_NOW, {"https://news.ycombinator.com/item?id=1"})

    assert "| — | (該当なし) | — |" in lines


def test_build_markdown_excludes_hn_posts_in_previous_news(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_ai_news, "BASE_DIR", str(tmp_path))
    _write_news(tmp_path, "20261103", "## Hacker News\n\n| 1 | [a](https://news.ycombinator.com/item?id=1) | 1 |\n")
    source_functions = [
        "fetch_hb.fetch_entrylist_tag_entries", "fetch_github_trend.fetch_entries",
        "fetch_qiita.fetch_entries", "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_reddit.fetch_url", return_value=None))
        stack.enter_context(patch("fetch_hn.fetch_hits_or_none", side_effect=[[_hn_hit("1", 10), _hn_hit("2", 5)], []]))
        markdown = fetch_ai_news.build_markdown(10, "day", _NOW)

    assert "https://news.ycombinator.com/item?id=1" not in markdown
    assert "https://news.ycombinator.com/item?id=2" in markdown


def test_build_markdown_passes_its_now_to_hn_section():
    now = datetime(2026, 8, 20, tzinfo=constants.JST)
    with patch("fetch_ai_news.hn_section", return_value=[]) as mock_hn, \
         patch("fetch_ai_news.hb_section", return_value=[]), \
         patch("fetch_ai_news.reddit_section", return_value=[]), \
         patch("fetch_ai_news.github_trend_section", return_value=[]), \
         patch("fetch_ai_news.qiita_section", return_value=[]), \
         patch("fetch_ai_news.zenn_section", return_value=[]):
        fetch_ai_news.build_markdown(10, "day", now)

    mock_hn.assert_called_once()
    assert mock_hn.call_args.args[:2] == (10, now)
