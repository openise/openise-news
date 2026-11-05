#!/usr/bin/env python3
"""curate_news.py のテスト（ Workers AI の HTTP はモックする）"""
import io
import json
import urllib.error
from datetime import datetime
from unittest.mock import patch

import pytest

import curate_news

DATE = datetime(2026, 11, 3)

NEWS = """---
title: "[AI ニュース] 2026 年 11 月 03 日 (火)"
createdDate: "20261103110001"
---

## はてなブックマーク

| # | タイトル | ブックマーク数 |
|---|---|---|
| 1 | [Claude Code \\| 入門 &amp; 実践](https://example.com/hb1) | 203 |
| 2 | [過去に選んだ記事](https://example.com/old) | 50 |

---

## Hacker News
*対象: Show HN + Ask HN の合算ランキング*

| # | 種別 | タイトル | Points | Comments |
|---|---|---|---|---|
| 1 | Show HN | [Show HN: An agent](https://news.ycombinator.com/item?id=1) | 142 | 30 |

---

## Reddit

| # | サブレディット | タイトル |
|---|---|---|
| 1 | r/ClaudeAI | [Reddit post](https://www.reddit.com/r/ClaudeAI/1) |

---

## Zenn

| # | タイトル | いいね数 |
|---|---|---|
| 1 | [Zenn 記事](https://zenn.dev/x/articles/1) | 12 |
| — | (取得できませんでした) | — |

---

*取得日時: 2026-11-03 11:00:01 JST*
"""

PAST_NEWS = """---
title: "過去の News"
createdDate: "20261020110001"
---

## 今日のピックアップ

1. **[過去に選んだ記事](https://example.com/old)**
*ソース: はてなブックマーク — 50 users*

   まとめ

## はてなブックマーク

| # | タイトル | ブックマーク数 |
|---|---|---|
| 1 | [表にだけある記事](https://example.com/hb1) | 10 |
"""


def write_news(base_dir, date_str, text):
    path = base_dir / date_str / "index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def api_response(output, usage=None):
    body = {
        "success": True,
        "errors": [],
        "result": {
            "response": output,
            "usage": usage or {"prompt_tokens": 300, "completion_tokens": 120, "total_tokens": 420},
        },
    }
    return io.BytesIO(json.dumps(body).encode("utf-8"))


class FakeUrlopen:
    """urlopen の代わりに呼ばれ、送られたリクエストを記録する。"""

    def __init__(self, response):
        self.response = response
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def run_curate(base_dir, response):
    fake = FakeUrlopen(response)
    with patch("urllib.request.urlopen", fake):
        curate_news.curate(DATE, str(base_dir), "token", "account")
    return fake


fetch_repo_description = curate_news.fetch_repo_description


@pytest.fixture(autouse=True)
def no_github_api(monkeypatch):
    """既定では GitHub API を呼ばず、説明文なしとして扱う（ urlopen のモックを Workers AI 用に残すため）。"""
    calls = []

    def fake(repo, token=""):
        calls.append((repo, token))
        return None

    monkeypatch.setattr(curate_news, "fetch_repo_description", fake)
    return calls


@pytest.fixture
def news_dir(tmp_path):
    write_news(tmp_path, "20261020", PAST_NEWS)
    return tmp_path


# -------------------------
# 正常系
# -------------------------

def test_curate_inserts_pickup_after_frontmatter(news_dir, capsys):
    path = write_news(news_dir, "20261103", NEWS)
    # 重複除外後の候補: 1 はてな hb1, 2 HN, 3 Reddit, 4 Zenn
    output = json.dumps([
        {"id": 2, "summary": "HN で 142 points を集めた agent です。"},
        {"id": 1, "summary": "Claude Code の入門記事です。"},
        {"id": 3, "summary": "Reddit の投稿です。"},
        {"id": 4, "summary": "Zenn の記事です。"},
    ], ensure_ascii=False)

    run_curate(news_dir, api_response(output))

    text = path.read_text(encoding="utf-8")
    assert text.startswith(
        '---\ntitle: "[AI ニュース] 2026 年 11 月 03 日 (火)"\ncreatedDate: "20261103110001"\n---\n\n'
        "## 今日のピックアップ\n\n"
        "1. **[Show HN: An agent](https://news.ycombinator.com/item?id=1)**  \n"
        "*ソース: Hacker News — 142 points*\n\n"
        "   HN で 142 points を集めた agent です。\n\n"
        "2. **[Claude Code \\| 入門 &amp; 実践](https://example.com/hb1)**  \n"
        "*ソース: はてなブックマーク — 203 users*\n\n"
        "   Claude Code の入門記事です。\n\n"
        "3. **[Reddit post](https://www.reddit.com/r/ClaudeAI/1)**  \n"
        "*ソース: Reddit (r/ClaudeAI)*\n\n"
        "   Reddit の投稿です。\n\n"
        "4. **[Zenn 記事](https://zenn.dev/x/articles/1)**  \n"
        "*ソース: Zenn — 12 likes*\n\n"
        "   Zenn の記事です。\n\n"
        "## はてなブックマーク\n"
    )
    # 元の表は残る
    assert "| 2 | [過去に選んだ記事](https://example.com/old) | 50 |" in text
    assert "description" not in text
    assert "トークン数: 入力 300 / 出力 120 / 合計 420" in capsys.readouterr().out


