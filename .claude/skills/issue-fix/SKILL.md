---
name: issue-fix
description: 引数で渡された番号の GitHub Issues の issue を実装し、作業ブランチに push して `Closes #N` 付きの PR を作る。issue 本文の Acceptance criteria にチェックを付け、PR のリンクとテスト計画の確認結果を issue にコメントする。close 済みの issue に未チェックの項目が残っていれば、merge 後の確認を行って結果を issue に書き戻す。「#N を実装して」「issue N を直して」「#N の merge 後の確認をして」などと頼まれたときに使う。
---

# issue-fix

引数の issue 番号（例: `3` や `#3`）の issue を実装して PR を作る。merge はしない。
close 済みの issue に未チェックの項目が残っていれば、実装の代わりに「merge 後の確認」を行う。

## 手順

1. GitHub MCP の `issue_read`（method: `get`）で openise/openise-news の issue を読み、Acceptance criteria とテスト計画を把握する
   - issue が無いなら、何も変更せずに停止して報告する
   - close 済みなら、`issue_read`（method: `get_comments`）でコメントも読む。issue 本文の Acceptance criteria か、コメントのテスト計画の確認結果に `- [ ]` が残っていれば、下の「merge 後の確認」に進む。残っていなければ、何も変更せずに停止して報告する
2. `CLAUDE.md` の作業の原則に沿って実装する。issue に関係する箇所だけを変える
3. テスト計画のうちセッション内でできるものと、`CLAUDE.md` の検証コマンドを実行し、通ることを確かめる
   - 失敗したら直す。直せなければ停止して報告する
   - merge 後にしか確かめられない項目は、PR の説明に残す
4. 作業ブランチで `<type>: <内容>` の形式で commit し、`git push -u origin <作業ブランチ>` で push する
   - type は `feat`・`fix`・`refactor`・`chore`・`docs`。内容は日本語で書く
5. GitHub MCP の `create_pull_request` で `main` 向けの PR を作る
   - タイトル: commit と同じ `<type>: <内容>`
   - 説明: 先頭に `Closes #N`。続けて変更内容と、Acceptance criteria・テスト計画の確認結果を書く
6. GitHub MCP の `issue_write`（method: `update`）で、issue 本文の Acceptance criteria のうち満たした項目を `- [x]` にする
   - 本文のほかの部分は変えない。手順 1 で読んだ本文をもとに、チェックボックスだけを書き換えた本文を渡す
   - merge 後にしか確かめられない項目は `- [ ]` のまま残す
7. GitHub MCP の `add_issue_comment` で issue にコメントする。次の 2 つを 1 つのコメントにまとめる
   - PR へのリンク
   - テスト計画の確認結果。項目ごとに `- [x]` で書き、実行したコマンドと結果（件数など）を添える。merge 後にしか確かめられない項目は `- [ ]` のまま残す
8. PR の URL を報告する
   - merge 後にしか確かめられない項目があれば、一覧にして伝える
   - あわせて、merge して確かめたあとに `/issue-fix <番号>` を実行すれば、確認結果を issue に書き戻せると案内する

## merge 後の確認

close 済みの issue に未チェックの項目が残っているときに行う。コードは変えず、commit・push・PR の作成もしない。

1. 未チェックの項目を、確かめ方で 2 つに分けて一覧にする
   - agent が確かめられる項目: 本番の URL への `curl`、GitHub Actions の実行結果、`main` の内容など
   - 人にしか確かめられない項目: Cloudflare の管理画面、実機のブラウザでの見た目など
2. agent が確かめられる項目を確かめる
3. 人にしか確かめられない項目は、ユーザーに結果を聞く。答えが無い項目は確かめていないものとして扱う
4. GitHub MCP の `issue_write`（method: `update`）で、issue 本文の Acceptance criteria のうち満たした項目を `- [x]` にする
   - 本文のほかの部分は変えない。手順 1 で読んだ本文をもとに、チェックボックスだけを書き換えた本文を渡す
5. コメントのテスト計画の確認結果を更新する
   - 既存のコメントの `- [ ]` を、GitHub MCP の `update_issue_comment` で `- [x]` にし、確かめた方法と結果を書き足す
   - 確認結果のコメントが無ければ、`add_issue_comment` で新しくコメントする
6. 満たさなかった項目と、確かめられなかった項目は `- [ ]` のまま残し、その理由をコメントに書く
7. 更新した項目と、`- [ ]` のまま残した項目を報告する

## してはいけないこと

- `main` への push・PR の merge・deploy（`wrangler deploy` など）
- merge 後の確認で、コードを変えること・commit・push・PR を作ること
