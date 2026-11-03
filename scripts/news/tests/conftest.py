#!/usr/bin/env python3
"""news テスト共通の fixture"""
import os
import time
from contextlib import contextmanager

import pytest


@pytest.fixture
def local_timezone():
    """テスト中だけローカルタイムゾーンを切り替えるコンテキストマネージャを返す。"""
    original = os.environ.get("TZ")

    @contextmanager
    def _switch(tz: str):
        os.environ["TZ"] = tz
        time.tzset()
        yield

    yield _switch

    if original is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = original
    time.tzset()
