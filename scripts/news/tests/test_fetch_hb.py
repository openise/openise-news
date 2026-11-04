#!/usr/bin/env python3
"""fetch_hb.py の _wait_for_crawl_delay() ・ _ENTRY_BLOCK_RE ・ _default_output_path() テスト"""
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import constants
import fetch_hb


def test_wait_for_crawl_delay_sleeps_when_called_within_5_seconds():
    fetch_hb._last_request_at = None

    with patch("fetch_hb.time.monotonic", side_effect=[100.0, 101.0, 105.0]), \
         patch("fetch_hb.time.sleep") as mock_sleep:
        fetch_hb._wait_for_crawl_delay()  # 1回目: 待機なし
        fetch_hb._wait_for_crawl_delay()  # 2回目: 1秒しか経過していないため4秒待機

    mock_sleep.assert_called_once_with(4.0)


# -------------------------
# _ENTRY_BLOCK_RE
# -------------------------

_ENTRY_LIST_HTML = """
<ul class="entrylist-contents-list">
  <li class="entrylist-contents js-keyboard-selectable-item" data-entry-id="1">
    <div class="entrylist-contents-main">
      <h3 class="entrylist-contents-title">
        <a href="https://example.com/article1" title="AI駆動開発の技術的負債について" target="_blank" rel="noopener">AI駆動開発の技術的負債について</a>
      </h3>
      <p class="entrylist-contents-description">AI駆動開発における技術的負債の扱い方について解説する記事です。</p>
      <ul class="entrylist-contents-meta">
        <li class="entrylist-contents-date">2026/07/01</li>
        <li>
          <span class="entrylist-contents-users">
            <a href="https://b.hatena.ne.jp/entry/s/example.com/article1"><span>42</span></a>
          </span>
        </li>
      </ul>
    </div>
  </li>
  <li class="entrylist-contents js-keyboard-selectable-item" data-entry-id="2">
    <div class="entrylist-contents-main">
      <h3 class="entrylist-contents-title">
        <a href="https://example.com/article2" title="Mac用ランチャーアプリの新機能" target="_blank" rel="noopener">Mac用ランチャーアプリの新機能</a>
      </h3>
      <p class="entrylist-contents-description">Mac向けランチャーアプリの新機能を紹介します。</p>
      <ul class="entrylist-contents-meta">
        <li class="entrylist-contents-date">2026/06/30</li>
        <li>
          <span class="entrylist-contents-users">
            <a href="https://b.hatena.ne.jp/entry/s/example.com/article2"><span>7</span></a>
          </span>
        </li>
      </ul>
    </div>
  </li>
  <li class="entrylist-contents js-keyboard-selectable-item" data-entry-id="3">
    <div class="entrylist-contents-main">
      <h3 class="entrylist-contents-title">
        <a href="https://example.com/article3" title="Rustで書くWebサーバー入門" target="_blank" rel="noopener">Rustで書くWebサーバー入門</a>
      </h3>
      <p class="entrylist-contents-description">Rustで Web サーバーを構築する入門記事です。</p>
      <ul class="entrylist-contents-meta">
        <li class="entrylist-contents-date">2026/06/29</li>
        <li>
          <span class="entrylist-contents-users">
            <a href="https://b.hatena.ne.jp/entry/s/example.com/article3"><span>128</span></a>
          </span>
        </li>
      </ul>
    </div>
  </li>
</ul>
"""


def test_entry_block_re_extracts_url_title_count_tuples_from_html_fragment():
    matches = fetch_hb._ENTRY_BLOCK_RE.findall(_ENTRY_LIST_HTML)

    assert matches == [
        ("https://example.com/article1", "AI駆動開発の技術的負債について", "42"),
        ("https://example.com/article2", "Mac用ランチャーアプリの新機能", "7"),
        ("https://example.com/article3", "Rustで書くWebサーバー入門", "128"),
    ]


# -------------------------
# _default_output_path
# -------------------------

def test_default_output_path_is_under_base_dir_manual_subdir():
    now = datetime(2026, 7, 3, 9, 30, 0)

    path = fetch_hb._default_output_path(category="it", limit=50, now=now)

    assert path == os.path.join(
        constants.MANUAL_OUTPUT_DIR, "hatena_it_top50_20260703_093000.md"
    )


# -------------------------
# _parse_rss (malformed XML)
# -------------------------

def test_parse_rss_returns_empty_list_on_malformed_xml(capsys):
    result = fetch_hb._parse_rss(b"<not-valid-xml", limit=10)

    assert result == []
    stderr = capsys.readouterr().err
    assert "[WARN] はてなブックマーク" in stderr
    assert "XML パース失敗" in stderr


