#!/usr/bin/env python3
"""BASE_DIR が __file__ からリポジトリルートを解決し、cwd に依存しないことのテスト"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import constants
import fetch_ai_news
import fetch_hb
import fetch_hn
import fetch_reddit

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_fetch_ai_news_base_dir_resolves_from_file_not_cwd():
    assert fetch_ai_news.BASE_DIR == str(REPO_ROOT / "src/content/news")


def test_fetch_hn_default_output_is_outside_news_collection():
    now = datetime(2026, 1, 2, 3, 4, 5)
    output = fetch_hn._default_output_path(now)
    assert not output.startswith(str(REPO_ROOT / "src/content/news"))
    assert output.startswith(constants.MANUAL_OUTPUT_DIR)


def test_fetch_hb_default_output_is_outside_news_collection():
    now = datetime(2026, 1, 2, 3, 4, 5)
    output = fetch_hb._default_output_path("it", 50, now)
    assert not output.startswith(str(REPO_ROOT / "src/content/news"))
    assert output.startswith(constants.MANUAL_OUTPUT_DIR)


def test_fetch_reddit_default_output_is_outside_news_collection():
    now = datetime(2026, 1, 2, 3, 4, 5)
    output = fetch_reddit._default_output_path("day", now)
    assert not output.startswith(str(REPO_ROOT / "src/content/news"))
    assert output.startswith(constants.MANUAL_OUTPUT_DIR)


def test_default_output_paths_resolve_from_file_not_cwd():
    assert constants.MANUAL_OUTPUT_DIR == str(REPO_ROOT / "vault" / "news-manual")
