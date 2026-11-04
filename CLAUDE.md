# CLAUDE.md

## プロジェクト

- Openise News: AI 関連ニュースを毎日収集し、ピックアップを公開する Astro 製の静的サイト
- 公開先: Cloudflare Workers（https://news.openise.jp/）
- 公開は `main` への merge を契機に Workers Builds が行う（設定は `wrangler.jsonc`）

## 開発の進め方

- 開発は Claude Code のクラウドセッションで行う
- issue は GitHub Issues で管理する。コード修正は issue に紐づける
- agent は main への push と deploy（`wrangler deploy` など Cloudflare アカウントを操作するコマンド）をしない
- 作業ブランチに push して PR を作成するまでにとどめる。merge は人が行う

## 言語

- 日本語で書くもの: 応答、ドキュメント、コードコメント、コミットメッセージ、PR のタイトルと説明、ユーザー向けのエラーメッセージとログ
- 英語のまま残すもの: コード、インラインコード、URL、技術用語と固有名詞、ファイル名、npm パッケージ名
- 日本語と英単語・数字が混在する文では、英単語・数字の前後に半角スペースを入れる（コードブロック・インラインコード・URL は除く）
  - 例:「Astro フレームワーク」「100 件」

## 作業の原則

- コーディングの前に考える: 前提を明示する。解釈が複数あれば提示する。不明点は質問する
- シンプルさ第一: 求められた以上の機能・抽象化・設定項目を足さない
- 外科手術的な変更: 依頼に関係する箇所だけを変える。隣接コードを勝手に改善しない。自分の変更で不要になったものだけを消す
- ゴール駆動: 検証できる成功基準を決め、テストやコマンドで確かめてから完了とする
- コードコメントには、コードから分からない理由（WHY）だけを書く

## issue の書式

- タイトル: `<type>: <内容>`（type は commit と同じ）
- 本文は次の 3 節にする
  - `## 概要`: 背景と、何をするか
  - `## Acceptance criteria`: 完了条件を `- [ ]` のチェックリストで書く
  - `## テスト計画`: 完了をどう確かめるか
- ラベル（type）を 1 つ付ける: `bug`・`enhancement`（feature）・`documentation`・`refactor`・`chore`
- priority は付けない

## commit と PR の書式

- commit メッセージと PR タイトル: `<type>: <内容>`
  - type は `feat`・`fix`・`refactor`・`chore`・`docs`
  - 例:「chore: GitHub Issues 用の skill と規約を整える」
- PR の説明の先頭に `Closes #N` を書き、merge 時に issue が自動で close されるようにする
- merge 後の片付けは、ブランチの自動削除と `Closes #N` による issue の自動 close に任せる

## 検証コマンド

- `npm run check`: 型チェック（`astro check`）
- `npm test`: テスト（Vitest）
- `npm run build`: 静的サイトのビルド（出力先は `dist/`）
- `python3 -m pytest scripts/news/tests`: News 取得スクリプトのテスト（pytest は `requirements-dev.txt` で入れる。クラウドセッションでは `scripts/install_pkgs.sh` が入れる）
- `npm run preview:workers`（`wrangler dev`）は `npm run build` 後の `dist/` を Workers 上の挙動で確かめる確認用で、検証コマンドではない

## skill の使い分け

- `new-issue`: 依頼内容を issue にするとき。タイトル・3 節の本文・ラベルを提案し、了承を得てから作る
- `issue-fix`: 既存の issue を実装するとき。issue 番号を引数に渡す。実装・検証・commit・push・PR 作成・issue の Acceptance criteria のチェックとコメントまで行い、merge はしない
