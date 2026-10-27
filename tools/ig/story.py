"""「今日の最安」ストーリー(1080x1920)と Threads 用テキストを data/*.json から作る。曜日ごとにテーマが変わる。
usage: python3 tools/ig/story.py <repo_dir> <out_dir> [weekday 0-6]
writes story.jpg, threads.txt, meta.json"""
import json, os, sys, statistics, datetime, html
from playwright.sync_api import sync_playwright

REPO, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
today = datetime.date.today()
wd = int(sys.argv[3]) if len(sys.argv) > 3 else today.weekday()
C = {c["id"]: c for c in json.load(open(f"{REPO}/data/clinics.json", encoding="utf-8"))}
P = json.load(open(f"{REPO}/data/prices.json", encoding="utf-8"))
U = json.load(open(f"{REPO}/data/updates.json", encoding="utf-8"))
day = (U[0]["date"] if U else today.isoformat()); y, m, d = day.split("-")
dlabel = f"{int(y)}年{int(m)}月{int(d)}日"; short = f"{int(m)}/{int(d)}"
e = html.escape; yen = lambda n: f"{int(round(n)):,}"
INK, MUTE, ROSE, BLUSH, PAPER, LINE = "#3B2A2C", "#7E6E70", "#9A554D", "#F6EEEC", "#FFFDFC", "#EADFDC"
SERIF, SANS = "'Noto Serif JP','Noto Serif CJK JP',serif", "'Noto Sans JP','Noto Sans CJK JP',sans-serif"

THEMES = [  # 月〜日
    ("wrinkle", {"korea"}, "ボトックス", "シワ1部位｜韓国製", "botox"),
    ("filler", None, "ヒアルロン酸", "1cc", "filler"),
    ("rejuran", None, "リジュラン", "1ccあたり", "booster"),
    ("jaw", {"korea"}, "エラボトックス", "両側｜韓国製", "botox"),
    ("ipl", None, "フォトフェイシャル", "顔全体1回", "spot"),
    ("wrinkle", {"allergan"}, "ボトックス", "シワ1部位｜アラガン", "botox"),
    ("body5", None, "全身脱毛", "5回コース", "hair"),
]
cat, origins, name, unit, group = THEMES[wd % 7]

def where(c):
    if c.get("scope") == "national": return "都内各院"
    a = (c.get("area") or "").split("(")
    return (a[1] if len(a) > 1 else a[0]).replace(")", "").replace("）", "").split("・")[0]

rows = [p for p in P if p["cat"] == cat and p.get("cond") == "通常" and p.get("tax") and p["clinicId"] in C
        and (C[p["clinicId"]].get("pref") == "東京都" or C[p["clinicId"]].get("scope") == "national")
        and (origins is None or p.get("origin") in origins)]
for p in rows: p["_u"] = p["price"] / p["cc"] if cat == "rejuran" and p.get("cc") else p["price"]
rows.sort(key=lambda p: p["_u"])
seen, top = set(), []
for p in rows:
    if p["clinicId"] not in seen: seen.add(p["clinicId"]); top.append(p)
if len(top) < 3: sys.exit(f"not enough data for {cat}")
med = statistics.median(p["_u"] for p in top)
first, rest = top[0], top[1:3]
url = f"https://kirei-ne.com/tokyo/{group}/"

runner = "".join(f'''<div style="display:flex;justify-content:space-between;align-items:baseline;padding:22px 0;border-top:1.5px solid {LINE}">
<span style="font-size:36px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;margin-right:20px"><b style="font-family:{SERIF};font-weight:600;margin-right:18px">{i+2}位</b>{e(C[p["clinicId"]]["name"])}</span>
<span style="font-family:{SERIF};font-size:42px;font-weight:600;white-space:nowrap">¥{yen(p["_u"])}</span></div>''' for i, p in enumerate(rest))
page = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>*{{box-sizing:border-box;margin:0}}</style></head>
<body style="width:1080px;height:1920px;background:{BLUSH};font-family:{SANS};color:{INK};padding:250px 80px 340px;display:flex;flex-direction:column">
<div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-family:{SERIF};font-size:44px;letter-spacing:.16em">キレイネ</span>
<span style="font-size:34px;color:{MUTE}">{short} 東京</span></div>
<div style="flex:1;display:flex;flex-direction:column;justify-content:center">
<p style="font-size:40px;color:{ROSE};letter-spacing:.08em">今日の最安</p>
<h1 style="font-family:{SERIF};font-weight:500;font-size:96px;line-height:1.3;margin:14px 0 6px">{e(name)}</h1>
<p style="font-size:38px;color:{MUTE}">{e(unit)}</p>
<div style="background:{PAPER};border-radius:36px;padding:54px 56px;margin:54px 0 0">
<p style="font-size:34px;color:{ROSE};font-weight:700">1位</p>
<p style="font-size:54px;font-weight:700;line-height:1.35;margin:8px 0 6px">{e(C[first["clinicId"]]["name"])}</p>
<p style="font-size:34px;color:{MUTE}">{e(where(C[first["clinicId"]]))}{(" ｜ " + e(first.get("product") or "")) if first.get("product") else ""}</p>
<p style="font-family:{SERIF};font-size:150px;font-weight:600;color:{ROSE};line-height:1.15;margin-top:24px">¥{yen(first["_u"])}</p>
<p style="font-size:34px;color:{MUTE};margin-bottom:30px">東京の相場(中央値) ¥{yen(round(med, -2))}</p>{runner}</div>
<p style="font-size:40px;font-weight:700;margin-top:56px;text-align:center">全院の比較はプロフィールのリンクから</p></div>
<p style="font-size:24px;color:{MUTE};line-height:1.6">{dlabel}時点・各院公式サイトの税込通常価格。最新情報は各院にご確認ください。広告費は受け取っていません。</p>
</body></html>'''
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.set_content(page); pg.wait_for_timeout(300); pg.evaluate("document.fonts.ready")
    pg.screenshot(path=f"{OUT}/story.jpg", type="jpeg", quality=90); b.close()

lines = [f"【今日の最安】東京の{name}({unit})", "",
         f"1位 {C[first['clinicId']]['name']}({where(C[first['clinicId']])}) ¥{yen(first['_u'])}"]
lines += [f"{i+2}位 {C[p['clinicId']]['name']} ¥{yen(p['_u'])}" for i, p in enumerate(rest)]
lines += ["", f"東京の相場は ¥{yen(round(med, -2))}(掲載{len(top)}院の中央値)。", "どこで受けてる？", "", f"比較 → {url}",
          f"※{dlabel}時点・公式サイトの税込通常価格"]
open(f"{OUT}/threads.txt", "w", encoding="utf-8").write("\n".join(lines)[:490])
json.dump({"date": today.isoformat(), "theme": cat, "name": name}, open(f"{OUT}/meta.json", "w"), ensure_ascii=False)
print("ok story", name, OUT)
