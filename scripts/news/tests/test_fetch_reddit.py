#!/usr/bin/env python3
"""fetch_reddit.py のテスト"""
import os
import sys
from xml.sax.saxutils import escape
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch_reddit
import pytest


@pytest.mark.parametrize("multi", [False, True])
@pytest.mark.parametrize("title", ["", "   "])
def test_empty_title_becomes_placeholder(multi, title):
    raw = _atom_feed([
        ("ClaudeAI", title, "https://reddit.com/1"),
        ("ClaudeAI", "次の投稿", "https://reddit.com/2"),
    ])
    with patch("fetch_reddit.fetch_url", return_value=raw):
        if multi:
            posts = fetch_reddit.fetch_top_posts_multi(["ClaudeAI"], 10, "day")["ClaudeAI"]
        else:
            posts = fetch_reddit.fetch_top_posts("ClaudeAI", 10, "day")
    assert posts == [
        {"title": "(タイトルなし)", "url": "https://reddit.com/1"},
        {"title": "次の投稿", "url": "https://reddit.com/2"},
    ]
    assert "タイトルなし" in "\n".join(fetch_reddit.section_md("ClaudeAI", posts))


def test_default_output_path_is_under_base_dir_manual_subdir():
    now = datetime(2026, 7, 3, 9, 30, 0)

    path = fetch_reddit._default_output_path(period="day", now=now)

    assert path == os.path.join(
        fetch_reddit.MANUAL_OUTPUT_DIR, "reddit_ai_day_20260703_093000.md"
    )


def test_fetch_top_posts_returns_empty_list_on_malformed_xml(capsys):
    with patch("fetch_reddit.fetch_url", return_value=b"<not-valid-xml"):
        result = fetch_reddit.fetch_top_posts("ClaudeCode", limit=10, period="day")

    assert result == []
    stderr = capsys.readouterr().err
    assert "[WARN] r/ClaudeCode" in stderr
    assert "XML パース失敗" in stderr


def test_fetch_top_posts_sends_the_shared_user_agent(monkeypatch):
    monkeypatch.setattr(fetch_reddit, "USER_AGENT", "TestAgent/9.9")

    with patch("fetch_reddit.fetch_url", return_value=None) as mock_fetch:
        fetch_reddit.fetch_top_posts("ClaudeCode", limit=10, period="day")

    assert mock_fetch.call_args.kwargs["user_agent"] == "TestAgent/9.9"


def _atom_feed(entries: list[tuple]) -> bytes:
    """(subreddit, title, url[, リンク先]) の list から統合 URL 応答を模した Atom feed を組み立てる。

    リンク先を渡すと、実際の応答と同じく content（HTML を XML エスケープしたもの）に
    "[link]" のアンカーとして入れる。
    """
    def _entry(sub, title, url, link=None):
        content = ""
        if link is not None:
            html = f'submitted by /u/someone <span><a href="{link}">[link]</a></span>'
            content = f'<content type="html">{escape(html)}</content>'
        return (
            f'<entry><category term="{sub}" label="r/{sub}"/>'
            f"<title>{title}</title>{content}"
            f'<link href="{url}" /></entry>'
        )

    entry_xml = "".join(_entry(*e) for e in entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<category term="multi" label="r/multi"/>'
        f"{entry_xml}</feed>"
    ).encode()


def test_fetch_top_posts_multi_requests_a_single_combined_url():
    with patch("fetch_reddit.fetch_url", return_value=None) as mock_fetch:
        fetch_reddit.fetch_top_posts_multi(["ClaudeAI", "OpenAI", "GeminiAI"], limit=10, period="day")

    assert mock_fetch.call_count == 1
    requested_url = mock_fetch.call_args.args[0]
    # limit(10) * subreddit 数(3) = 30 は REDDIT_MULTI_FETCH_SIZE(100) の下限に切り上げられる
    assert requested_url == (
        "https://www.reddit.com/r/ClaudeAI+OpenAI+GeminiAI/top.rss?t=day&limit=100"
    )


