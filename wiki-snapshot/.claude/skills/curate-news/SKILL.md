---
name: curate-news
description: Use when a News file needs manual curation for its 「今日のピックアップ」 section
predecessors: []
successors: []
---

# curate-news

Openise Wiki が owner の News を手動でキュレーションし、対象日の News ファイルを commit して現在 branch の upstream へ push する。この手順はユーザーが手動で skill を起動した場合に限る。cron による定期取得にキュレーション・ commit ・ push を追加しない。

## 手順

### 1. 対象ファイルを特定する

`$ARGUMENTS` が渡されていれば日付として使う（例: `20260304`）。渡されていない場合は今日の日付（`YYYYMMDD`）を使う。

対象ファイル: `src/content/news/YYYYMMDD/index.md`

ファイルが存在しない場合はユーザーに確認する。

### 2. ファイルを読み取る

6 ソースのデータを読み取り、各アイテムのタイトル・URL と、数値列がある場合はスコアを把握する。

### 3. ピックアップを最大 10 件選ぶ

以下の基準で選定する：

- **数値の高さ**: はてな のブクマ数・ HN の Points が高いもの。同じソース内の比較に使う
- **クロスソース優先**: 複数ソースで話題になっているトピックは優先
- **多様性**: 同じトピックが被らないよう調整
- **技術・開発寄り**: Claude Code・AI・開発ツール等ユーザーの興味関心に合ったものを優先
- **過去 30 日間の重複除外**: 手順 1 の対象日を基準に、30 日前から前日まで（両端を含む）の `src/content/news/YYYYMMDD/index.md` を確認する。存在する記事の「今日のピックアップ」セクションだけを読み取り、選出済みの URL と一致する候補は原則除外する。収集元の表だけにある URL は選出履歴に含めない。記事がない日は飛ばし、参照範囲を短縮したり、30 記事が揃うまで遡ったりしない。31 日前と対象日以降の記事は参照しない。期間内の記事がなければ履歴による除外は行わない
- **新情報がある場合の例外**: 取得済みデータから、過去の選出時にはなかった具体的なリリース・機能追加・仕様変更などを確認できる場合だけ、同一 URL の再選出を認める。紹介文の言い換え・スコアの増加・Trending への再登場だけでは新情報と扱わない。根拠を確認できない場合は除外を維持する。再選出時は手順 4 のコメントに新情報と再選出理由を記載する

数値列があるのは はてな と HN だけ。Reddit ・ GitHub Trending ・ Qiita ・ Zenn など数値の無いソースは数値を書かない。過去 30 日間の重複を除外したうえで、クロスソース・多様性・技術・開発寄りの基準を優先し、数値は同じソース内で候補を絞る補助に使う。数値の無いソースもこれらの基準で選定する。

適切な候補が 10 件未満の場合は、その件数だけを選ぶ。件数を埋めるために重複候補を戻さない。候補が 0 件の場合は、選出できる候補がなかった旨をピックアップセクションに記載する。

### 4. 一言コメントを生成する

各ピックアップについて、タイトル・ソースと、取得データにある数値から：

- なぜ話題になっているかの文脈
- 読む価値や注目ポイント

を 1〜3 文で書く。新情報の例外で再選出する場合は、確認できた更新内容と再選出理由も含める（例: 「以前紹介したツールに、今回取得したデータで新しい連携機能の追加が明記されています。この機能追加を新情報として再選出しました。」）。**本文取得（WebFetch）は行わない**。

### 5. フロントマターの title・description を更新する

ピックアップ内容をもとにフロントマターを更新する。title は核心テーマ（日付不要）、description は 1〜2 件のサマリー。

例: `references/frontmatter-example.md` を参照

### 6. セクションを追記する

`## 今日のピックアップ` セクションは **フロントマター直後（本文の先頭）** に挿入する。既存のソースデータ（はてな・HN・Reddit の表）より前に来るようにする。

以下の形式で記述する（参照: `references/format-example.md`）:

注意点:
- タイトル行は `N. **[title](url)**  `（末尾に半角スペース 2 つ = ハードブレーク）
- `*ソース:*` 行はインデントなし（flush-left）
- コメント文のインデントは項目番号の桁数に合わせる（`1. `→3 スペース、`10. `→4 スペース）
- 生成する日本語には日英 spacing を適用する。

### 7. 対象ファイルを commit する

`YYYYMMDD` は手順 1 の対象日付に置き換える。まず次のコマンドで対象ファイルの状態を確認する。

```bash
git status --porcelain -- src/content/news/YYYYMMDD/index.md
```

コマンドの成功を確認し、出力が空のときだけ commit ・ push を行わず「変更なし」と報告する。未追跡（`??`）・変更済み・ stage 済みの出力があれば、次のコマンドで commit へ進む。

```bash
git add -- src/content/news/YYYYMMDD/index.md
git commit -m "news YYYYMMDD: 今日のピックアップを更新" -- src/content/news/YYYYMMDD/index.md
```

各コマンドの成功を確認してから次へ進む。対象ファイルだけを pathspec で指定し、無関係な変更や staged file を含めない。commit message は `.claude/commit-patterns.json` の `news YYYYMMDD:` pattern に従う。

stage ・ hook ・ commit に失敗した場合は停止し、キュレーションの更新状況と失敗理由を報告する。commit が成功していなければ push しない。`--no-verify` や hook を無効化する環境変数は使わない。

### 8. 現在 branch の upstream へ push する

commit 成功後、`git log -1 --format='%h %s'` で commit を記録する。`git branch --show-current` で現在 branch を取得し、`git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'` で設定済み upstream を確認する。

upstream が未設定、または detached HEAD の場合は停止する。ローカル commit は完了したが push は未実施であることを報告し、upstream を自動設定しない。

現在 branch の `branch.<branch>.remote` と `branch.<branch>.merge` を `git config --get` で取得し、取得した remote と完全な ref を次の形で指定する（例: `origin` と `refs/heads/main`）。

```bash
git push <remote> HEAD:<upstream-ref>
```

現在 branch の設定済み upstream のみを送信先とし、`--all` ・ `--force` ・ `--no-verify` は使わない。push は branch の未送信 commit も送るため、対象ファイル以外を今回の commit に含めないことと区別する。

pre-push hook または push が失敗した場合は停止し、ローカル commit は成功・ push は失敗として理由を報告する。自動の pull ・ rebase ・再 commit で回避しない。

### 9. 報告する

選定した理由とピックアップ一覧、対象ファイル、commit hash、push 先と実行結果をユーザーに伝える。失敗時は完了した段階と未完了の段階を区別し、push コマンドの成功を確認する前に remote 反映済みと報告しない。
