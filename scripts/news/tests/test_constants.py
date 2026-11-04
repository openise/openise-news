#!/usr/bin/env python3
"""constants.py の filter_by_keywords() / fetch_url() テスト"""
import sys
import http.client
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import constants
import pytest


@pytest.mark.parametrize("title", [
    "Explain the maintainers tradeoffs", "Digital legacy and legit email",
    "detail train", "paid", "git2", "2ai", "LLMserver", "mcpsystem",
    "GPT6server", "GPT4.1server", "myGPT6", "2GPT6", "GPT.6",
    "myNeovim", "trusted", "cvesystem",
])
def test_filter_by_keywords_ignores_keyword_inside_word(title):
    assert constants.filter_by_keywords([{"title": title}], constants.AI_KEYWORDS) == []


@pytest.mark.parametrize("title", [
    "LLMs", "AI agents", "Claude Code", "LLMエージェント", "OpenAI",
    "ClaudeCode", "GitHub", "MCPs", "GPTs", "日本語LLM", "LLM-powered", "生成AIとLLM",
])
def test_filter_by_keywords_matches_plural_and_japanese_neighbor(title):
    entries = [{"title": title}]
    assert constants.filter_by_keywords(entries, constants.AI_KEYWORDS) == entries


@pytest.mark.parametrize("title", [
    "GPT6", "gpt4", "GPT4.1", "GPT4.1.2", "日本語GPT6入門", "GPT6.",
])
def test_filter_by_keywords_matches_product_names_and_numbered_gpt(title):
    entries = [{"title": title}]
    assert constants.filter_by_keywords(entries, constants.AI_KEYWORDS) == entries


@pytest.mark.parametrize("title", [
    "VS Code の拡張機能", "VSCode 拡張", "Neovim 入門", "Vim の設定", "Next.js 16 の新機能",
    "E2Eテスト大全", "Rust で書く", "CVE-2026-12345 の脆弱性", "Grok 5 が登場", "Qwen3 を試す",
    "GLM-5 の性能", "Kimi K3", "OpenCode を使う", "Ghostty の設定", "GitLab CI", "Python 3.15",
    "TypeScript 7", "Node.js 26", "Ruby on Rails", "Markdown 記法", "Mermaid で図を描く",
    "CSS の新機能", "Playwright でテスト", "ADR を書く", "TDD 入門", "SDD で開発", "Web API 設計",
    "Cursor 3.0", "Devin を導入", "WordPress 7",
])
def test_filter_by_keywords_matches_programming_keywords(title):
    entries = [{"title": title}]
    assert constants.filter_by_keywords(entries, constants.AI_KEYWORDS) == entries


@pytest.mark.parametrize("title", [
    # 4 文字以上のキーワードは後ろに英字が続いても当たるため、loop は入れていない
    "Loopback interface",
    # 外したキーワード（claw ・ openclaw ・ vllm ・ litellm）だけを含むタイトル
    "vLLM で推論", "OpenClaw を試す", "LiteLLM proxy", "Claw machine",
    # ai は外したため、「AI」以外にキーワードを含まないタイトル
    "高市早苗が細野豪志に手を重ねている画像はAIによる偽画像だよ", "JASRACが生成曲の検知へ AI時代",
    "AIエージェント", "日本語AI", "AI-powered", "Ask HN: Are you using AI to do election choices",
])
def test_filter_by_keywords_ignores_unlisted_words(title):
    assert constants.filter_by_keywords([{"title": title}], constants.AI_KEYWORDS) == []


@pytest.mark.parametrize("title", [
    "Google が新モデルを発表", "Meta の Llama", "AWS Lambda 入門", "React 19 の新機能",
    "npm パッケージ", "Hono で API", "Docker Compose", "Slack bot", "Vercel にデプロイ",
    "Obsidian のプラグイン", "EmDash を試す", "Muse を使う", "Jev を試す",
    "Reacts", "Metaの新モデル", "GoogleCloud", "Docker入門",
])
def test_filter_by_keywords_matches_added_keywords(title):
    entries = [{"title": title}]
    assert constants.filter_by_keywords(entries, constants.AI_KEYWORDS) == entries


