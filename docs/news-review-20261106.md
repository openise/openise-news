# News のレビュー候補の確認記録（2026-11-06）

issue #150 の確認記録。ユーザーが共有した `openise-daily/src/content/projects/openise-news/code-review-20261106.md` の M11・M13・L3 を、`code-reviewer-config.md` に照らして再判定した。

元の行番号はそのレポートの位置を識別するために残す。現在の行番号とは異なるため、同じ名前の列挙を関数・用途と照合する。基準となる現在の実装は #144 〜 #149 の修正を含む `ebbaf5b`。本記録は原本全体の複製ではなく、対象の列挙項目と判断を記録する。

## 修正するもの

| 元の候補 | 修正と理由 | 確認するテスト |
| --- | --- | --- |
| M11: `curate_news.py:281 data`、`:288 result` | `call_workers_ai` の API 応答全体を `response_payload`、その中のモデル応答を `model_result` にする。同じ関数で異なる階層の辞書を読み、検証・本文抽出・usage 取得を行うため、扱う階層を名前で区別する。JSON キー `result` と Request の引数 `data` は外部仕様として維持 | `scripts/news/tests/test_curate_news.py` の応答形式・usage・API 失敗の検証 |
| M11: `curate_news.py:353 c`、`:356 c` | `render_pickup` の候補を `candidate` にする。同じ処理に選定結果の `pick` と元記事の候補があり、id による対応付けと複数行の描画にまたがるため区別する | 同ファイルのピックアップ書式・要約のエスケープの検証 |

## 維持するものと理由

下の全列挙のうち上表以外は、次の用途ごとの判断を適用する。過去の修正で移動・変更されたものは現在の対応箇所を確認し、同じ処理を再導入しない。

| 候補と用途 | 判断の根拠 |
| --- | --- |
| M11: 例外 `e`、ファイル `f` | `except`・`with` の範囲で対象が分かる。長い名前への一律置換をしない。収集の保存処理は #148 の `save_news_atomic`、履歴読み込みは #149 の `iter_history_news` に移ったものも確認 |
| M11: 内包表記・短いループの `e`・`h`・`p`・`a`・`s`・`t`・`u`・`m`・`v`・`r`・`k`・`c` | 記事、投稿、タグ、URL、正規表現の一致、並べ替えキーなど、直近のコレクションとアクセスするキーで意味が分かる。`render_pickup` の複数の対象を扱う箇所だけは上表のとおり修正。`pagination.ts` の `a`・`b` も数値比較 `a - b` に閉じるため維持 |
| M11: API パーサーの `data` | HN・Qiita・Zenn は 1 回の応答を検証して必要なフィールドを取り出す範囲で閉じる。`fetch_repo_description` も単一応答の description の抽出。`fetch_github_trend.py` の `handle_data(data)` は HTMLParser のコールバック引数として保持 |
| M11: `describe_finish(result)`、テストの `result` | 前者はモデル応答だけを引数として診断する関数。後者は同じテスト内の対象関数の戻り値を直後に検証する。複数階層の辞書を切り替えないため維持 |
| M13: 定数・正規表現・関数・schema | `USER_AGENT`・`BASE_DIR`・`HISTORY_DAYS`・`MAX_PAGE_SLOTS`・`withPage`・`dateString` 等は設定値・仕様・役割の名前。モジュール外の利用もあり、ローカルの参照回数だけでは不要といえない |
| M13: 取得・変換・描画の中間結果 | `payload`・`request`・`raw`・`errors`・`entries`・`ranked`・`chosen`・`priority`・`link`・`stars`・`likes`・`source`・`indent` 等は段階や意味を付け、複雑な引数・f-string を分解する。#148 のソース別解析に移った score・description も維持 |
| M13: 日付・期間・出力ファイル・節 | `start`・`end`・`now`・`date`・`date_str`・`datetime_str`・`filename`・`hb`・`hn`・`rd`・`gt`・`qt`・`zn` 等は対象日時や書式、ソース別の結果を表す。評価時点・呼び出し順を維持し、期間の境界や生成内容を追いやすくする |
| M13: UI の値とテストの準備・結果 | `navItems`・`currentPath`・`isCurrent`・`pageTitle`・`canonicalURL`・`themeBootstrapScript`・`current`、テストの fixture・HTTP 応答・HTML・DOM・検証結果は準備／実行／検証を区別する。`originalNews`・`originalItems` は変更前の状態を保存するので維持 |
| M11・M13: `constants.py` の旧 RSS パーサー内の値 | #147 で本番未使用のパーサーがテスト helper `_parse_rss_items` に移動済み。テスト側の title・url・entries は入力解析の段階として維持し、本番へは戻さない |
| L3: 取得元・進捗・件数・保存先・記事一覧 | CLI の利用者向け表示と workflow の運用ログ。`print` の使用自体は問題にしない。logger への全面置換は標準出力／標準エラーの契約や表示形式を変えるため行わない |
| L3: 警告・保存失敗・キュレーション失敗 | 部分的なスキップと全体の失敗を判別する出力。#144 の保存失敗の非ゼロ終了、ファイル保全、外部応答検証を維持。#148 で移動したログも維持 |
| L3: worker の 4 出力 | 3 箇所の固定したエラーログと 1 箇所の受理ログは `docs/daily-news-trigger.md` の確認手順で使う。失敗時の throw と、token・応答本文・通信例外の原文を出さない振る舞いを維持 |