def test_curate_indents_summary_by_number_width(news_dir):
    rows = "\n".join(f"| {i} | [記事 {i}](https://zenn.dev/x/{i}) |" for i in range(1, 11))
    news = NEWS.split("## はてなブックマーク")[0] + f"## Zenn\n\n| # | タイトル |\n|---|---|\n{rows}\n"
    path = write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": i, "summary": f"まとめ {i}"} for i in range(1, 11)], ensure_ascii=False)

    run_curate(news_dir, api_response(output))

    text = path.read_text(encoding="utf-8")
    assert "\n   まとめ 9\n" in text
    assert "\n    まとめ 10\n" in text


def test_curate_sends_only_number_source_title_and_score(news_dir):
    write_news(news_dir, "20261103", NEWS)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    fake = run_curate(news_dir, api_response(output))

    request = fake.requests[0]
    assert request.full_url == (
        "https://api.cloudflare.com/client/v4/accounts/account/ai/run/" + curate_news.MODEL
    )
    assert request.get_header("Authorization") == "Bearer token"
    payload = json.loads(request.data)
    assert payload["max_tokens"] == curate_news.MAX_TOKENS
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["messages"][1]["content"] == (
        "候補:\n"
        "1. [はてなブックマーク] Claude Code | 入門 & 実践 (203 users)\n"
        "2. [Hacker News] Show HN: An agent (142 points)\n"
        "3. [Reddit (r/ClaudeAI)] Reddit post\n"
        "4. [Zenn] Zenn 記事 (12 likes)"
    )
    assert "http" not in payload["messages"][1]["content"]


def test_curate_reads_tables_with_reduced_columns(news_dir):
    news = NEWS.split("## はてなブックマーク")[0] + (
        "## はてなブックマーク\n\n| # | タイトル | BM |\n|---|---|---|\n"
        "| 1 | [はてな記事](https://example.com/hb1) | 203 |\n\n---\n\n"
        "## Hacker News\n\n| # | タイトル | Points |\n|---|---|---|\n"
        "| 1 | [Show HN: An agent](https://news.ycombinator.com/item?id=1) | 142 |\n\n---\n\n"
        "## Reddit\n\n| # | タイトル |\n|---|---|\n"
        "| 1 | [Reddit post](https://www.reddit.com/r/ClaudeAI/1) |\n\n---\n\n"
        "## GitHub Trending\n\n| # | リポジトリ | Star |\n|---|---|---|\n"
        "| 1 | [owner/agent](https://github.com/owner/agent) | 1234 |\n"
        "| 2 | [owner/plain](https://github.com/owner/plain) | — |\n\n---\n\n"
        "## Zenn\n\n| # | タイトル | いいね |\n|---|---|---|\n"
        "| 1 | [Zenn 記事](https://zenn.dev/x/articles/1) | 12 |\n"
    )
    write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    fake = run_curate(news_dir, api_response(output))

    assert json.loads(fake.requests[0].data)["messages"][1]["content"] == (
        "候補:\n"
        "1. [はてなブックマーク] はてな記事 (203 users)\n"
        "2. [Hacker News] Show HN: An agent (142 points)\n"
        "3. [Reddit] Reddit post\n"
        "4. [GitHub Trending] owner/agent (1234 stars today)\n"
        "5. [GitHub Trending] owner/plain\n"
        "6. [Zenn] Zenn 記事 (12 likes)"
    )


