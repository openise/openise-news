---
name: c-new-issue
description: "依頼内容から GitHub Issues の issue（タイトル・本文・ラベル）を下書きし、了承を得てから作る。"
---

# c-new-issue

依頼内容を `CLAUDE.md` の「issue の書式」に沿った issue にまとめ、了承を得てから openise/openise-news に作る。

## 手順

1. 依頼内容を読み、足りない情報（目的・完了条件・確かめ方）があれば質問する
2. 次の 3 つを下書きしてユーザーに提示する
   - タイトル: `<type>: <内容>`（type は `feat`・`fix`・`refactor`・`chore`・`docs`）
   - 本文: `## 概要`・`## Acceptance criteria`（`- [ ]` のチェックリスト）・`## テスト計画` の 3 節
   - ラベル: `bug`・`enhancement`・`documentation`・`refactor`・`chore` から 1 つ。priority は付けない
3. ユーザーの了承を得る。修正を求められたら直して再提示する。了承前に issue を作らない
4. GitHub MCP の `issue_write`（method: `create`）で issue を作る
5. 作った issue の番号と URL を報告する

## 注意

- 下書きだけを頼まれたときは、提示までで止める
- Acceptance criteria は検証できる形で書く（「〜がある」「〜で〜が表示される」など）
