# Openise News のレビュー基準

## 対象とルールソース

パスとコマンドはすべてリポジトリルートを基準にする。このファイルはレビュー時に読む規約であり、自動実行される設定ではない。

- 作業・言語・検証の原則: `CLAUDE.md`（`AGENTS.md` は同じファイルへのリンク）
- issue 対応と PR の作成: `.claude/skills/c-issue-fix/SKILL.md`
- サイト: `src/**/*.astro`、`src/**/*.ts`、`src/styles/global.css`、`public/_headers`
- News の取得・保存・キュレーション: `scripts/news/*.py`
- 定期実行: `.github/workflows/daily-news.yml`、`workers/daily-news-trigger/index.ts`
- 設定: `package.json`、`tsconfig.json`、`astro.config.mjs`、`vitest.config.ts`、`wrangler.jsonc`、`workers/daily-news-trigger/wrangler.jsonc`
- 運用の前提: `docs/daily-news-trigger.md`

`src/content/news/*/index.md` は生成される記事データとして扱う。`node_modules/`、`dist/`、`.astro/` はレビュー対象から除く。`package-lock.json` は依存関係の変更に合わせて確認し、生成された名前や形式にソースコードの命名基準を適用しない。

## 自動チェック

`CLAUDE.md` の次のコマンドを使う。チェックの成功と、人が仕様を確認した結果を区別する。

| コマンド | 確認すること |
| --- | --- |
| `npm run check` | Astro・TypeScript の型と診断 |
| `npm test` | `vitest.config.ts` に基づく TypeScript・Astro・worker のテスト |
| `npm run build` | 静的ページの生成 |
| `python3 -m pytest scripts/news/tests` | News スクリプトと workflow の回帰テスト |

Python の開発依存は `requirements-dev.txt` に定義される。`npm run preview:workers` はビルド後の手動確認用であり、自動チェックの代わりにはしない。lint や網羅率のコマンド・しきい値は定義されていないため、存在する前提で指摘しない。

## テスト配置と対応の探し方

隣接ファイルだけでテストの有無を判定しない。まず下表の場所を探し、対象関数の import・呼び出し・検証内容まで読む。ファイル名が一致することだけで十分な検証があるとも判断しない。

| 実装 | 対応するテスト |
| --- | --- |
| `scripts/news/<module>.py` | `scripts/news/tests/test_<module>.py`。例: `fetch_hn.py` → `test_fetch_hn.py`、`curate_news.py` → `test_curate_news.py` |
| 複数の News スクリプトにまたがる仕様 | `scripts/news/tests/test_news_target_date.py`、`test_news_markdown.py`、`test_paths.py` |
| `.github/workflows/daily-news.yml` | `scripts/news/tests/test_daily_news_workflow.py`（外部コマンドをモックして実際の shell 部分を検証） |
| `src/domain/*.ts`、`src/constants/typography.ts` | 隣接する `*.test.ts` |
| `src/scripts/client/*.ts` | 隣接する `*.test.ts` または `*.dom.test.ts` |
| `src/components/*.astro`、`src/layouts/*.astro` | 隣接する `*.test.ts`。CSP は `src/layouts/headers.test.ts` も確認 |
| `src/pages/index.astro`、`about.astro`、`404.astro` | `src/pages/_index.test.ts`、`src/pages/_about.test.ts`、`test/pages.test.ts` |
| `src/pages/news/[...page].astro`、`[id].astro` | `src/pages/news/_news-index.test.ts`、`_news-detail.test.ts` |
| `workers/daily-news-trigger/index.ts` | `workers/daily-news-trigger/index.test.ts` |

Astro ページのテスト名の先頭 `_` はページとして生成されないための配置であり、命名不一致として扱わない。`?raw` によるソース文字列の検証と Astro Container による描画結果の検証を区別する。前者が存在しても実際の生成経路・表示の検証済みとはしない。content loader と Pagination の振る舞いの検証不足は issue #152 で扱う。

## 名前と中間変数

- 文字数ではなく、用途を読み違えるか、離れた定義を何度も追う必要があるかで判断する。修正を提案するときは実際に曖昧な対象と改善する読み方を示す。
- 狭い範囲の添字 `i`、例外 `e`、ファイル `f` は、ループ・`except`・`with` から役割が分かるなら維持する。複数の同種の値を扱う、スコープが広い、別の意味で使い回す場合は意味の分かる名前にする。
- 記事・候補などを表す短い変数も周囲の処理から対象が一意なら許容する。長い分岐や複数のデータ変換をまたいで意味が変わるなら改名を検討する。一律の置換はしない。
- 参照が 1 回でも、業務上の意味を付ける値、長い式の分解、評価順序や取得時点の固定、複雑な API 引数の準備は中間変数を維持する。対象日の固定値や期間の始点・終点をインライン化して再計算しない。
- 元の式を見なければ意味が分からず、分割によってかえって追跡が増える別名だけなら削除を検討する。参照回数だけで不要と判定しない。

## CLI 出力と運用ログ

- `scripts/news/` の記事一覧、保存先、進捗、取得件数、スキップ理由は CLI の利用者向け出力として許容する。`print` を使っていることだけでデバッグ出力としない。
- `[WARN]`・`[ERROR]` の標準エラー出力と、処理を継続できない場合の終了コードを維持する。個別ソースのスキップと、ファイル保存やキュレーション全体の失敗を区別する。
- workflow のサマリー・既存 PR の再利用・通信失敗のログは運用判断に必要な出力として扱う。成功のログだけに置き換えたり、例外を握りつぶしたりしない。
- `workers/daily-news-trigger/index.ts` の `console.error` と例外は失敗の通知、`console.log` は起動要求の受理の記録として維持する。
- worker のトークン、Authorization ヘッダー、API 応答本文、通信例外の原文はログや例外に含めない。固定メッセージと HTTP ステータスで診断し、秘密情報を含む原文を追加する提案はしない。対応する `index.test.ts` の秘密情報が出ない検証を維持する。
- 一時的な値のダンプや、同じ事象を無目的に繰り返す出力は削除を検討する。出力の削除は、利用者と運用上の用途を確認してから行う。

## 指摘の記録

2026-11-06 の M11・M13・L3 の全列挙と修正・維持の判断は `docs/news-review-20261106.md` に記録する。

修正候補には対象のファイルと関数、具体的な保守上の問題、修正または維持の理由、確認したテストを記録する。例外は用途とスコープで説明し、短い名前・中間変数・出力全体を無条件に除外しない。

型キャスト・非 null 表明の個別判断は issue #151、News ページ生成・描画の追加検証は issue #152 の範囲とする。指摘件数を減らすことを目的とする改名・インライン化・ログ削除・テスト移動は行わない。
