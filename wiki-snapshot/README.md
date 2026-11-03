# wiki-snapshot

openise-wiki （ GitLab ）の News 機能の移植元ファイル。クラウドセッションは GitLab を clone できないため、このブランチに置いた。

- 取り込み元: openise-wiki `5a1a37a` （ 2026-11-03 ）
- パスは openise-wiki のリポジトリルートからの相対パスのまま
- このブランチ（ `import/wiki-news` ）は `main` に merge しない。移植の issue では、必要なファイルをここから読んで `main` 向けのブランチに書き直す
- 読み方: `git fetch origin import/wiki-news` のあと `git show FETCH_HEAD:wiki-snapshot/<パス>` 、または `git checkout FETCH_HEAD -- wiki-snapshot` で作業ツリーに展開し、 commit 前に消す

含めたもの:

- News のページ・ドメイン・スキーマとテスト（ `src/pages/news/` ・ `src/domain/news.ts` など）
- ページが使うレイアウト・コンポーネント・クライアントスクリプト・ `global.css` （ UI をどこまで移すかは移植の issue で決める）
- 取得スクリプトと pytest （ `scripts/news/` ）
- キュレーションの手順（ `.claude/skills/curate-news/` 。 Workers AI のプロンプトの元にする）
- 参考: `astro.config.mjs` ・ `package.json` ・ `pyproject.toml` ・ `src/markdown/plugins.ts`
- 表示確認用の News 3 件（ `src/content/news/20261031` 〜 `20261102` ）