M13 の列挙には同一位置の `test_fetch_ai_news.py:1064 urls` が 2 回含まれる。原本との照合のため、以下でも両方を残して 394 件として数える。「1 回だけ参照する」という判定そのものを正しいと仮定せず、定数・関数・保存用の値も用途から再判定した。今回インライン化が必要な項目はない。

## L4 とテスト配置

レポートに列挙された `constants.py`・`curate_news.py`・`fetch_ai_news.py`・`fetch_github_trend.py`・`fetch_hb.py`・`fetch_hn.py`・`fetch_qiita.py`・`fetch_reddit.py`・`fetch_zenn.py` には `scripts/news/tests/test_<module>.py` がある。#149 の `news_markdown.py` も同じ規約で対応する。Python の配置を変更する必要はない。

TypeScript の隣接テスト、Astro の `_*.test.ts`・`test/pages.test.ts`、worker の隣接テストを config に明記した。News ページのソース文字列テストを描画検証と数えない。`src/content.config.ts` の ID 生成と `src/components/Pagination.astro` の描画の検証追加は issue #152、型表明は issue #151 で扱う。

## 原本の全列挙との対応

表の値は `名前 @ 元の行番号`。同じファイル・名前をまとめても列挙された位置を省略しない。M11 の修正 4 項目以外は上記の用途ごとの理由で維持または移動済みと判断した。

### M11: 146 件

