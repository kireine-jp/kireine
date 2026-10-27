"""Build the public static site for kirei-ne.com into the repo folder.
Usage: python3 build.py <live_data_dir> <repo_dir>
live_data_dir holds clinics/*.json, prices/*.json, updates/*.json pulled from the artifact DB.
"""
import json, glob, os, sys, re, datetime, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo

LIVE, OUT = sys.argv[1], sys.argv[2]
APP = None  # set below
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app.html")
SITE = "https://kirei-ne.com"

def load(kind):
    rows = []
    for f in sorted(glob.glob(f"{LIVE}/{kind}/*.json")):
        d = json.load(open(f, encoding="utf-8"))
        d = d.get("data", d) if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) else d
        rows.append({"id": os.path.basename(f)[:-5], **d})
    return rows

clinics, prices, updates = load("clinics"), load("prices"), load("updates")
updates.sort(key=lambda u: u.get("date", ""), reverse=True)
os.makedirs(f"{OUT}/data", exist_ok=True)
for name, rows in (("clinics", clinics), ("prices", prices), ("updates", updates), ("reviews", [])):
    json.dump(rows, open(f"{OUT}/data/{name}.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---- index.html: app + read-only data shim ----
app = open(APP, encoding="utf-8").read()
app = re.sub(r"^<title>.*?</title>\n", "", app, count=1)
app = app.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
shim = open(f"{HERE}/shim.js", encoding="utf-8").read()
gjs = re.search(r"const GROUPS=(\[.*?\n\]);", app, re.S).group(1)
GROUPS = json.loads(subprocess.run(["node", "-e", "process.stdout.write(JSON.stringify(" + gjs + "))"], capture_output=True, text=True, check=True).stdout)
n_cl, n_pr = len(clinics), len(prices)
desc = f"美容皮膚科・美容クリニックの料金を公式サイトから毎日チェックして比較。ボトックス・ヒアルロン酸・リジュラン・シミ治療・医療脱毛を全国{n_cl}院・{n_pr}件の料金で安い順に。"
head = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>キレイネ｜美容医療の料金比較 ボトックス・ヒアルロン酸・リジュラン</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{SITE}/">
<meta name="theme-color" content="#e0306c">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="キレイネ">
<meta property="og:title" content="キレイネ｜美容医療の料金比較">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}/">
<meta property="og:image" content="{SITE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<style>body{{margin:0}}</style>
<script>window.KIREINE_PUBLIC=true;</script>
<script>{shim}</script>
</head>
<body>
"""
seo_css = "<style>.kn-seo{max-width:640px;margin:0 auto;padding:12px 16px calc(var(--tabh,64px) + 48px);font-size:12.5px;line-height:1.7;color:var(--muted)}.kn-seo b{display:block;color:var(--fg);font-size:13px;margin-top:6px}.kn-seo nav{display:flex;flex-wrap:wrap;gap:4px 14px;margin:4px 0 12px}.kn-seo a{color:var(--muted);text-decoration:underline;text-underline-offset:2px}</style>"
open(f"{OUT}/index.html", "w", encoding="utf-8").write(head + app + "\n" + seo_css + seo.home_links(clinics, prices, GROUPS) + "\n</body>\n</html>\n")

# ---- legal / info pages ----
OP = json.load(open(f"{HERE}/operator.json", encoding="utf-8"))
css = open(f"{HERE}/page.css", encoding="utf-8").read()
def page(slug, title, body):
    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}｜キレイネ</title>
<link rel="canonical" href="{SITE}/{slug}.html">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;600&display=swap">
<style>{css}</style>
</head>
<body>
<header><a class="logo" href="/"><i>¥</i>キレイネ<small>美容医療の料金比較</small></a></header>
<main>
<h1>{title}</h1>
{body}
</main>
<footer><nav><a href="/">トップ</a><a href="/about.html">運営者情報</a><a href="/terms.html">利用規約</a><a href="/privacy.html">プライバシーポリシー</a><a href="/contact.html">お問い合わせ</a></nav><p>© {datetime.date.today().year} キレイネ</p></footer>
</body>
</html>
"""
    open(f"{OUT}/{slug}.html", "w", encoding="utf-8").write(html)

tpl = {k: v for k, v in OP.items()}
for slug, title in (("about", "運営者情報"), ("terms", "利用規約"), ("privacy", "プライバシーポリシー"), ("contact", "お問い合わせ・掲載情報の修正依頼")):
    body = open(f"{HERE}/pages/{slug}.html", encoding="utf-8").read()
    for k, v in tpl.items():
        body = body.replace("{{" + k + "}}", v)
    page(slug, title, body)

# ---- SEO pages ----
for d in ["clinic"] + [g["id"] for g in GROUPS] + [s for _, s in seo.PREFS]:
    if os.path.isdir(f"{OUT}/{d}"): shutil.rmtree(f"{OUT}/{d}")
seo_urls = seo.generate(OUT, clinics, prices, updates, GROUPS, css + open(f"{HERE}/seo.css", encoding="utf-8").read(), SITE)

# ---- static extras ----
today = datetime.date.today().isoformat()
open(f"{OUT}/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
urls = [""] + sorted(seo_urls) + ["about.html", "terms.html", "privacy.html", "contact.html"]
open(f"{OUT}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    "".join(f"<url><loc>{SITE}/{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(f"{OUT}/_headers", "w").write("/tools/*\n  X-Robots-Tag: noindex\n/ig/*\n  X-Robots-Tag: noindex\n/data/*\n  Cache-Control: public, max-age=600\n  X-Robots-Tag: noindex\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
import shutil
for f in ("favicon.svg", "og.png", "apple-touch-icon.png", "mascot.jpg", "mascot@2x.jpg"):
    shutil.copy(f"{HERE}/{f}", f"{OUT}/{f}")
print("built", n_cl, "clinics", n_pr, "prices", len(updates), "updates", len(seo_urls), "seo pages")
