# Daily News の定期起動

起動専用の `openise-news-trigger` Worker が毎日 11:00 JST（02:00 UTC）に
GitHub API の `workflow_dispatch` を呼び、`main` の
`.github/workflows/daily-news.yml` を `force=false` で起動する。
Cron 式は `0 2 * * *`。GitHub Actions の実行待ち時間は残るため、公開時刻を保証するものではない。

コードと設定は `workers/daily-news-trigger/` に置く。公開サイトの
`wrangler.jsonc` とは別の Worker で、HTTP の公開 URL や起動用エンドポイントは作らない。
サイトの Workers Builds だけではこの Worker は公開されない。

## GitHub の認証情報

GitHub で fine-grained personal access token を作る。

- Resource owner: `openise`
- Repository access: `openise-news` のみ
- Repository permissions: Actions の Read and write（Metadata の Read は自動付与）
- 有効期限を設定し、失効前に Worker の secret を更新する

Worker の secret 名は `GITHUB_ACTIONS_TOKEN`。GitHub Actions 側の
`GITHUB_TOKEN` とは別に登録する。値はリポジトリ、Wrangler の vars、コマンド引数、
ログへ書かず、下記の対話入力で登録する。組織で token の承認が必要な場合は承認を済ませる。

## 初回の切り替え

Cloudflare の操作は管理者が行う。認証済みの端末で、リポジトリのルートから実行する。
この変更の merge で GitHub Actions の `schedule` が無くなるため、
次の 11:00 JST までに十分な余裕を持って切り替える。Cron 設定の反映には数分から 15 分程度かかることがある。
切り替えが間に合わない場合は、Daily News を手動実行する。

1. 最新の `main` を取得し、`npm ci` を実行する。
2. Worker の secret を登録する。

   ```sh
   npx wrangler secret put GITHUB_ACTIONS_TOKEN --config workers/daily-news-trigger/wrangler.jsonc
   ```

   新規 Worker の作成を聞かれたら、名前が `openise-news-trigger` であることを確認して作成する。
   この段階では Cron の処理コードは未公開なので、次の手順まで続ける。

3. 起動用 Worker と Cron を公開する。

   ```sh
   npx wrangler deploy --config workers/daily-news-trigger/wrangler.jsonc
   ```

4. Cloudflare の `openise-news-trigger` の設定で、secret 名が登録され、Cron が
   `0 2 * * *` になっていることを確認する。既存のサイト `openise-news` は変更しない。
5. GitHub の Daily News に `schedule` が無く、Run workflow から `main` と
   `force` を選べることを確認する。手動実行時の `force` の既定値は false のまま。
6. 最初の Cron 実行から News の公開まで、次の「確認」に従って確かめる。

通常のコード更新は手順 3 で反映する。token の更新は手順 2 を再実行する。
`secret put` や `deploy` は本番を変更するため、ローカルの検証とは分けて行う。

## 実行時刻の変更

Cron 設定を変更して merge した後は、管理者が最新の `main` を取得し、
上の手順 3 で起動用 Worker を再公開する。サイトの Workers Builds だけでは
Cron 設定は反映されない。次の 11:00 JST より 15 分以上前に反映し、
Cloudflare の Cron が `0 2 * * *` になっていることと、下記の起動・公開結果を確認する。
元の時刻へ戻す場合も、設定を revert してから起動用 Worker を再公開する。

## 確認

Cloudflare の Worker の Logs で、11:00 JST 頃の Cron 実行と次のログを確認する。
必要なら実行時刻の前から次のコマンドでログを見る。

```sh
npx wrangler tail --config workers/daily-news-trigger/wrangler.jsonc
```

- 成功: `Daily News の起動リクエストが受理されました（main、force=false）`
- 失敗: `Daily News の起動に失敗しました` から始まるログと、scheduled handler の失敗

成功ログは GitHub API が HTTP 204 で受理したことを表し、Actions の完了は表さない。
[Daily News の実行一覧](https://github.com/openise/openise-news/actions/workflows/daily-news.yml)で
`workflow_dispatch` の新しい実行、`main`、実行結果を確認する。
News の PR が作成・merge され、サイトの Workers Builds が成功し、
[本番サイト](https://news.openise.jp/)にその日の News が表示されるところまで確かめる。
その日の News が既にある場合、`force=false` では収集がスキップされる。
必要な再取得だけ手動で `force=true` を選ぶ。

HTTP 401・403 は token の期限・承認・Actions 権限を、404 はリポジトリへのアクセス権を、
422 は workflow と `main` の入力仕様を確認する。429・5xx・通信失敗は GitHub の状況を確認する。
通信が途切れても GitHub 側が受理している可能性があるため、再実行前に実行一覧を見る。
Worker は重複 dispatch を避けるため自動リトライを行わない。
エラーのログと例外には token、API の応答本文、通信例外の詳細を含めない。

切り替え後に issue #137 の未チェック項目へ、Cron の実行日時・Actions の実行 URL・
News の公開確認結果を書き戻す。

## 元に戻す

1. Cloudflare で `openise-news-trigger` の Cron Trigger を削除し、反映を確認する。
   二重の定期起動を防ぐため、GitHub 側の定期実行を戻す前に行う。
2. 作業ブランチと PR で `.github/workflows/daily-news.yml` の `on` に次を戻し、merge する。

   ```yaml
   schedule:
     - cron: "0 2 * * *"
   ```

3. GitHub Actions の定期実行が復旧するまで、必要な日だけ手動実行する。
4. Worker を再公開すると設定ファイルの Cron が再登録されるため、
   復旧を継続する場合は設定ファイルの `triggers.crons` も空配列にする。
   Worker を廃止する場合は Cloudflare で削除し、GitHub の token も失効させる。

コードの revert だけでは、Cloudflare 上の Cron と secret は消えない。

## ローカル検証

```sh
npm test
npm run check
npm run build
python3 -m pytest scripts/news/tests
npx wrangler deploy --config workers/daily-news-trigger/wrangler.jsonc --dry-run
```

Worker のテストは GitHub API をモックするため、本物の token の登録や workflow の起動は行わない。
`--dry-run` は Worker を bundle し、設定の検証を行う。Cloudflare への公開と Cron の動作確認は行わない。