| ファイル | 元の列挙箇所 |
| --- | --- |
| `scripts/news/constants.py` | `e @ 128, 192, 66, 76, 79, 82`、`p @ 66` |
| `scripts/news/curate_news.py` | `c @ 119, 215, 229, 322, 353, 356, 404, 406`、`m @ 168`、`f @ 179, 376, 394`、`data @ 200, 281`、`e @ 201, 204, 274, 277, 282, 297, 314, 445`、`result @ 236, 288`、`t @ 250` |
| `scripts/news/fetch_ai_news.py` | `h @ 123, 128, 137`、`p @ 155, 178`、`k @ 168, 169`、`e @ 199, 214, 217, 220, 230, 243, 252, 81, 89, 98`、`u @ 212`、`f @ 363, 59`、`m @ 65` |
| `scripts/news/fetch_github_trend.py` | `data @ 74` |
| `scripts/news/fetch_hb.py` | `e @ 129, 163, 213`、`f @ 171`、`t @ 210, 214, 87` |
| `scripts/news/fetch_hn.py` | `f @ 139`、`data @ 47`、`e @ 48`、`h @ 71` |
| `scripts/news/fetch_qiita.py` | `data @ 82`、`e @ 83, 86` |
| `scripts/news/fetch_reddit.py` | `p @ 166`、`s @ 176, 217, 235, 237`、`f @ 242`、`h @ 68` |
| `scripts/news/fetch_zenn.py` | `data @ 27`、`e @ 28, 66`、`a @ 38` |
| `scripts/news/tests/test_constants.py` | `result @ 123, 149, 167, 180, 196, 213, 230, 245, 252, 261, 267, 277, 282, 288, 294, 300, 306, 313, 321, 329, 337, 345, 361`、`e @ 124, 456` |
| `scripts/news/tests/test_curate_news.py` | `result @ 454, 576` |
| `scripts/news/tests/test_fetch_ai_news.py` | `v @ 1049`、`r @ 278`、`u @ 428, 446` |
| `scripts/news/tests/test_fetch_github_trend.py` | `e @ 139, 38, 48` |
| `scripts/news/tests/test_fetch_hb.py` | `result @ 112, 153` |
| `scripts/news/tests/test_fetch_hn.py` | `result @ 34, 55, 65, 85` |
| `scripts/news/tests/test_fetch_qiita.py` | `e @ 107, 117, 63, 73` |
| `scripts/news/tests/test_fetch_reddit.py` | `result @ 117, 128, 135, 198, 212, 225, 243, 46`、`p @ 119, 120, 200, 214, 227, 228, 245, 246, 262`、`e @ 80` |
| `scripts/news/tests/test_fetch_zenn.py` | `e @ 62, 68, 74` |
| `src/domain/pagination.ts` | `a @ 12`、`b @ 12` |

### M13: 394 件

