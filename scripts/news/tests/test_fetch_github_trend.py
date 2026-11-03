#!/usr/bin/env python3
"""fetch_github_trend.py の fetch_entries() テスト"""
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch_github_trend

def _mock_response(body: str):
    """urlopen のコンテキストマネージャ応答を模したモックを返す。"""
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_fetch_entries_returns_all_entries_with_title_and_url():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        entries = fetch_github_trend.fetch_entries(limit=0)

    assert entries == [
        {"title": "awesome/repo1", "url": "https://github.com/awesome/repo1"},
        {"title": "example/tool", "url": "https://github.com/example/tool"},
        {"title": "awesome/repo3", "url": "https://github.com/awesome/repo3"},
    ]


def test_fetch_entries_respects_limit():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        entries = fetch_github_trend.fetch_entries(limit=2)

    assert len(entries) == 2
    assert [e["title"] for e in entries] == [
        "awesome/repo1",
        "example/tool",
    ]


def test_fetch_entries_filters_by_keywords():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        entries = fetch_github_trend.fetch_entries(limit=10, keywords=["tool"])

    assert [e["title"] for e in entries] == ["example/tool"]


def test_fetch_entries_returns_empty_list_for_empty_feed():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response("<html></html>")):
        entries = fetch_github_trend.fetch_entries(limit=0)

    assert entries == []


TRENDING_HTML = """<!DOCTYPE html>
<html><body>
<a href="/outside/repo">外部カード</a>
<article class="Box-row">
  <div><a href="/sponsors/awesome">Sponsor</a></div>
  <h2 class="h3 lh-condensed"><a href="/awesome/repo1">
    <svg><path d="M0 0"></path></svg><span>awesome /</span> repo1
  </a></h2>
  <p class="col-9 color-fg-muted my-1">A comfortable chair</p>
  <a href="/awesome/repo1/stargazers">100</a>
  <a href="/contributors">Built by</a>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed"><a href="/example/tool"><span>example /</span> tool</a></h2>
  <p class="col-9 color-fg-muted my-1">An <strong>LLM</strong> tool &amp; assistant</p>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed"><a href="/awesome/repo3">awesome / repo3</a></h2>
  <p class="col-9 color-fg-muted my-1">AI agents for developers</p>
</article>
</body></html>
"""


def test_parse_trending_html_returns_ordered_repositories():
    assert fetch_github_trend.parse_trending_html(TRENDING_HTML) == [
        {"title": "awesome/repo1", "url": "https://github.com/awesome/repo1", "description": "A comfortable chair"},
        {"title": "example/tool", "url": "https://github.com/example/tool", "description": "An LLM tool & assistant"},
        {"title": "awesome/repo3", "url": "https://github.com/awesome/repo3", "description": "AI agents for developers"},
    ]


def test_parse_trending_html_ignores_non_repository_links():
    html = """
    <a href="/outside/repo">outside/repo</a>
    <article><h2><a href="/other/repo">other/repo</a></h2></article>
    <article class="Box-row"><a href="/sponsors/person">Sponsor</a></article>
    <article class="Box-row"><h2><a href="/example/tool/stargazers">Star</a></h2></article>
    <article class="Box-row"><h2><a href="https://other.example/owner/repo">owner/repo</a></h2></article>
    <article class="Box-row"><h2><a href="/valid/repo">valid / repo</a></h2>
      <a href="/sponsors/person">Sponsor</a><a href="/valid/repo/forks">Forks</a>
    </article>
    """
    assert fetch_github_trend.parse_trending_html(html) == [
        {"title": "valid/repo", "url": "https://github.com/valid/repo", "description": ""},
    ]


def test_parse_trending_html_handles_missing_description_and_entities():
    html = """
    <article class="Box-row"><h2><a href="/one/first"><span>one /</span> first</a></h2>
      <p class="col-9">日本語の <strong>AI</strong> &amp; LLM</p><div>Built by somebody</div>
    </article>
    <article class="Box-row"><h2><a href="/two/second"> two / second </a></h2></article>
    """
    assert fetch_github_trend.parse_trending_html(html) == [
        {"title": "one/first", "url": "https://github.com/one/first", "description": "日本語の AI & LLM"},
        {"title": "two/second", "url": "https://github.com/two/second", "description": ""},
    ]



def test_fetch_entries_uses_daily_trending_url():
    def respond(request, timeout):
        assert request.full_url == "https://github.com/trending?since=daily"
        assert timeout == 20
        return _mock_response(TRENDING_HTML)

    with patch("constants.urllib.request.urlopen", side_effect=respond):
        assert fetch_github_trend.fetch_entries(limit=1) == [
            {"title": "awesome/repo1", "url": "https://github.com/awesome/repo1"},
        ]


def test_fetch_entries_matches_description_without_changing_title():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        assert fetch_github_trend.fetch_entries(keywords=["LLM"]) == [
            {"title": "example/tool", "url": "https://github.com/example/tool"},
        ]


def test_fetch_entries_preserves_keyword_boundaries():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        assert fetch_github_trend.fetch_entries(keywords=["AI"]) == [
            {"title": "awesome/repo3", "url": "https://github.com/awesome/repo3"},
        ]


def test_fetch_entries_limits_after_filtering():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        assert fetch_github_trend.fetch_entries(limit=1, keywords=["LLM", "AI"]) == [
            {"title": "example/tool", "url": "https://github.com/example/tool"},
        ]


def test_fetch_entries_zero_limit_returns_all_matches():
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        assert fetch_github_trend.fetch_entries(limit=0, keywords=["LLM", "AI"]) == [
            {"title": "example/tool", "url": "https://github.com/example/tool"},
            {"title": "awesome/repo3", "url": "https://github.com/awesome/repo3"},
        ]


def test_fetch_entries_returns_empty_for_no_matches(capsys):
    with patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        assert fetch_github_trend.fetch_entries(keywords=["not-present"]) == []
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("error, message", [
    (urllib.error.HTTPError("https://github.com/trending", 404, "Not Found", {}, None), "HTTP 404"),
    (urllib.error.URLError("接続失敗"), "接続失敗"),
])
def test_fetch_entries_returns_empty_on_network_error(error, message, capsys):
    with patch("constants.urllib.request.urlopen", side_effect=error):
        assert fetch_github_trend.fetch_entries() == []
    captured = capsys.readouterr()
    assert "[WARN] GitHub Trend:" in captured.err
    assert message in captured.err


def test_fetch_entries_warns_when_no_cards_are_recognized(capsys):
    with patch("constants.urllib.request.urlopen", return_value=_mock_response("<html><h1>Unexpected page</h1></html>")):
        assert fetch_github_trend.fetch_entries() == []
    assert "[WARN] GitHub Trend:" in capsys.readouterr().err


@pytest.mark.parametrize("arguments, expected", [
    (["--limit", "1"], "1. awesome/repo1\n   https://github.com/awesome/repo1\n"),
    (["--ai-only", "--limit", "1"], "1. example/tool\n   https://github.com/example/tool\n"),
    (["--keywords", "LLM", "--limit", "1"], "1. example/tool\n   https://github.com/example/tool\n"),
])
def test_main_preserves_cli_options_and_output(arguments, expected, capsys):
    with patch.object(sys, "argv", ["fetch_github_trend.py", *arguments]), \
            patch("constants.urllib.request.urlopen", return_value=_mock_response(TRENDING_HTML)):
        fetch_github_trend.main()
    captured = capsys.readouterr()
    assert captured.out.endswith(expected)
    assert "2." not in captured.out
    assert captured.err == ""
