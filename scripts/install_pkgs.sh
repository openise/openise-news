#!/bin/bash
set -euo pipefail

# ローカル環境では依存関係を勝手に入れ直さないよう、クラウドセッションに限定する
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Astro プロジェクト作成前は package-lock.json が無いため何もしない
if [ ! -f package-lock.json ]; then
  exit 0
fi

npm ci

# News 取得スクリプトは標準ライブラリのみで動くため、入れるのはテスト用の pytest だけ
pip install --quiet -r requirements-dev.txt