| ファイル | 元の列挙箇所 |
| --- | --- |
| `scripts/news/constants.py` | `title @ 142`、`url @ 143`、`parse_limit @ 167`、`USER_AGENT @ 19`、`_MD_ESCAPE_RE @ 197`、`_URL_UNSAFE_CHARS @ 201`、`req @ 71` |
| `scripts/news/curate_news.py` | `request @ 197, 265`、`score @ 230`、`description @ 231`、`payload @ 256`、`raw @ 273`、`detail @ 275`、`errors @ 285`、`valid_ids @ 322`、`BASE_DIR @ 33`、`by_id @ 353`、`source @ 357`、`indent @ 358`、`API_URL @ 38`、`text @ 395`、`MAX_TOKENS @ 40`、`GITHUB_REPO_API @ 41`、`picks @ 419`、`_GITHUB_REPO_RE @ 42`、`date @ 436`、`SOURCES @ 48`、`_CELL_SPLIT_RE @ 59`、`_ROW_RE @ 60`、`_THINK_RE @ 61`、`SYSTEM_PROMPT @ 63` |
| `scripts/news/fetch_ai_news.py` | `start @ 111`、`title @ 138`、`url @ 139`、`link @ 140, 179, 200, 231, 253, 99`、`ranked @ 154`、`priority @ 165`、`chosen @ 168`、`stars @ 201`、`token @ 216`、`likes @ 232`、`WEEKDAYS @ 265`、`datetime_str @ 274`、`date_str @ 275`、`hb @ 278`、`hn @ 281`、`rd @ 284`、`gt @ 287`、`qt @ 290`、`zn @ 293`、`lines @ 295`、`HISTORY_DAYS @ 35`、`REDDIT_MIN_POSTS_PER_SUBREDDIT @ 41`、`entries @ 77` |
| `scripts/news/fetch_github_trend.py` | `searchable @ 103`、`_STARS_TODAY_RE @ 23` |
| `scripts/news/fetch_hb.py` | `_ENTRY_BLOCK_RE @ 105`、`body @ 128`、`now @ 150`、`link @ 164`、`filename @ 182`、`search_tags @ 210`、`entry_tags @ 214`、`md @ 221`、`items @ 78`、`tags_raw @ 86`、`tags @ 87` |
| `scripts/news/fetch_hn.py` | `filename @ 100`、`filter_label @ 126`、`md @ 138`、`ALGOLIA_BASE @ 24`、`HN_BASE @ 25`、`url @ 41, 73`、`title @ 72`、`link @ 74`、`points @ 75`、`comments @ 76`、`date_str @ 82`、`datetime_str @ 83`、`title_suffix @ 84`、`lines @ 86` |
| `scripts/news/fetch_qiita.py` | `FEED_URL @ 27`、`ITEM_API @ 29`、`_ITEM_PATH_RE @ 30`、`DIGEST_TITLE_MARKER @ 35`、`request @ 79` |
| `scripts/news/fetch_reddit.py` | `fetch_size @ 116`、`url @ 117, 75`、`link @ 167`、`period_label @ 175`、`subreddit_names @ 176`、`datetime_str @ 177`、`filename @ 196`、`multi_results @ 234`、`total @ 238`、`md @ 241`、`AI_SUBREDDITS @ 31`、`MEDIA_HOSTS @ 39`、`_CONTENT_LINK_RE @ 41`、`PERIOD_LABEL @ 43`、`title @ 53`、`ns @ 82`、`REDDIT_MULTI_FETCH_SIZE @ 95` |
| `scripts/news/fetch_zenn.py` | `BASE_URL @ 21` |
| `scripts/news/tests/test_constants.py` | `entries @ 118, 129, 134, 454, 465, 480, 491, 500`、`result @ 123, 149, 167, 180, 196, 213, 230, 277, 294, 300, 306`、`titles @ 124`、`http_error @ 163`、`url_error @ 178`、`stderr @ 185`、`destination @ 364`、`root @ 380, 397, 415, 443, 452`、`billion_laughs @ 389, 407`、`feed @ 425` |
| `scripts/news/tests/test_curate_news.py` | `path @ 145, 183, 253, 269, 284, 322, 342, 430, 455, 466, 505, 515, 550`、`output @ 147, 184, 195, 232, 254, 270, 285, 302, 323, 343, 365, 387, 467, 494`、`rows @ 181`、`news @ 182, 218, 248, 266, 279, 298, 317, 338, 352, 382, 504`、`fake @ 197, 234, 256, 272, 287, 304, 325, 345, 496, 507, 517`、`body @ 431, 456, 578, 590, 86`、`urls @ 487` |
| `scripts/news/tests/test_fetch_ai_news.py` | `html @ 1013`、`lines @ 1025, 1116, 1123, 1131, 1162, 212, 225, 236, 245, 377, 414, 432, 557, 569, 583, 629, 637, 799, 810, 825, 845, 859, 908, 935, 955, 965`、`start @ 1061`、`end @ 1062`、`urls @ 1064`、`now @ 1074, 1080, 706`、`hits @ 1106, 1129, 1150`、`excluded @ 1151, 464, 491, 529, 543, 555, 602, 616, 933, 953, 963`、`source_functions @ 1170, 645, 713, 736, 763, 973`、`entries @ 193, 207, 220, 232, 256, 271, 284, 314, 328, 347, 355, 375, 390, 411, 428, 446, 459, 473, 486, 501, 522, 542, 554, 567, 595, 615, 635, 914`、`body @ 227, 247, 349, 357`、`rows @ 262, 277, 434`、`utm @ 515`、`headings @ 666`、`markdown @ 678, 696`、`original_open @ 74`、`feed @ 762, 868, 888, 929, 952, 962`、`ranked @ 808, 819, 839, 855`、`media @ 867, 887` |
| `scripts/news/tests/test_fetch_github_trend.py` | `html @ 112, 126, 96`、`entries @ 24, 46, 53` |
| `scripts/news/tests/test_fetch_hb.py` | `path @ 100`、`result @ 112, 153`、`md @ 122`、`stderr @ 156`、`entries @ 199`、`_ENTRY_LIST_HTML @ 29`、`matches @ 84`、`now @ 98` |
| `scripts/news/tests/test_fetch_hn.py` | `lines @ 110, 126, 98`、`hits @ 117, 96`、`url @ 22`、`payload @ 31`、`result @ 34, 55, 65, 85` |
| `scripts/news/tests/test_fetch_qiita.py` | `entries @ 105, 115, 49, 71, 78`、`EMPTY_FEED @ 32` |
| `scripts/news/tests/test_fetch_reddit.py` | `requested_url @ 105, 94`、`raw @ 110, 125, 18, 192, 209, 218, 232, 250`、`result @ 128, 135, 198, 212, 46`、`argv @ 147, 159, 173`、`ranked @ 259`、`now @ 35`、`path @ 37`、`html @ 72`、`entry_xml @ 80` |
| `scripts/news/tests/test_fetch_zenn.py` | `entries @ 37`、`body @ 58, 78` |
| `scripts/news/tests/test_paths.py` | `now @ 22, 29, 36` |
| `src/components/ContentCard.test.ts` | `headingHtml @ 28`、`rule @ 40` |
| `src/components/Header.astro` | `navItems @ 4`、`currentPath @ 8`、`isCurrent @ 9` |
| `src/components/Header.test.ts` | `labels @ 20`、`newsHtml @ 38` |
| `src/domain/news.test.ts` | `originalItems @ 52` |
| `src/domain/pagination.ts` | `MAX_PAGE_SLOTS @ 3` |
| `src/domain/routes.ts` | `withPage @ 6` |
| `src/layouts/BaseLayout.astro` | `pageTitle @ 22`、`canonicalURL @ 24`、`themeBootstrapScript @ 25` |
| `src/layouts/BaseLayout.test.ts` | `unavailableStorage @ 40` |
| `src/layouts/ContentLayout.test.ts` | `window @ 13` |
| `src/layouts/headers.test.ts` | `html @ 26`、`scriptSrc @ 28`、`csp @ 38` |
| `src/pages/_about.test.ts` | `window @ 12`、`headings @ 23`、`hrefs @ 39` |
| `src/pages/_index.test.ts` | `window @ 24`、`originalNews @ 29` |
| `src/schemas/content.ts` | `dateString @ 3` |
| `src/scripts/client/theme-contract.ts` | `THEME_STORAGE_KEY @ 3`、`THEME_MEDIA_QUERY @ 4` |
| `src/scripts/client/theme.ts` | `current @ 34` |
| `test/pages.test.ts` | `window @ 45` |

