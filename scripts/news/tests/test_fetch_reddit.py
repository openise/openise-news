#!/usr/bin/env python3
"""fetch_reddit.py のテスト"""
import os
import sys
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


def _atom_feed(entries: list[tuple[str, str, str]]) -> bytes:
    """(subreddit, title, url) の list から統合 URL 応答を模した Atom feed を組み立てる。"""
    entry_xml = "".join(
        f'<entry><category term="{sub}" label="r/{sub}"/>'
        f"<title>{title}</title>"
        f'<link href="{url}" /></entry>'
        for sub, title, url in entries
    )
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