@pytest.mark.parametrize("title", [
    # muse ・ meta ・ react ・ hono ・ slack は右側も境界必須のため、別の単語には当たらない
    "Museum of Modern Art", "metadata の扱い", "reaction GIF", "honor code", "slacker",
    "Metaverse", "Reactive programming",
])
def test_filter_by_keywords_requires_right_boundary_for_whole_word_keywords(title):
    assert constants.filter_by_keywords([{"title": title}], constants.AI_KEYWORDS) == []


def test_filter_by_keywords_treats_custom_keywords_as_literals():
    entries = [{"title": "C++ 入門"}, {"title": "CCC 入門"}]
    assert constants.filter_by_keywords(entries, ["c++"]) == entries[:1]


def test_filter_by_keywords_handles_empty_keywords_and_null_title():
    assert constants.filter_by_keywords([{"title": "AI"}], []) == []
    assert constants.filter_by_keywords([{"title": None}], constants.AI_KEYWORDS) == []

RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Claude Code Tips</title>
      <link>https://example.com/1</link>
    </item>
    <item>
      <title>Docker Compose </title>
      <link>https://example.com/2</link>
    </item>
  </channel>
</rss>
"""


# -------------------------
# filter_by_keywords
# -------------------------

def test_filter_by_keywords_matches_case_insensitively():
    entries = [
        {"title": "Claude Code の新機能"},
        {"title": "Mac用ランチャーアプリ"},
        {"title": "OPENAIが新モデル発表"},
    ]
    result = constants.filter_by_keywords(entries, ["claude", "openai"])
    titles = [e["title"] for e in result]
    assert titles == ["Claude Code の新機能", "OPENAIが新モデル発表"]


def test_filter_by_keywords_returns_empty_when_no_match():
    entries = [{"title": "Mac用ランチャーアプリ"}]
    assert constants.filter_by_keywords(entries, ["claude"]) == []


def test_filter_by_keywords_handles_missing_title_key():
    entries = [{"url": "https://example.com"}]
    assert constants.filter_by_keywords(entries, ["claude"]) == []


# -------------------------
# fetch_url
# -------------------------

def test_fetch_url_returns_response_bytes_on_success():
    fake_response = MagicMock()
    fake_response.read.return_value = b"body-bytes"
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False

    with patch("constants.urllib.request.urlopen", return_value=fake_response) as mock_urlopen:
        result = constants.fetch_url(
            "https://example.com/feed",
            user_agent="TestAgent/1.0",
            source_label="Test",
        )

    assert result == b"body-bytes"
    called_req, = mock_urlopen.call_args.args
    assert called_req.full_url == "https://example.com/feed"
    assert called_req.get_header("User-agent") == "TestAgent/1.0"
    assert mock_urlopen.call_args.kwargs == {"timeout": 20}


def test_fetch_url_returns_none_on_http_error(capsys):
    http_error = urllib.error.HTTPError(
        url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
    )
    with patch("constants.urllib.request.urlopen", side_effect=http_error):
        result = constants.fetch_url(
            "https://example.com", user_agent="TestAgent/1.0", source_label="Test"
        )

    assert result is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "404" in stderr


def test_fetch_url_returns_none_on_url_error(capsys):
    url_error = urllib.error.URLError("接続失敗の理由")
    with patch("constants.urllib.request.urlopen", side_effect=url_error):
        result = constants.fetch_url(
            "https://example.com", user_agent="TestAgent/1.0", source_label="Test"
        )

    assert result is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr


def test_fetch_url_returns_none_on_read_timeout(capsys):
    fake_response = MagicMock()
    fake_response.read.side_effect = TimeoutError("read timed out")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False

    with patch("constants.urllib.request.urlopen", return_value=fake_response):
        result = constants.fetch_url(
            "https://example.com", user_agent="TestAgent/1.0", source_label="Test"
        )

    assert result is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "レスポンス読み込み失敗" in stderr


def test_fetch_url_returns_none_on_read_os_error(capsys):
    fake_response = MagicMock()
    fake_response.read.side_effect = OSError("connection reset")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False

    with patch("constants.urllib.request.urlopen", return_value=fake_response):
        result = constants.fetch_url(
            "https://example.com", user_agent="TestAgent/1.0", source_label="Test"
        )

    assert result is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "レスポンス読み込み失敗" in stderr


def test_fetch_url_returns_none_on_incomplete_read(capsys):
    fake_response = MagicMock()
    fake_response.read.side_effect = http.client.IncompleteRead(b"partial", 10)
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False

    with patch("constants.urllib.request.urlopen", return_value=fake_response):
        result = constants.fetch_url(
            "https://example.com", user_agent="TestAgent/1.0", source_label="Test"
        )

    assert result is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "レスポンス読み込み失敗" in stderr


# -------------------------
# render_external_link
# -------------------------

def test_render_external_link_escapes_html_tags_in_label():
    result = constants.render_external_link("<script>alert(1)</script>", "https://example.com")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "[&lt;script&gt;alert\\(1\\)&lt;/script&gt;](https://example.com)" == result


def test_render_external_link_escapes_markdown_characters():
    result = constants.render_external_link("title [with] (parens) \\backslash", "https://example.com")
    assert "\\[" in result
    assert "\\]" in result
    assert "\\(" in result
    assert "\\)" in result
    assert "\\\\" in result


def test_render_external_link_returns_label_only_for_javascript_url():
    result = constants.render_external_link("Click me", "javascript:alert(1)")
    assert result == "Click me"
    assert "[" not in result


def test_render_external_link_returns_label_only_when_url_has_no_netloc():
    result = constants.render_external_link("title", "")
    assert result == "title"
    assert "[" not in result

    result2 = constants.render_external_link("title", "ftp://example.com")
    assert result2 == "title"
    assert "[" not in result2


def test_render_external_link_builds_normal_link_for_https_url():
    result = constants.render_external_link("Normal Title", "https://example.com/article")
    assert result == "[Normal Title](https://example.com/article)"


def test_render_external_link_escapes_pipe_for_table():
    result = constants.render_external_link("col1 | col2", "https://example.com")
    assert "\\|" in result
    assert "[col1 \\| col2](https://example.com)" == result


def test_render_external_link_replaces_newlines_in_label():
    result = constants.render_external_link("line1\nline2", "https://example.com")
    assert "\n" not in result
    assert "line1 line2" in result


def test_render_external_link_replaces_carriage_return_in_label():
    result = constants.render_external_link("line1\rline2", "https://example.com")

    assert result == "[line1 line2](https://example.com)"


def test_render_external_link_collapses_crlf_in_label_into_single_space():
    result = constants.render_external_link("line1\r\nline2", "https://example.com")

    assert result == "[line1 line2](https://example.com)"


def test_render_external_link_collapses_consecutive_newlines_in_label():
    result = constants.render_external_link("a\r\n\r\nb", "https://example.com")

    assert result == "[a b](https://example.com)"


def test_render_external_link_escapes_newline_in_url():
    """改行を含む URL でも table 行が 1 行のまま保たれる。"""
    result = constants.render_external_link("title", "https://example.com/a\nb")

    assert "\n" not in result
    assert result == "[title](https://example.com/ab)"


def test_render_external_link_escapes_tab_in_url():
    """タブを含む URL でも table 行が 1 行のまま保たれる。"""
    result = constants.render_external_link("title", "https://example.com/a\tb")

    assert "\t" not in result
    assert result == "[title](https://example.com/ab)"


def test_render_external_link_escapes_space_in_url():
    """空白を含む URL でもリンクが途中で切れない。"""
    result = constants.render_external_link("title", "https://example.com/a b")

    assert " " not in result[result.index("](") :]
    assert result == "[title](https://example.com/a%20b)"


def test_render_external_link_escapes_pipe_in_url():
    """パイプを含む URL でも table の列が増えない。"""
    result = constants.render_external_link("title", "https://example.com/a|b")

    assert "|" not in result
    assert result == "[title](https://example.com/a%7Cb)"


def test_render_external_link_escapes_unbalanced_parenthesis_in_url():
    """閉じ括弧を含む URL でもリンク構文が正しく閉じる。"""
    result = constants.render_external_link("title", "https://example.com/a)b")

    assert result == "[title](https://example.com/a%29b)"
    assert result.count("(") == 1
    assert result.count(")") == 1


def test_render_external_link_keeps_query_fragment_and_existing_escapes():
    """正常な URL は無変換で通す（query ・ fragment ・ percent-encode 済みの値・ unicode host）。"""
    url = "https://例え.jp/p?a=b&c=d%28e%29#frag"

    assert constants.render_external_link("title", url) == f"[title]({url})"


def test_render_external_link_keeps_balanced_parentheses_resolvable():
    """括弧を含む正常な URL がリンク先として解決可能なまま保たれる。"""
    result = constants.render_external_link("title", "https://ja.wikipedia.org/wiki/Foo_(bar)")

    assert result == "[title](https://ja.wikipedia.org/wiki/Foo_%28bar%29)"
    destination = result[result.index("](") + 2 : -1]
    assert urllib.parse.unquote(destination) == "https://ja.wikipedia.org/wiki/Foo_(bar)"


# -------------------------
# parse_xml
# -------------------------

def test_parse_xml_returns_root_element_for_valid_xml():
    root = constants.parse_xml(RSS_FEED, "Test")

    assert root is not None
    assert root.tag == "rss"


def test_parse_xml_returns_none_on_broken_xml(capsys):
    root = constants.parse_xml(b"<rss><item>unclosed", "Test")

    assert root is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "XML パース失敗" in stderr


def test_parse_xml_rejects_billion_laughs_payload(capsys):
    billion_laughs = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<rss><item><title>&lol3;</title></item></rss>
"""
    root = constants.parse_xml(billion_laughs, "Test")

    assert root is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "DOCTYPE" in stderr