### L3: 62 件

| ファイル | 元の列挙箇所 |
| --- | --- |
| `scripts/news/constants.py` | `print(...) @ 123, 129, 157, 189, 193, 194, 77, 80, 83` |
| `scripts/news/curate_news.py` | `print(...) @ 183, 202, 205, 400, 408, 413, 421, 428, 440, 446` |
| `scripts/news/fetch_ai_news.py` | `print(...) @ 277, 280, 283, 286, 289, 292, 350, 375, 380, 389, 390` |
| `scripts/news/fetch_github_trend.py` | `print(...) @ 100, 93` |
| `scripts/news/fetch_hb.py` | `print(...) @ 120, 130, 173, 211, 219, 223, 64` |
| `scripts/news/fetch_hn.py` | `print(...) @ 128, 130, 136, 142, 49, 53, 58` |
| `scripts/news/fetch_qiita.py` | `print(...) @ 72, 84, 87, 91` |
| `scripts/news/fetch_reddit.py` | `print(...) @ 118, 239, 244, 245, 76` |
| `scripts/news/fetch_zenn.py` | `print(...) @ 29, 34, 54` |
| `workers/daily-news-trigger/index.ts` | `console.error(message); @ 34, 40, 9`、`console.log("Daily News の起動リクエストが受理されました（main、force=false）"); @ 44` |
