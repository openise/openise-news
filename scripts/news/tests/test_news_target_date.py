"""対象日を指定した収集とキュレーションが JST の日付境界をまたいでもずれない。"""
from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import curate_news
import fetch_ai_news
from constants import JST


@pytest.mark.parametrize('explicit_date', [False, True])
def test_news_target_date_across_midnight(tmp_path, monkeypatch, explicit_date):
    class Clock(datetime):
        current = datetime(2026, 11, 6, 23, 59, tzinfo=JST)

        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)

    monkeypatch.setattr(fetch_ai_news, 'datetime', Clock)
    monkeypatch.setattr(curate_news, 'datetime', Clock)
    monkeypatch.setattr(fetch_ai_news, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(curate_news, 'BASE_DIR', str(tmp_path))
    history_dates = []
    hn_calls = []

    def empty_source(*args, **kwargs):
        Clock.current = datetime(2026, 11, 7, 0, 1, tzinfo=JST)
        return []

    def hn_source(tag, since, limit, until):
        hn_calls.append((since, until))
        return []

    def history(date, *args):
        history_dates.append(date.strftime('%Y%m%d'))
        return set()

    monkeypatch.setattr(fetch_ai_news, 'recent_urls', history)
    monkeypatch.setattr(fetch_ai_news.fetch_hb, 'fetch_entrylist_tag_entries', empty_source)
    monkeypatch.setattr(fetch_ai_news.fetch_hn, 'fetch_hits_or_none', hn_source)
    monkeypatch.setattr(fetch_ai_news, 'reddit_section', lambda *args: [])
    monkeypatch.setattr(fetch_ai_news, 'github_trend_section', lambda *args: [])
    monkeypatch.setattr(fetch_ai_news, 'qiita_section', lambda *args: [])
    monkeypatch.setattr(fetch_ai_news, 'zenn_section', lambda *args: [])
    date_args = ['--date', '20261106'] if explicit_date else []
    monkeypatch.setattr('sys.argv', ['fetch_ai_news.py', *date_args])
    assert fetch_ai_news.main() == 0
    output = tmp_path / '20261106' / 'index.md'
    markdown = output.read_text()
    assert 'title: "2026 年 11 月 06 日（金）"' in markdown
    assert 'createdDate: "20261106' in markdown
    assert set(history_dates) == {'20261106'}
    start = int(datetime(2026, 11, 4, tzinfo=JST).timestamp()) - 1
    end = int(datetime(2026, 11, 5, tzinfo=JST).timestamp()) - 1
    assert hn_calls == [(start, end), (start, end)]
    assert not (tmp_path / '20261107').exists()

    monkeypatch.setenv('CLOUDFLARE_API_TOKEN', 'token')
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'account')
    curate = Mock()
    monkeypatch.setattr(curate_news, 'curate', curate)
    monkeypatch.setattr('sys.argv', ['curate_news.py', *date_args])
    assert curate_news.main() == 0
    target = curate.call_args.args[0]
    # 省略時は各 CLI の実行開始時点の当日を使う既存の挙動を保つ。
    assert target.strftime('%Y%m%d') == ('20261106' if explicit_date else '20261107')
    assert target.utcoffset() == timedelta(hours=9)
    if explicit_date:
        assert (tmp_path / target.strftime('%Y%m%d') / 'index.md') == output
