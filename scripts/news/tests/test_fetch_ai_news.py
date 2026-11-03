#!/usr/bin/env python3
"""fetch_ai_news.py のセクション生成テスト"""
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
    with patch("fetch_hb.fetch_hotentry_tag_entries", return_value=entries):
        body = "\n".join(fetch_ai_news.hb_section(1))
    assert "Explain" not in body
    assert "Digital" not in body
    assert body.count("LLMs と AIエージェント") == 1


def test_hb_section_keeps_only_titles_matching_ai_keywords():
    entries = [
        _entry("AI駆動開発の技術的負債について", "https://example.com/a", 10),
        _entry("Mac用ランチャーアプリの新機能", "https://example.com/b", 20),
    ]
    with patch("fetch_hb.fetch_hotentry_tag_entries", return_value=entries):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert "AI駆動開発の技術的負債について" in body
    assert "Mac用ランチャーアプリの新機能" not in body


def test_hb_section_removes_duplicate_titles():
    entries = [
        _entry("AI記事タイトル", "https://a.example.com/1", 10),
        _entry("AI記事タイトル", "https://b.example.com/1", 5),
    ]
    with patch("fetch_hb.fetch_hotentry_tag_entries", return_value=entries):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert body.count("AI記事タイトル") == 1


def test_hb_section_escapes_script_in_title():
    entries = [
        _entry('<script>alert(1)</script> AI記事', "https://example.com/xss", 5),
    ]
    with patch("fetch_hb.fetch_hotentry_tag_entries", return_value=entries):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_hb_section_generates_output_when_source_returns_empty(capsys):
    with patch("fetch_hb.fetch_hotentry_tag_entries", return_value=[]):
        lines = fetch_ai_news.hb_section(10)

    body = "\n".join(lines)
    assert "該当なし" in body


# -------------------------
# 2 列テーブルのセクション（GitHub Trending / Qiita / Zenn）
# -------------------------

def test_github_trend_section_renders_repository_table():
    entries = [{"title": "awesome/repo", "url": "https://github.com/awesome/repo"}]
    with patch("fetch_github_trend.fetch_entries", return_value=entries):
        lines = fetch_ai_news.github_trend_section(10)

    assert lines == [
        "## GitHub Trending（AI 関連 Top 10）",
        "",
        "| 番号 | リポジトリ |",
        "|---|---|",
        "| 1 | [awesome/repo](https://github.com/awesome/repo) |",
        "",
    ]


def test_qiita_section_renders_title_table():
    entries = [{"title": "AI 記事", "url": "https://qiita.com/example/items/1"}]
    with patch("fetch_qiita.fetch_entries", return_value=entries):
        lines = fetch_ai_news.qiita_section(10)

    assert lines == [
        "## Qiita（AI 関連人気記事 Top 10）",
        "",
        "| 番号 | タイトル |",
        "|---|---|",
        "| 1 | [AI 記事](https://qiita.com/example/items/1) |",
        "",
    ]


def test_zenn_section_renders_title_table():
    entries = [{"title": "AI 記事", "url": "https://zenn.dev/example/articles/1"}]
    with patch("fetch_zenn.fetch_entries", return_value=entries):
        lines = fetch_ai_news.zenn_section(10)

    assert lines == [
        "## Zenn（AI 関連最新記事 Top 10）",
        "",
        "| 番号 | タイトル |",
        "|---|---|",
        "| 1 | [AI 記事](https://zenn.dev/example/articles/1) |",
        "",
    ]


def test_qiita_section_shows_placeholder_when_source_returns_empty():
    with patch("fetch_qiita.fetch_entries", return_value=[]):
        lines = fetch_ai_news.qiita_section(10)

    assert "| — | (取得できませんでした) |" in lines


