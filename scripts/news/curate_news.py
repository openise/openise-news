#!/usr/bin/env python3
"""
curate_news.py - 収集済みの News に Workers AI で「今日のピックアップ」を付ける

AI には記事の選定と記事ごとの短いまとめだけを任せ、書式・重複除外は Python で行う。

使い方:
    python3 curate_news.py                 # 今日（JST）の News
    python3 curate_news.py --date 20261103

環境変数:
    CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID

終了コード: 成功・スキップは 0 、失敗（ API エラー・応答の検証失敗など）は 1
"""

import argparse
import html
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from constants import JST

BASE_DIR = str(Path(__file__).resolve().parents[2] / "src/content/news")

# 多言語に強い Gemma 4 の MoE 版。推論時に動くパラメータが 4B 程度で Neurons の消費が少ない
# （入力 9,091 ・出力 27,273 Neurons / 100 万トークン）。
MODEL = "@cf/google/gemma-4-26b-a4b-it"
API_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
# 10 件 × 1 〜 2 文の日本語と JSON の記号が収まる量。思考の出力が返る場合もこの範囲に収める
MAX_TOKENS = 1500
MAX_PICKS = 10
HISTORY_DAYS = 30
PICKUP_HEADING = "## 今日のピックアップ"

# 収集スクリプトの見出しの先頭 → ピックアップの source 表記
SOURCES = {
    "## はてなブックマーク": "はてなブックマーク",
    "## Hacker News": "Hacker News",
    "## Reddit": "Reddit",
    "## GitHub Trending": "GitHub Trending",
    "## Qiita": "Qiita",
    "## Zenn": "Zenn",
}

# render_external_link が出力するリンク。タイトル内の ] は \] にエスケープ済み
_LINK_RE = re.compile(r"\[((?:\\.|[^\]\\])*)\]\(([^)\s]+)\)")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_ROW_RE = re.compile(r"^\| \d+ \|")
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

SYSTEM_PROMPT = f"""あなたは AI ・開発ツールのニュースを選ぶ編集者です。
候補の一覧から「今日のピックアップ」を最大 {MAX_PICKS} 件選び、各記事に日本語で 1 〜 2 文の短いまとめを付けてください。

選定基準:
- 数値の高さ: はてなブックマークの users 、 Hacker News の points が高いものを優先する（同じ source 内の比較に使う）
- クロスソース: 複数の source で話題になっているトピックを優先する
- 多様性: 同じトピックが重ならないようにする
- 技術寄り: Claude Code ・ AI ・開発ツールなど、開発者向けの技術的な話題を優先する
- 適切な候補が {MAX_PICKS} 件に満たなければ、その件数だけ選ぶ

まとめの書き方:
- タイトルから分かる範囲で、なぜ注目か・何が読みどころかを書く。タイトルに無い事実を作らない
- 日本語と英単語・数字の間には半角スペースを入れる（例:「Claude Code の新機能」「100 件」）

出力は次の形式の JSON 配列だけにしてください。前後に説明文やコードブロックを付けないでください。
[{{"id": 候補の番号, "summary": "まとめ"}}]"""


class CurationError(Exception):
    """キュレーションの失敗（ API エラー・応答の検証失敗）。"""


# -----------------------------------------------------------------------
# News ファイルの解析
# -----------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """frontmatter（区切りの --- を含む）と本文に分ける。"""
    match = re.match(r"---\n.*?\n---\n", text, re.DOTALL)
    if not match:
        raise CurationError("frontmatter が見つかりません")
    return text[: match.end()], text[match.end():]


def plain_title(link_text: str) -> str:
    """表のリンク文字列から Markdown ・ HTML のエスケープを外す（ AI に渡す用）。"""
    return html.unescape(re.sub(r"\\(.)", r"\1", link_text))


def parse_candidates(body: str) -> list[dict]:
    """本文の各 source の表から候補を取り出す。同じ URL は最初の 1 件だけ残す。"""
    candidates = []
    seen_urls = set()
    source = None
    for line in body.splitlines():
        if line.startswith("## "):
            source = next((label for prefix, label in SOURCES.items() if line.startswith(prefix)), None)
            continue
        if source is None or not _ROW_RE.match(line):
            continue
        link = _LINK_RE.search(line)
        if not link or link.group(2) in seen_urls:
            continue
        seen_urls.add(link.group(2))

        cells = [c.strip() for c in _CELL_SPLIT_RE.split(line)[1:-1]]
        label = source
        score = None
        if source == "はてなブックマーク":
            score = f"{cells[2]} users"
        elif source == "Hacker News":
            score = f"{cells[3]} points"
        elif source == "Reddit":
            label = f"Reddit ({cells[1]})"

        candidates.append({
            "id": len(candidates) + 1,
            "source": label,
            "score": score,
            "link_text": link.group(1),
            "url": link.group(2),
        })
    return candidates