def test_curate_reads_reddit_table_with_feed_rank_column(news_dir):
    news = NEWS.split("## はてなブックマーク")[0] + (
        "## Reddit\n\n| # | タイトル | 順位 |\n|---|---|---|\n"
        "| 1 | [Reddit post](https://www.reddit.com/r/ClaudeCode/1) | 3 |\n"
        "| 2 | [r/LocalLLaMA の話題](https://www.reddit.com/r/LocalLLaMA/2) | 21 |\n"
    )
    path = write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": 2, "summary": "まとめ"}], ensure_ascii=False)

    fake = run_curate(news_dir, api_response(output))

    assert json.loads(fake.requests[0].data)["messages"][1]["content"] == (
        "候補:\n"
        "1. [Reddit] Reddit post (フィード 3 位)\n"
        "2. [Reddit] r/LocalLLaMA の話題 (フィード 21 位)"
    )
    assert "*ソース: Reddit — フィード 21 位*" in path.read_text(encoding="utf-8")

def test_curate_reads_zenn_table_without_likes_column(news_dir):
    news = NEWS.split("## はてなブックマーク")[0] + (
        "## Zenn\n\n| # | タイトル |\n|---|---|\n| 1 | [Zenn 記事](https://zenn.dev/x/articles/1) |\n"
    )
    path = write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    fake = run_curate(news_dir, api_response(output))

    assert json.loads(fake.requests[0].data)["messages"][1]["content"] == "候補:\n1. [Zenn] Zenn 記事"
    assert "*ソース: Zenn*\n" in path.read_text(encoding="utf-8")


GITHUB_NEWS_HEAD = NEWS.split("## はてなブックマーク")[0]


def test_curate_sends_github_description_and_stars_today(news_dir):
    news = GITHUB_NEWS_HEAD + (
        "## GitHub Trending\n\n| # | リポジトリ | 説明 | 今日のスター |\n|---|---|---|---|\n"
        "| 1 | [owner/agent](https://github.com/owner/agent) | AI agent \\| &lt;CLI&gt; | 1234 |\n"
        "| 2 | [owner/plain](https://github.com/owner/plain) |  | — |\n"
    )
    path = write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    fake = run_curate(news_dir, api_response(output))

    payload = json.loads(fake.requests[0].data)
    assert payload["messages"][1]["content"] == (
        "候補:\n"
        "1. [GitHub Trending] owner/agent (1234 stars today) — AI agent | <CLI>\n"
        "2. [GitHub Trending] owner/plain"
    )
    assert "GitHub Trending の stars today" in payload["messages"][0]["content"]
    assert "*ソース: GitHub Trending — 1234 stars today*\n" in path.read_text(encoding="utf-8")


def test_curate_reads_github_table_without_description_and_stars_columns(news_dir):
    news = GITHUB_NEWS_HEAD + (
        "## GitHub Trending\n\n| # | リポジトリ |\n|---|---|\n"
        "| 1 | [owner/agent](https://github.com/owner/agent) |\n"
    )
    path = write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    fake = run_curate(news_dir, api_response(output))

    assert json.loads(fake.requests[0].data)["messages"][1]["content"] == "候補:\n1. [GitHub Trending] owner/agent"
    assert "*ソース: GitHub Trending*\n" in path.read_text(encoding="utf-8")


def test_curate_adds_github_api_description_only_when_table_has_none(news_dir, monkeypatch):
    news = GITHUB_NEWS_HEAD + (
        "## GitHub Trending\n\n| # | リポジトリ | Star |\n|---|---|---|\n"
        "| 1 | [owner/agent](https://github.com/owner/agent) | 1234 |\n"
        "| 2 | [owner/plain](https://github.com/owner/plain) | — |\n"
    )
    write_news(news_dir, "20261103", news)
    calls = []

    def fake(repo, token=""):
        calls.append((repo, token))
        return {"owner/agent": "AI agent | <CLI>"}.get(repo)

    monkeypatch.setattr(curate_news, "fetch_repo_description", fake)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    fake_urlopen = FakeUrlopen(api_response(output))
    with patch("urllib.request.urlopen", fake_urlopen):
        curate_news.curate(DATE, str(news_dir), "token", "account", "gh-token")

    assert calls == [("owner/agent", "gh-token"), ("owner/plain", "gh-token")]
    payload = json.loads(fake_urlopen.requests[0].data)
    assert payload["messages"][1]["content"] == (
        "候補:\n"
        "1. [GitHub Trending] owner/agent (1234 stars today) — AI agent | <CLI>\n"
        "2. [GitHub Trending] owner/plain"
    )
    assert "スター数や Trending に入ったことには触れず" in payload["messages"][0]["content"]


def test_curate_does_not_call_github_api_when_table_has_description(news_dir, no_github_api):
    news = GITHUB_NEWS_HEAD + (
        "## GitHub Trending\n\n| # | リポジトリ | 説明 | 今日のスター |\n|---|---|---|---|\n"
        "| 1 | [owner/agent](https://github.com/owner/agent) | AI agent | 1234 |\n"
    )
    write_news(news_dir, "20261103", news)
    output = json.dumps([{"id": 1, "summary": "まとめ"}], ensure_ascii=False)

    run_curate(news_dir, api_response(output))

    assert no_github_api == []