def test_parse_xml_rejects_billion_laughs_payload_encoded_as_utf16(capsys):
    """バイト列の部分文字列一致では検出できない encoding でも拒否できることを確認する。"""
    billion_laughs = """<?xml version="1.0" encoding="UTF-16"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<rss><item><title>&lol2;</title></item></rss>
""".encode("utf-16")

    root = constants.parse_xml(billion_laughs, "Test")

    assert root is None
    stderr = capsys.readouterr().err
    assert "[WARN] Test" in stderr
    assert "DOCTYPE" in stderr


def test_parse_xml_does_not_reject_doctype_text_inside_cdata():
    """地の文（CDATA 内テキスト）に \"<!DOCTYPE\" という文字列が含まれるだけでは拒否されないことを確認する。"""
    feed = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item><title><![CDATA[HTML5 \xe3\x81\xae <!DOCTYPE html> \xe3\x81\xab\xe3\x81\xa4\xe3\x81\x84\xe3\x81\xa6]]></title><link>https://example.com</link></item>
</channel></rss>
"""
    root = constants.parse_xml(feed, "Test")

    assert root is not None
    assert constants.parse_rss_items(root) == [
        {"title": "HTML5 の <!DOCTYPE html> について", "url": "https://example.com"}
    ]


# -------------------------
# parse_rss_items
# -------------------------

def test_parse_rss_items_extracts_title_and_url_from_channel():
    root = constants.parse_xml(RSS_FEED, "Test")

    assert constants.parse_rss_items(root, limit=0) == [
        {"title": "Claude Code Tips", "url": "https://example.com/1"},
        {"title": "Docker Compose", "url": "https://example.com/2"},
    ]


def test_parse_rss_items_respects_limit():
    root = constants.parse_xml(RSS_FEED, "Test")

    entries = constants.parse_rss_items(root, limit=1)

    assert [e["title"] for e in entries] == ["Claude Code Tips"]


# -------------------------
# fetch_feed_entries
# -------------------------

def test_fetch_feed_entries_parses_response_with_given_parser():
    with patch("constants.fetch_url", return_value=RSS_FEED):
        entries = constants.fetch_feed_entries(
            "https://example.com/feed", constants.parse_rss_items, "Test", limit=1
        )

    assert entries == [{"title": "Claude Code Tips", "url": "https://example.com/1"}]


def test_fetch_feed_entries_filters_by_keywords_before_applying_limit():
    captured_limits = []

    def spy_parser(root, limit):
        captured_limits.append(limit)
        return constants.parse_rss_items(root, limit)

    with patch("constants.fetch_url", return_value=RSS_FEED):
        entries = constants.fetch_feed_entries(
            "https://example.com/feed", spy_parser, "Test", limit=1, keywords=["docker"]
        )

    # キーワード指定時は全件パース（limit=0）してからフィルタする
    assert captured_limits == [0]
    assert entries == [{"title": "Docker Compose", "url": "https://example.com/2"}]


def test_fetch_feed_entries_returns_empty_list_when_fetch_fails():
    with patch("constants.fetch_url", return_value=None):
        entries = constants.fetch_feed_entries(
            "https://example.com/feed", constants.parse_rss_items, "Test"
        )

    assert entries == []


def test_fetch_feed_entries_returns_empty_list_on_broken_xml(capsys):
    with patch("constants.fetch_url", return_value=b"<rss><item>unclosed"):
        entries = constants.fetch_feed_entries(
            "https://example.com/feed", constants.parse_rss_items, "Test"
        )

    assert entries == []
    assert "[WARN] Test" in capsys.readouterr().err


# -------------------------
# run_feed_cli
# -------------------------

def test_run_feed_cli_prints_numbered_entries(capsys):
    calls = []

    def fake_fetch(limit, keywords):
        calls.append((limit, keywords))
        return [{"title": "記事タイトル", "url": "https://example.com/1"}]

    with patch.object(sys, "argv", ["fetch_x.py", "--limit", "3"]):
        constants.run_feed_cli("テスト用フェッチャー", fake_fetch)

    assert calls == [(3, None)]
    out = capsys.readouterr().out
    assert "1. 記事タイトル" in out
    assert "https://example.com/1" in out


def test_run_feed_cli_passes_ai_keywords_when_ai_only_is_given():
    calls = []

    def fake_fetch(limit, keywords):
        calls.append((limit, keywords))
        return []

    with patch.object(sys, "argv", ["fetch_x.py", "--ai-only"]):
        constants.run_feed_cli("テスト用フェッチャー", fake_fetch)

    assert calls == [(10, constants.AI_KEYWORDS)]


def test_run_feed_cli_appends_custom_keywords_to_ai_keywords():
    calls = []

    def fake_fetch(limit, keywords):
        calls.append((limit, keywords))
        return []

    with patch.object(sys, "argv", ["fetch_x.py", "--ai-only", "--keywords", "rust"]):
        constants.run_feed_cli("テスト用フェッチャー", fake_fetch)

    assert calls == [(10, constants.AI_KEYWORDS + ["rust"])]


def test_run_feed_cli_prints_placeholder_when_no_entries(capsys):
    with patch.object(sys, "argv", ["fetch_x.py"]):
        constants.run_feed_cli("テスト用フェッチャー", lambda limit, keywords: [])

    assert "(該当記事なし)" in capsys.readouterr().out