def test_zenn_section_escapes_script_in_title():
    entries = [{"title": "<script>alert(1)</script>", "url": "https://zenn.dev/x"}]
    with patch("fetch_zenn.fetch_entries", return_value=entries):
        lines = fetch_ai_news.zenn_section(10)

    body = "\n".join(lines)
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def _build_markdown_with_empty_sources(limit: int) -> str:
    source_functions = [
        "fetch_hb.fetch_hotentry_tag_entries",
        "fetch_hn.fetch_hits",
        "fetch_hn.filter_by_keywords",
        "fetch_github_trend.fetch_entries",
        "fetch_qiita.fetch_entries",
        "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch(
            "fetch_reddit.fetch_top_posts_multi",
            return_value={sub: [] for sub in fetch_ai_news.fetch_reddit.AI_SUBREDDITS},
        ))
        return fetch_ai_news.build_markdown(
            limit, "day", datetime(2026, 8, 20, tzinfo=fetch_ai_news.JST)
        )


def test_sections_keep_top_10_heading_for_default_limit():
    markdown = _build_markdown_with_empty_sources(10)

    assert "description:" not in markdown
    for heading in [
        "## はてなブックマーク（AI 関連 Top 10）",
        "## Hacker News（AI 関連 Top 10）",
        "## Reddit（AI 関連 subreddit 別ピックアップ 10 件）",
        "## GitHub Trending（AI 関連 Top 10）",
        "## Qiita（AI 関連人気記事 Top 10）",
        "## Zenn（AI 関連最新記事 Top 10）",
    ]:
        assert heading in markdown


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
        "fetch_hn.fetch_hits",
        "fetch_hn.filter_by_keywords",
        "fetch_github_trend.fetch_entries",
        "fetch_qiita.fetch_entries",
        "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch(
            "fetch_reddit.fetch_top_posts_multi",
            return_value={sub: [] for sub in fetch_ai_news.fetch_reddit.AI_SUBREDDITS},
        ))
        stack.enter_context(patch("fetch_hb._wait_for_crawl_delay"))
        stack.enter_context(patch("fetch_hb.fetch_url", return_value=b"\xff\xfe invalid utf-8"))
        markdown = fetch_ai_news.build_markdown(
            10, "day", datetime(2026, 8, 20, tzinfo=fetch_ai_news.JST)
        )

    assert "## はてなブックマーク（AI 関連 Top 10）" in markdown
    assert "| — | (該当なし) | — |" in markdown
    assert "## Zenn（AI 関連最新記事 Top 10）" in markdown