def github_response(body):
    return io.BytesIO(json.dumps(body).encode("utf-8"))


def test_fetch_repo_description_sends_token_and_normalizes_spaces():
    fake = FakeUrlopen(github_response({"description": "  AI\n agent  "}))
    with patch("urllib.request.urlopen", fake):
        assert fetch_repo_description("owner/agent", "gh-token") == "AI agent"

    request = fake.requests[0]
    assert request.full_url == "https://api.github.com/repos/owner/agent"
    assert request.get_header("Authorization") == "Bearer gh-token"
    assert request.get_header("Accept") == "application/vnd.github+json"


def test_fetch_repo_description_without_token_sends_no_authorization():
    fake = FakeUrlopen(github_response({"description": "AI agent"}))
    with patch("urllib.request.urlopen", fake):
        assert fetch_repo_description("owner/agent") == "AI agent"
    assert fake.requests[0].get_header("Authorization") is None


@pytest.mark.parametrize("response", [
    github_response({"description": None}),
    github_response({"description": "  "}),
    github_response(["not", "a", "dict"]),
    io.BytesIO(b"not json"),
    urllib.error.HTTPError("https://api.github.com/repos/owner/agent", 403, "rate limit", None, None),
    urllib.error.URLError("timeout"),
])
def test_fetch_repo_description_returns_none_on_failure_or_empty(response):
    with patch("urllib.request.urlopen", FakeUrlopen(response)):
        assert fetch_repo_description("owner/agent") is None