def test_to_markdown_uses_jst_timestamp_under_non_jst_timezone(local_timezone):
    with local_timezone("UTC"):
        md = fetch_hb.to_markdown([], "テストカテゴリ")

    assert datetime.now(constants.JST).strftime("%Y-%m-%d %H:%M") in md


def test_main_uses_jst_timestamp_in_default_output_path_under_non_jst_timezone(
    tmp_path, monkeypatch, local_timezone
):
    monkeypatch.setattr(fetch_hb, "MANUAL_OUTPUT_DIR", str(tmp_path))
    captured = {}

    def fake_save_markdown(content, path):
        captured["path"] = path

    with local_timezone("UTC"), \
            patch.object(sys, "argv", ["fetch_hb.py"]), \
            patch("fetch_hb.fetch_entries", return_value=[]), \
            patch("fetch_hb.save_markdown", side_effect=fake_save_markdown):
        fetch_hb.main()

    assert datetime.now(constants.JST).strftime("%Y%m%d_%H%M") in captured["path"]


# -------------------------
# fetch_entrylist_tag_entries: 非 UTF-8 応答
# -------------------------

def test_fetch_entrylist_returns_empty_on_non_utf8_response(capsys):
    """非 UTF-8 のバイト列を受け取っても例外を送出せず、[WARN] を出して空リストを返す。"""
    with patch("fetch_hb._wait_for_crawl_delay"), \
            patch("fetch_hb.fetch_url", return_value=b"\xff\xfe invalid utf-8"):
        result = fetch_hb.fetch_entrylist_tag_entries(category="it", tag="プログラミング")

    assert result == []
    stderr = capsys.readouterr().err
    assert "[WARN] はてなブックマーク" in stderr


ENTRYLIST_HTML = """
<h3 class="entrylist-contents-title">
        <a href="https://example.com/articles/1?a=1&amp;b=2"
           title="E2Eテスト大全 &amp; Rust 入門"
           target="_blank" rel="noopener"
           class="js-keyboard-openable"
           data-gtm-click-label="entry-info-title">E2Eテスト大全 &amp; Rust 入門</a>
      </h3>
      <span class="entrylist-contents-users">
        <a href="/entry/s/example.com/articles/1"
           title="すべてのブックマークを見る"
           class="js-keyboard-entry-page-openable"
           data-gtm-click-label="entry-info-users"><span>284</span> users</a>
      </span>
<h3 class="entrylist-contents-title">
        <a href="https://example.com/articles/2"
           title="Claude Code の新機能"
           target="_blank" rel="noopener">Claude Code の新機能</a>
      </h3>
      <span class="entrylist-contents-users">
        <a href="/entry/s/example.com/articles/2"><span>4</span> users</a>
      </span>
"""


def test_fetch_entrylist_requests_tag_entrylist_page():
    with patch("fetch_hb._wait_for_crawl_delay") as wait, \
            patch("fetch_hb.fetch_url", return_value=ENTRYLIST_HTML.encode("utf-8")) as fetch:
        fetch_hb.fetch_entrylist_tag_entries(category="it", tag="プログラミング")

    wait.assert_called_once()
    assert fetch.call_args.args[0] == (
        "https://b.hatena.ne.jp/entrylist/it/%E3%83%97%E3%83%AD%E3%82%B0%E3%83%A9%E3%83%9F%E3%83%B3%E3%82%B0"
    )


def test_fetch_entrylist_parses_title_url_and_bookmark_count():
    with patch("fetch_hb._wait_for_crawl_delay"), \
            patch("fetch_hb.fetch_url", return_value=ENTRYLIST_HTML.encode("utf-8")):
        entries = fetch_hb.fetch_entrylist_tag_entries(category="it", tag="プログラミング")

    assert entries == [
        {"title": "E2Eテスト大全 & Rust 入門", "url": "https://example.com/articles/1?a=1&b=2", "tags": [], "bookmark_count": 284},
        {"title": "Claude Code の新機能", "url": "https://example.com/articles/2", "tags": [], "bookmark_count": 4},
    ]


# -------------------------
# module docstring
# -------------------------

def test_module_docstring_references_actual_filename():
    """使い方の案内がそのまま実行できる実ファイル名を参照している。"""
    assert "hatena_bookmark_tech.py" not in fetch_hb.__doc__
    assert "python3 fetch_hb.py" in fetch_hb.__doc__