def test_build_markdown_continues_other_feeds_after_invalid_hn_response():
    source_functions = [
        ("fetch_hb.fetch_hotentry_tag_entries", []),
        ("fetch_hn.fetch_url", [b"\xff", b'{"hits": []}']),
        (
            "fetch_reddit.fetch_top_posts_multi",
            {sub: [] for sub in fetch_ai_news.fetch_reddit.AI_SUBREDDITS},
        ),
        ("fetch_github_trend.fetch_entries", []),
        ("fetch_qiita.fetch_entries", []),
        (
            "fetch_zenn.fetch_entries",
            [{"title": "Claude AI follow up", "url": "https://zenn.dev/example/articles/hn-continued"}],
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

    assert "## Zenn（AI 関連最新記事 Top 10）" in markdown
    assert "[Claude AI follow up](https://zenn.dev/example/articles/hn-continued)" in markdown


def test_build_markdown_completes_with_empty_reddit_title():
    feed = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><category term="ClaudeAI"/><title/><link href="https://reddit.com/1"/></entry><entry><category term="ClaudeAI"/><title>Next post</title><link href="https://reddit.com/2"/></entry></feed>'
    source_functions = [
        "fetch_hb.fetch_hotentry_tag_entries", "fetch_hn.fetch_hits",
        "fetch_github_trend.fetch_entries", "fetch_qiita.fetch_entries", "fetch_zenn.fetch_entries",
    ]
    with ExitStack() as stack:
        for function in source_functions:
            stack.enter_context(patch(function, return_value=[]))
        stack.enter_context(patch("fetch_reddit.fetch_url", return_value=feed))
        markdown = fetch_ai_news.build_markdown(10, "day", datetime(2026, 10, 3, tzinfo=constants.JST))
    assert "タイトルなし" in markdown
    assert "Next post" in markdown
    assert "## Zenn（AI 関連最新記事 Top 10）" in markdown


def test_sections_render_custom_limit_in_heading():
    markdown = _build_markdown_with_empty_sources(5)

    for heading in [
        "## はてなブックマーク（AI 関連 Top 5）",
        "## Hacker News（AI 関連 Top 5）",
        "## Reddit（AI 関連 subreddit 別ピックアップ 5 件）",
        "## GitHub Trending（AI 関連 Top 5）",
        "## Qiita（AI 関連人気記事 Top 5）",
        "## Zenn（AI 関連最新記事 Top 5）",
    ]:
        assert heading in markdown


# -------------------------
# reddit_section
# -------------------------

def _fake_fetch_top_posts_multi(count: int):
    """subreddit ごとに独立した投稿リストを持つ dict を返す stub を作る（統合 URL 取得の模擬）。

    全サブレディットに同じ list を返すと、`p["subreddit"] = sub` の代入で
    共有された dict が上書きされ、どの行がどのサブレディット由来か検証できなくなる。
    """
    def _fetch(subreddits, limit, period):
        return {
            sub: [
                {"title": f"AI post {sub} {i}", "url": f"https://reddit.com/{sub}/{i}"}
                for i in range(1, count + 1)
            ]
            for sub in subreddits
        }

    return _fetch


def test_reddit_section_limits_rows_to_requested_number():
    with patch("fetch_reddit.fetch_top_posts_multi", side_effect=_fake_fetch_top_posts_multi(12)):
        lines = fetch_ai_news.reddit_section(3, "day")

    body = "\n".join(lines)
    assert "| 3 | r/" in body
    assert "| 4 | r/" not in body


def test_reddit_section_heading_states_the_same_count_as_rows():
    with patch("fetch_reddit.fetch_top_posts_multi", side_effect=_fake_fetch_top_posts_multi(12)):
        lines = fetch_ai_news.reddit_section(3, "day")

    assert lines[0] == "## Reddit（AI 関連 subreddit 別ピックアップ 3 件）"


def test_reddit_section_keeps_default_limit_in_heading():
    with patch("fetch_reddit.fetch_top_posts_multi", side_effect=_fake_fetch_top_posts_multi(12)):
        lines = fetch_ai_news.reddit_section(10, "day")

    assert lines[0] == "## Reddit（AI 関連 subreddit 別ピックアップ 10 件）"


def test_reddit_section_includes_entries_from_every_subreddit():
    """先頭の subreddit が limit 件返しても、後続の subreddit の記事が載る。"""
    with patch("fetch_reddit.fetch_top_posts_multi", side_effect=_fake_fetch_top_posts_multi(12)):
        lines = fetch_ai_news.reddit_section(6, "day")

    body = "\n".join(lines)
    for subreddit in fetch_ai_news.fetch_reddit.AI_SUBREDDITS:
        assert f"| r/{subreddit} |" in body


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
      <p class="col-9">LLM assistant</p></article>
    <article class="Box-row"><h2><a href="/example/agent">example / agent</a></h2>
      <p class="col-9">AI agents</p></article>
    </body></html>"""
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = html
    with patch("constants.urllib.request.urlopen", return_value=response):
        lines = fetch_ai_news.github_trend_section(1)
    assert lines == [
        "## GitHub Trending（AI 関連 Top 1）", "", "| 番号 | リポジトリ |", "|---|---|",
        "| 1 | [example/tool](https://github.com/example/tool) |", "",
    ]


def test_github_trend_section_keeps_empty_result_placeholder():
    with patch("fetch_github_trend.fetch_entries", return_value=[]):
        assert "| — | (取得できませんでした) |" in fetch_ai_news.github_trend_section(1)
