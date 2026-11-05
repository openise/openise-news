# openise-news

## Daily News の定期起動

毎日 00:47 JST に Cloudflare Workers の Cron Triggers から GitHub Actions の
Daily News を起動する。設定・切り替え・確認・復旧の手順は
[運用手順](docs/daily-news-trigger.md)を参照する。

## Workers AI の使用量

「今日のピックアップ」の作成（`scripts/news/curate_news.py`）では Cloudflare Workers AI を使っている。実行回数や候補の数を増やすときは、次の目安で無料枠に収まるかを判断する。

### モデルと単価

- モデル: `@cf/google/gemma-4-26b-a4b-it`
- 単価: 100 万トークンあたり入力 9,091 Neurons、出力 27,273 Neurons（`curate_news.py` の `MODEL` のコメントより）

### 1 回の実行の使用量

| 項目 | トークン数 | Neurons |
|---|---|---|
| 入力（候補 42 件） | 1,462 | 約 13 |
| 出力 | 330 | 約 9 |
| 合計 | 1,792 | 約 22 |

2026-11-04 の Daily News の手動実行（https://github.com/openise/openise-news/actions/runs/41789482765 ）の実績。

多めに見積もると、1 回 70 Neurons 前後になる。

- 出力は `MAX_TOKENS = 1500` までなので、最大で約 41 Neurons
- 入力は候補の数にほぼ比例する。候補が 80 件ほどに増えても約 25 Neurons（約 2,800 トークン）

### 無料枠

- 1 日 10,000 Neurons。毎日 00:00 UTC（09:00 JST）にリセットされる
- 出典: [Workers AI の料金ページ](https://developers.cloudflare.com/workers-ai/platform/pricing/)（2026-11-04 に確認。ページの最終更新は 2026-10-20）。モデルの単価も同じページの値と一致する
- 上限を超えると、その日のリクエストはエラーになる。Workers Paid プランなら、超えた分は 1,000 Neurons あたり $0.011 で課金される
- 1 回 22〜70 Neurons なので、毎日 1 回の自動実行に数回の手動実行を足しても十分に収まる

### 実際の使用量を確かめる場所

- Cloudflare のダッシュボードの Workers AI の画面
- GitHub Actions の Daily News のログ。「Workers AI でピックアップを作る」ステップに、次の行が出る

  ```
  [INFO] Workers AI (@cf/google/gemma-4-26b-a4b-it) トークン数: 入力 1462 / 出力 330 / 合計 1792
  ```
