---
name: issue-fix
description: 引数で渡された番号の GitHub Issues の issue を実装し、作業ブランチに push して `Closes #N` 付きの PR を作り、issue に PR のリンクをコメントする。「#N を実装して」「issue N を直して」などと頼まれたときに使う。
---

# issue-fix

引数の issue 番号（例: `3` や `#3`）の issue を実装して PR を作る。merge はしない。

## 手順

1. GitHub MCP の `issue_read`（method: `get`）で openise/openise-news の issue を読み、Acceptance criteria とテスト計画を把握する
   - issue が無い・close 済みなら、何も変更せずに停止して報告する
2. `CLAUDE.md` の作業の原則に沿って実装する。issue に関係する箇所だけを変える
3. テスト計画のうちセッション内でできるものと、`CLAUDE.md` の検証コマンドを実行し、通ることを確かめる
   - 失敗したら直す。直せなければ停止して報告する
   - merge 後にしか確かめられない項目は、PR の説明に残す
4. 作業ブランチで `<type>: <内容>` の形式で commit し、`git push -u origin <作業ブランチ>` で push する
   - type は `feat`・`fix`・`refactor`・`chore`・`docs`。内容は日本語で書く
5. GitHub MCP の `create_pull_request` で `main` 向けの PR を作る
   - タイトル: commit と同じ `<type>: <内容>`
   - 説明: 先頭に `Closes #N`。続けて変更内容と、Acceptance criteria・テスト計画の確認結果を書く
6. GitHub MCP の `add_issue_comment` で issue に PR へのリンクをコメントする
7. PR の URL を報告する

## してはいけないこと

- `main` への push・PR の merge・deploy（`wrangler deploy` など）