def test_curate_accepts_code_fenced_json_and_choices_format(news_dir):
    path = write_news(news_dir, "20261103", NEWS)
    body = {
        "success": True,
        "result": {
            "choices": [{"message": {"content": '```json\n[{"id": 4, "summary": "Zenn の記事"}]\n```'}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        },
    }

    run_curate(news_dir, io.BytesIO(json.dumps(body).encode("utf-8")))

    assert "*ソース: Zenn — 12 likes*\n\n   Zenn の記事\n" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "result",
    [
        {"choices": [{"message": {
            "reasoning_content": "候補 1 は重要。[{\"id\": 2}]",
            "content": '[{"id": 4, "summary": "Zenn の記事"}]',
        }}]},
        {"response": '<think>候補 1 は重要。[{"id": 2}]</think>\n[{"id": 4, "summary": "Zenn の記事"}]'},
    ],
)
def test_curate_discards_reasoning_output(news_dir, result):
    path = write_news(news_dir, "20261103", NEWS)
    body = {"success": True, "result": result}

    run_curate(news_dir, io.BytesIO(json.dumps(body).encode("utf-8")))

    text = path.read_text(encoding="utf-8")
    assert "*ソース: Zenn — 12 likes*\n\n   Zenn の記事\n" in text
    assert "候補 1 は重要" not in text


def test_curate_escapes_html_and_links_in_summary(news_dir):
    path = write_news(news_dir, "20261103", NEWS)
    output = json.dumps([{"id": 1, "summary": "<script>x</script>\n[罠](javascript:x)"}])

    run_curate(news_dir, api_response(output))

    text = path.read_text(encoding="utf-8")
    assert "   &lt;script&gt;x&lt;/script&gt; \\[罠\\](javascript:x)\n" in text
    assert "<script>" not in text


# -------------------------
# 重複除外
# -------------------------

def test_recent_picked_urls_reads_only_pickup_within_30_days(tmp_path):
    write_news(tmp_path, "20261020", PAST_NEWS)
    pickup = "---\ntitle: x\ncreatedDate: \"20261003110001\"\n---\n\n## 今日のピックアップ\n\n1. **[a](https://example.com/{})**  \n"
    write_news(tmp_path, "20261004", pickup.format("day30"))   # 30 日前は含む
    write_news(tmp_path, "20261003", pickup.format("day31"))   # 31 日前は含まない
    write_news(tmp_path, "20261103", pickup.format("today"))   # 対象日は含まない

    urls = curate_news.recent_picked_urls(DATE, str(tmp_path))

    assert urls == {"https://example.com/old", "https://example.com/day30"}


def test_curate_excludes_recently_picked_urls_and_renumbers(news_dir):
    write_news(news_dir, "20261103", NEWS)
    output = json.dumps([{"id": 1, "summary": "まとめ"}])

    fake = run_curate(news_dir, api_response(output))

    prompt = json.loads(fake.requests[0].data)["messages"][1]["content"]
    assert "過去に選んだ記事" not in prompt
    assert "\n2. [Hacker News]" in prompt


def test_curate_writes_message_without_calling_ai_when_no_candidates(tmp_path):
    news = NEWS.split("## はてなブックマーク")[0] + "## Zenn\n\n| — | (取得できませんでした) |\n"
    path = write_news(tmp_path, "20261103", news)

    fake = run_curate(tmp_path, api_response("[]"))

    assert fake.requests == []
    assert "## 今日のピックアップ\n\n選出できる候補がありませんでした。\n" in path.read_text(encoding="utf-8")


def test_curate_skips_when_pickup_already_exists(news_dir, capsys):
    text = NEWS.replace("---\n\n## はてな", "---\n\n## 今日のピックアップ\n\n既存\n\n## はてな", 1)
    path = write_news(news_dir, "20261103", text)

    fake = run_curate(news_dir, api_response("[]"))

    assert fake.requests == []
    assert path.read_text(encoding="utf-8") == text
    assert "スキップ" in capsys.readouterr().out


# -------------------------
# 失敗系（ファイルは変えない）
# -------------------------

@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b'{"errors":["auth"]}')),
            "HTTP 401",
        ),
        (urllib.error.URLError("timeout"), "接続できません"),
        (io.BytesIO(json.dumps({"success": False, "errors": [{"message": "bad"}]}).encode()), "エラーを返しました"),
        (io.BytesIO(b"not json"), "応答が JSON ではありません"),
        (api_response("ピックアップは次のとおりです"), "出力が JSON ではありません"),
        (api_response('{"id": 1, "summary": "x"}'), "JSON 配列ではありません"),
        (api_response("[]"), "1 〜 10 件ではありません"),
        (api_response(json.dumps([{"id": i, "summary": "x"} for i in range(1, 12)])), "1 〜 10 件ではありません"),
        (api_response('[{"id": 99, "summary": "x"}]'), "候補に無い id"),
        (api_response('[{"id": "1", "summary": "x"}]'), "候補に無い id"),
        (api_response('[{"id": 1, "summary": "x"}, {"id": 1, "summary": "y"}]'), "重複"),
        (api_response('[{"id": 1, "summary": "  "}]'), "summary が空"),
        (api_response('[1]'), "オブジェクトではありません"),
    ],
)
def test_curate_raises_and_keeps_file_on_failure(news_dir, response, message):
    path = write_news(news_dir, "20261103", NEWS)

    with pytest.raises(curate_news.CurationError, match=message):
        run_curate(news_dir, response)

    assert path.read_text(encoding="utf-8") == NEWS


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        # 2026-11-03 の失敗: 思考で max_tokens を使い切り、本文が空
        (
            {"choices": [{"finish_reason": "length", "message": {"reasoning_content": "秘密の思考" * 10, "content": ""}}]},
            "finish_reason: length / 思考の欄: reasoning_content 50 文字",
        ),
        (
            {"choices": [{"finish_reason": "stop", "message": {"content": "説明文"}}]},
            "finish_reason: stop / 思考の欄: なし",
        ),
        (
            {"response": "<think>秘密の思考</think>説明文"},
            "finish_reason: None / 思考の欄: <think> 5 文字",
        ),
    ],
)
def test_curate_logs_finish_reason_and_reasoning_length_on_failure(news_dir, capsys, result, expected):
    write_news(news_dir, "20261103", NEWS)
    body = {"success": True, "result": result}

    with pytest.raises(curate_news.CurationError, match="出力が JSON ではありません"):
        run_curate(news_dir, io.BytesIO(json.dumps(body).encode("utf-8")))

    err = capsys.readouterr().err
    assert expected in err
    assert "秘密の思考" not in err


def test_curate_reports_finish_reason_when_output_is_missing(news_dir):
    write_news(news_dir, "20261103", NEWS)
    body = {"success": True, "result": {"choices": [{"finish_reason": "length", "message": {"reasoning_content": "abc"}}]}}

    with pytest.raises(curate_news.CurationError, match="finish_reason: length / 思考の欄: reasoning_content 3 文字"):
        run_curate(news_dir, io.BytesIO(json.dumps(body).encode("utf-8")))


def test_main_returns_1_without_credentials(monkeypatch, capsys):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.setattr("sys.argv", ["curate_news.py"])

    assert curate_news.main() == 1
    assert "CLOUDFLARE_API_TOKEN" in capsys.readouterr().err


def test_main_returns_1_on_curation_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setattr(curate_news, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["curate_news.py", "--date", "20261103"])

    assert curate_news.main() == 1
    assert "News のファイルがありません" in capsys.readouterr().err