def test_fetch_top_posts_multi_requests_more_than_fetch_size_floor_when_needed():
    with patch("fetch_reddit.fetch_url", return_value=None) as mock_fetch:
        fetch_reddit.fetch_top_posts_multi(["ClaudeAI", "OpenAI", "GeminiAI"], limit=50, period="day")

    requested_url = mock_fetch.call_args.args[0]
    assert "limit=150" in requested_url


def test_fetch_top_posts_multi_groups_entries_by_subreddit_category():
    raw = _atom_feed([
        ("ClaudeAI", "post 1", "https://reddit.com/1"),
        ("OpenAI", "post 2", "https://reddit.com/2"),
        ("ClaudeAI", "post 3", "https://reddit.com/3"),
    ])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeAI", "OpenAI", "GeminiAI"], limit=10, period="day")

    assert [p["title"] for p in result["ClaudeAI"]] == ["post 1", "post 3"]
    assert [p["title"] for p in result["OpenAI"]] == ["post 2"]
    assert result["GeminiAI"] == []


def test_fetch_top_posts_multi_caps_each_subreddit_at_limit():
    raw = _atom_feed([("ClaudeAI", f"post {i}", f"https://reddit.com/{i}") for i in range(1, 5)])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeAI"], limit=2, period="day")

    assert len(result["ClaudeAI"]) == 2


def test_fetch_top_posts_multi_returns_empty_lists_for_all_subreddits_when_rate_limited():
    with patch("fetch_reddit.fetch_url", return_value=None):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeAI", "OpenAI"], limit=10, period="day")

    assert result == {"ClaudeAI": [], "OpenAI": []}


def test_main_uses_jst_timestamp_under_non_jst_timezone(tmp_path, local_timezone):
    captured = {}

    def fake_to_markdown(results, period, now):
        captured["now"] = now
        return "# dummy\n"

    argv = ["fetch_reddit.py", "--subreddit", "ClaudeCode", "--output", str(tmp_path / "out.md")]
    with local_timezone("UTC"), \
            patch.object(sys, "argv", argv), \
            patch("fetch_reddit.fetch_top_posts", return_value=[]), \
            patch("fetch_reddit.to_markdown", side_effect=fake_to_markdown):
        fetch_reddit.main()

    # naive datetime なら utcoffset() は None になるため、JST 化されたことを決定的に検証できる
    assert captured["now"].utcoffset() == timedelta(hours=9)


def test_main_uses_combined_fetch_for_multiple_subreddits(tmp_path):
    argv = [
        "fetch_reddit.py", "--subreddit", "ClaudeAI", "OpenAI",
        "--output", str(tmp_path / "out.md"),
    ]
    with patch.object(sys, "argv", argv), \
            patch("fetch_reddit.fetch_top_posts_multi", return_value={"ClaudeAI": [], "OpenAI": []}) as mock_multi, \
            patch("fetch_reddit.fetch_top_posts") as mock_single:
        fetch_reddit.main()

    mock_multi.assert_called_once_with(["ClaudeAI", "OpenAI"], 10, "day")
    mock_single.assert_not_called()


def test_main_uses_single_fetch_for_one_subreddit(tmp_path):
    argv = ["fetch_reddit.py", "--subreddit", "ClaudeCode", "--output", str(tmp_path / "out.md")]
    with patch.object(sys, "argv", argv), \
            patch("fetch_reddit.fetch_top_posts", return_value=[]) as mock_single, \
            patch("fetch_reddit.fetch_top_posts_multi") as mock_multi:
        fetch_reddit.main()

    mock_single.assert_called_once_with("ClaudeCode", 10, "day")
    mock_multi.assert_not_called()