def picked_urls(text: str) -> set[str]:
    """「今日のピックアップ」節にある URL を返す（収集元の表の URL は含めない）。"""
    _, body = split_frontmatter(text)
    urls = set()
    in_pickup = False
    for line in body.splitlines():
        if line.startswith("## "):
            in_pickup = line.strip() == PICKUP_HEADING
            continue
        if in_pickup:
            urls.update(m.group(2) for m in _LINK_RE.finditer(line))
    return urls


def recent_picked_urls(date: datetime, base_dir: str) -> set[str]:
    """対象日の前日から 30 日前まで（両端を含む）の News でピックアップ済みの URL を返す。"""
    urls = set()
    for days in range(1, HISTORY_DAYS + 1):
        path = os.path.join(base_dir, (date - timedelta(days=days)).strftime("%Y%m%d"), "index.md")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            try:
                urls |= picked_urls(f.read())
            except CurationError:
                print(f"[WARN] frontmatter が無いため重複除外の対象外にします: {path}", file=sys.stderr)
    return urls


# -----------------------------------------------------------------------
# Workers AI
# -----------------------------------------------------------------------

def build_prompt(candidates: list[dict]) -> str:
    lines = ["候補:"]
    for c in candidates:
        score = f" ({c['score']})" if c["score"] else ""
        lines.append(f"{c['id']}. [{c['source']}] {plain_title(c['link_text'])}{score}")
    return "\n".join(lines)


def describe_finish(result: dict) -> str:
    """失敗の切り分け用に、 finish_reason と思考の欄の有無・長さを返す（思考の中身は含めない）。"""
    choice = {}
    if isinstance(result.get("choices"), list) and result["choices"] and isinstance(result["choices"][0], dict):
        choice = result["choices"][0]
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}

    reasoning = []
    for key in ("reasoning_content", "reasoning"):
        if message.get(key) is not None:
            reasoning.append(f"{key} {len(str(message[key]))} 文字")
    if isinstance(result.get("response"), str):
        thinks = re.findall(r"<think>(.*?)</think>", result["response"], re.DOTALL)
        if thinks:
            reasoning.append(f"<think> {sum(len(t) for t in thinks)} 文字")
    return f"finish_reason: {choice.get('finish_reason')} / 思考の欄: {'、'.join(reasoning) or 'なし'}"


