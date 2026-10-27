#!/usr/bin/env bash
# Threads トークンを暗号化ファイル(ig/threads/token.enc)から読み出して後続ステップの環境変数にする。
# 復号鍵はシークレット TH_APP_SECRET。TH_TOKEN シークレットが直接設定されていればそちらを優先。
set -e
if [ -z "$TH_TOKEN" ] && [ -f ig/threads/token.enc ] && [ -n "$TH_APP_SECRET" ]; then
  t=$(openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -a -A -pass env:TH_APP_SECRET -in ig/threads/token.enc)
  echo "::add-mask::$t"
  echo "TH_TOKEN=$t" >> "$GITHUB_ENV"
  echo "Threads token loaded"
elif [ -n "$TH_TOKEN" ]; then
  echo "::add-mask::$TH_TOKEN"; echo "TH_TOKEN=$TH_TOKEN" >> "$GITHUB_ENV"
fi