@pytest.mark.parametrize("link", [
    "https://i.redd.it/abc.png",
    "https://v.redd.it/abc",
    "https://preview.redd.it/abc.png?width=640&crop=smart",
    "https://imgur.com/abc",
    "https://i.imgur.com/abc.jpg",
    "https://www.reddit.com/gallery/1xabcde",
])
def test_fetch_top_posts_multi_excludes_media_posts(link):
    raw = _atom_feed([
        ("ClaudeCode", "画像の投稿", "https://reddit.com/1", link),
        ("ClaudeCode", "次の投稿", "https://reddit.com/2"),
    ])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeCode"], limit=10, period="day")

    assert [p["title"] for p in result["ClaudeCode"]] == ["次の投稿"]


@pytest.mark.parametrize("link", [
    # テキスト投稿は [link] が投稿自身を指す
    "https://www.reddit.com/r/ClaudeCode/comments/1xabcde/some_post/",
    "https://example.com/blog/post",
])
def test_fetch_top_posts_multi_keeps_text_and_external_link_posts(link):
    raw = _atom_feed([("ClaudeCode", "残る投稿", "https://reddit.com/1", link)])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeCode"], limit=10, period="day")

    assert [p["title"] for p in result["ClaudeCode"]] == ["残る投稿"]


def test_fetch_top_posts_multi_keeps_only_first_post_with_same_title():
    raw = _atom_feed([
        ("ClaudeCode", "クロスポスト", "https://reddit.com/1"),
        ("LocalLLaMA", "クロスポスト", "https://reddit.com/2"),
        ("LocalLLaMA", "別の投稿", "https://reddit.com/3"),
    ])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeCode", "LocalLLaMA"], limit=10, period="day")

    assert [p["url"] for p in result["ClaudeCode"]] == ["https://reddit.com/1"]
    assert [p["url"] for p in result["LocalLLaMA"]] == ["https://reddit.com/3"]


def test_fetch_top_posts_multi_fills_excluded_slots_with_next_posts():
    raw = _atom_feed([
        ("ClaudeCode", "画像", "https://reddit.com/1", "https://i.redd.it/a.png"),
        ("ClaudeCode", "post 2", "https://reddit.com/2"),
        ("LocalLLaMA", "post 2", "https://reddit.com/3"),
        ("ClaudeCode", "post 4", "https://reddit.com/4"),
        ("LocalLLaMA", "post 5", "https://reddit.com/5"),
        ("LocalLLaMA", "post 6", "https://reddit.com/6"),
        ("ClaudeCode", "post 7", "https://reddit.com/7"),
    ])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        result = fetch_reddit.fetch_top_posts_multi(["ClaudeCode", "LocalLLaMA"], limit=2, period="day")

    assert [p["title"] for p in result["ClaudeCode"]] == ["post 2", "post 4"]
    assert [p["title"] for p in result["LocalLLaMA"]] == ["post 5", "post 6"]


def test_fetch_top_posts_ranked_keeps_feed_order_across_subreddits():
    raw = _atom_feed([
        ("ClaudeCode", "post 1", "https://reddit.com/1"),
        ("LocalLLaMA", "post 2", "https://reddit.com/2"),
        ("ClaudeCode", "画像", "https://reddit.com/3", "https://i.redd.it/a.png"),
        ("ClaudeCode", "post 4", "https://reddit.com/4"),
        ("Other", "post 5", "https://reddit.com/5"),
    ])

    with patch("fetch_reddit.fetch_url", return_value=raw):
        ranked = fetch_reddit.fetch_top_posts_ranked(["ClaudeCode", "LocalLLaMA"], limit=10, period="day")

    # 順位は応答での位置で、除いた画像の投稿・対象外のサブレディットの投稿も数える
    assert [(sub, rank, p["title"]) for sub, rank, p in ranked] == [
        ("ClaudeCode", 1, "post 1"), ("LocalLLaMA", 2, "post 2"), ("ClaudeCode", 4, "post 4"),
    ]


def test_fetch_top_posts_ranked_returns_empty_list_when_rate_limited():
    with patch("fetch_reddit.fetch_url", return_value=None):
        assert fetch_reddit.fetch_top_posts_ranked(["ClaudeCode"], limit=10, period="day") == []
