# キレイネ (kirei-ne.com)

美容医療の料金比較サイト。各クリニック公式サイトの料金だけを使い、安い順に比較します。

- `index.html` — アプリ本体(データは `data/*.json` から読み込み)
- `data/` — クリニック・料金・更新ログ(毎日更新)
- `about.html` / `terms.html` / `privacy.html` / `contact.html` — 運営者情報・規約など

静的サイトのため、ビルド不要でそのまま配信できます(Cloudflare Pages: Build command なし、出力ディレクトリ `/`)。