def call_workers_ai(prompt: str, api_token: str, account_id: str) -> tuple[object, dict, str]:
    """Workers AI を呼び、モデルの出力・ usage ・失敗時の切り分け用の情報を返す。"""
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": MAX_TOKENS,
        # gemma-4 は既定で思考し、 max_tokens を思考だけで使い切って本文が空になることがあった（ #26 ）
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request = urllib.request.Request(
        API_URL.format(account_id=account_id, model=MODEL),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise CurationError(f"Workers AI が HTTP {e.code} を返しました: {detail}") from e
    except (urllib.error.URLError, OSError) as e:
        raise CurationError(f"Workers AI に接続できませんでした: {e}") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CurationError("Workers AI の応答が JSON ではありません") from e
    if not isinstance(data, dict) or not data.get("success") or not isinstance(data.get("result"), dict):
        errors = data.get("errors") if isinstance(data, dict) else None
        raise CurationError(f"Workers AI がエラーを返しました: {errors}")

    result = data["result"]
    diagnostics = describe_finish(result)
    # モデルによって応答の形が異なる（ response 形式と OpenAI 互換の choices 形式）。
    # 思考の出力（ reasoning_content など）は使わずに捨て、本文だけを取り出す
    if "response" in result:
        output = result["response"]
    else:
        try:
            output = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise CurationError(f"Workers AI の応答にモデルの出力がありません（ {diagnostics} ）") from e
    if isinstance(output, str):
        output = _THINK_RE.sub("", output)
    return output, result.get("usage") or {}, diagnostics


def parse_picks(output: object, candidates: list[dict]) -> list[dict]:
    """モデルの出力を検証し、 [{"id", "summary"}] を返す。"""
    if isinstance(output, str):
        text = output.strip()
        # 指示に反してコードブロックで囲まれた場合だけ外す
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        try:
            output = json.loads(text)
        except json.JSONDecodeError as e:
            raise CurationError(f"モデルの出力が JSON ではありません: {text[:200]}") from e

    if not isinstance(output, list):
        raise CurationError("モデルの出力が JSON 配列ではありません")
    if not 1 <= len(output) <= MAX_PICKS:
        raise CurationError(f"選ばれた件数が 1 〜 {MAX_PICKS} 件ではありません: {len(output)} 件")

    valid_ids = {c["id"] for c in candidates}
    picks = []
    seen = set()
    for item in output:
        if not isinstance(item, dict):
            raise CurationError(f"要素がオブジェクトではありません: {item!r}")
        pick_id = item.get("id")
        summary = item.get("summary")
        if isinstance(pick_id, bool) or not isinstance(pick_id, int) or pick_id not in valid_ids:
            raise CurationError(f"候補に無い id です: {pick_id!r}")
        if pick_id in seen:
            raise CurationError(f"id が重複しています: {pick_id}")
        if not isinstance(summary, str) or not summary.strip():
            raise CurationError(f"summary が空です: id {pick_id}")
        seen.add(pick_id)
        picks.append({"id": pick_id, "summary": summary})
    return picks


# -----------------------------------------------------------------------
# 書式
# -----------------------------------------------------------------------

def sanitize_summary(summary: str) -> str:
    """AI の出力を 1 行のテキストにし、 HTML ・リンク構文として解釈されないようにする。"""
    text = " ".join(summary.split())
    text = html.escape(text, quote=False)
    return re.sub(r"([\\\[\]])", r"\\\1", text)


def render_pickup(picks: list[dict], candidates: list[dict]) -> str:
    by_id = {c["id"]: c for c in candidates}
    lines = [PICKUP_HEADING, ""]
    for i, pick in enumerate(picks, 1):
        c = by_id[pick["id"]]
        source = f"{c['source']} — {c['score']}" if c["score"] else c["source"]
        indent = " " * (len(str(i)) + 2)
        lines += [
            f"{i}. **[{c['link_text']}]({c['url']})**  ",
            f"*ソース: {source}*",
            "",
            f"{indent}{sanitize_summary(pick['summary'])}",
            "",
        ]
    return "\n".join(lines)


def has_pickup(body: str) -> bool:
    return any(line.strip() == PICKUP_HEADING for line in body.splitlines())


def write_atomic(path: str, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".curate.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# -----------------------------------------------------------------------
# エントリーポイント
# -----------------------------------------------------------------------

def curate(date: datetime, base_dir: str, api_token: str, account_id: str) -> None:
    """対象日の News にピックアップを付ける。失敗時は CurationError を送出し、ファイルは変えない。"""
    path = os.path.join(base_dir, date.strftime("%Y%m%d"), "index.md")
    if not os.path.exists(path):
        raise CurationError(f"News のファイルがありません: {path}")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    frontmatter, body = split_frontmatter(text)

    # 同じ日の再実行で AI を呼び直さず、公開済みのピックアップも変えない
    if has_pickup(body):
        print(f"[INFO] ピックアップが既にあるためスキップします: {path}")
        return

    history = recent_picked_urls(date, base_dir)
    candidates = [c for c in parse_candidates(body) if c["url"] not in history]
    # 除外で番号が飛ぶと AI が存在しない番号を返しやすいため、振り直す
    for i, c in enumerate(candidates, 1):
        c["id"] = i
    print(f"[INFO] 候補 {len(candidates)} 件（過去 {HISTORY_DAYS} 日のピックアップ {len(history)} 件を除外対象）")

    if candidates:
        output, usage, diagnostics = call_workers_ai(build_prompt(candidates), api_token, account_id)
        print(
            f"[INFO] Workers AI ({MODEL}) トークン数: "
            f"入力 {usage.get('prompt_tokens', '?')} / 出力 {usage.get('completion_tokens', '?')} / "
            f"合計 {usage.get('total_tokens', '?')}"
        )
        try:
            picks = parse_picks(output, candidates)
        except CurationError:
            print(f"[INFO] モデルの出力の状況: {diagnostics}", file=sys.stderr)
            raise
        pickup = render_pickup(picks, candidates)
    else:
        pickup = f"{PICKUP_HEADING}\n\n選出できる候補がありませんでした。\n"

    write_atomic(path, f"{frontmatter}\n{pickup}\n{body.lstrip(chr(10))}")
    print(f"✅ ピックアップを追加しました: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="News に Workers AI で「今日のピックアップ」を付ける")
    parser.add_argument("--date", "-d", default="", help="対象日 YYYYMMDD (default: 今日 JST)")
    args = parser.parse_args()

    date = datetime.strptime(args.date, "%Y%m%d") if args.date else datetime.now(JST)
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    if not api_token or not account_id:
        print("[ERROR] CLOUDFLARE_API_TOKEN と CLOUDFLARE_ACCOUNT_ID を設定してください", file=sys.stderr)
        return 1

    try:
        curate(date, BASE_DIR, api_token, account_id)
    except CurationError as e:
        print(f"[ERROR] キュレーションに失敗しました: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
