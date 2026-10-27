"""Instagram Reel generator (1080x1920, 30fps, ~15s) from data/*.json — theme C, no faces, data-driven.
Usage: python3 tools/ig/reel.py <repo_dir> <out_dir> [topic]
topic: botox-tokyo | filler-tokyo | booster-tokyo | spot-tokyo
Writes reel.mp4, cover.jpg, caption.txt into out_dir.
"""
import json, os, sys, statistics, datetime, html, shutil, subprocess, tempfile
from playwright.sync_api import sync_playwright

REPO, OUT = sys.argv[1], sys.argv[2]
TOPIC = sys.argv[3] if len(sys.argv) > 3 else "botox-tokyo"
FPS = 30
os.makedirs(OUT, exist_ok=True)
C = {c["id"]: c for c in json.load(open(f"{REPO}/data/clinics.json", encoding="utf-8"))}
P = json.load(open(f"{REPO}/data/prices.json", encoding="utf-8"))
U = json.load(open(f"{REPO}/data/updates.json", encoding="utf-8"))
day = (U[0]["date"] if U else datetime.date.today().isoformat())
y, m, d = day.split("-"); dlabel = f"{int(y)}年{int(m)}月{int(d)}日"
e = html.escape
yen = lambda n: f"{int(round(n)):,}"
INK, MUTE, ROSE, BLUSH, PAPER, LINE = "#3B2A2C", "#7E6E70", "#9A554D", "#F6EEEC", "#FFFDFC", "#EADFDC"
SERIF, SANS = "'Noto Serif JP','Noto Serif CJK JP',serif", "'Noto Sans JP','Noto Sans CJK JP',sans-serif"

def where(c):
    if c.get("scope") == "national": return "都内各院"
    a = (c.get("area") or "").split("(")
    return (a[1] if len(a) > 1 else a[0]).replace(")", "").replace("）", "").split("・")[0]

def rows(cat, origins=None):
    r = [p for p in P if p["cat"] == cat and p.get("cond") == "通常" and p.get("tax") and p["clinicId"] in C
         and (C[p["clinicId"]].get("pref") == "東京都" or C[p["clinicId"]].get("scope") == "national")
         and (origins is None or p.get("origin") in origins)]
    unit = (lambda p: p["price"] / p["cc"]) if cat == "rejuran" else (lambda p: p["price"])
    for p in r: p["_u"] = unit(p)
    r.sort(key=lambda p: p["_u"])
    seen, out = set(), []
    for p in r:
        if p["clinicId"] in seen: continue
        seen.add(p["clinicId"]); out.append(p)
    return out

TEXT_ONLY = "--text-only" in sys.argv
G = {
    "botox": dict(cat="wrinkle", origins={"korea", "allergan", "allergan_unclear"}, name="ボトックス", unit="シワ1部位", page="botox",
                  tags="#ボトックス #ボトックス注射 #美容皮膚科 #美容医療 #美容垢 #プチ整形 #美容好きな人と繋がりたい"),
    "jaw": dict(cat="jaw", origins={"korea", "allergan", "allergan_unclear"}, name="エラボトックス", unit="両側", page="botox",
                tags="#エラボトックス #小顔 #ボトックス #美容皮膚科 #美容医療 #美容垢 #プチ整形"),
    "filler": dict(cat="filler", origins=None, name="ヒアルロン酸", unit="1cc", page="filler",
                   tags="#ヒアルロン酸 #ヒアルロン酸注入 #涙袋 #美容皮膚科 #美容医療 #美容垢 #プチ整形"),
    "booster": dict(cat="rejuran", origins=None, name="リジュラン", unit="1ccあたり", page="booster",
                    tags="#リジュラン #肌育注射 #サーモン注射 #美容皮膚科 #美容医療 #美容垢 #韓国美容"),
    "spot": dict(cat="ipl", origins=None, name="フォトフェイシャル", unit="顔全体1回", page="spot",
                 tags="#フォトフェイシャル #シミ取り #美容皮膚科 #美容医療 #美容垢 #肌管理"),
}
grp, place = TOPIC.split("-", 1)                       # 例: botox-tokyo / filler-ginza
T = dict(G[grp])
R = rows(T["cat"], T["origins"])
if place == "tokyo":
    T["place"], T["url"] = "東京", f"https://kirei-ne.com/tokyo/{T['page']}/"
    T["tags"] += " #東京美容"
else:                                                   # 駅エリア(その駅に院があるクリニックのみ。都内各院のチェーンは除く)
    sys.path.insert(0, os.path.join(REPO, "tools")); import seo
    lab = None
    def here(c):
        global lab
        if c.get("scope") == "national" or c.get("pref") != "東京都": return False
        for k, l, sl in seo.area_keys(c):
            if k == "st" and sl == place: lab = l; return True
        return False
    R = [p for p in R if here(C[p["clinicId"]])]
    if len(R) < 3: sys.exit(f"not enough clinics in {place}: {len(R)}")
    T["place"], T["url"] = lab, f"https://kirei-ne.com/tokyo/{place}/{T['page']}/"
    T["tags"] += f" #{lab.split('・')[0]}美容 #東京美容"
vals = [p["_u"] for p in R]
lo, hi, med = vals[0], vals[-1], statistics.median(vals)
top = R[:5]
N = len(top)

BASE = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0}} body{{width:1080px;height:1920px;overflow:hidden;font-family:{SANS};color:{INK}}}
.s{{position:absolute;inset:0;padding:240px 90px 420px;display:flex;flex-direction:column;justify-content:center}}
.k{{font-size:40px;color:{ROSE};letter-spacing:.06em}}
.serif{{font-family:{SERIF};font-weight:500}}
.up{{animation:up .55s cubic-bezier(.2,.8,.2,1) both}}
.pop{{animation:pop .5s cubic-bezier(.2,1.4,.4,1) both}}
.fade{{animation:fade .5s ease both}}
.bar{{animation:bar var(--d) linear both}}
@keyframes up{{from{{opacity:0;transform:translateY(60px)}}to{{opacity:1;transform:none}}}}
@keyframes pop{{from{{opacity:0;transform:scale(.6)}}to{{opacity:1;transform:none}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes bar{{from{{width:0}}to{{width:100%}}}}
.brand{{position:absolute;top:120px;left:90px;font-family:{SERIF};font-size:40px;letter-spacing:.16em}}
</style></head><body>"""

def brand(color=INK):
    return f'<div class="brand" style="color:{color}">キレイネ</div>'

def hook():
    return (BASE + f'<div style="position:absolute;inset:0;background:{PAPER}"></div>' + brand() +
        f'''<div class="s"><p class="k up">{e(T["place"])}の{e(T["name"])}｜{e(T["unit"])}</p>
<p class="up" style="animation-delay:0s;font-size:62px;font-weight:700;margin:26px 0 50px;line-height:1.4">同じ施術なのに…</p>
<div class="pop serif" style="animation-delay:.1s;font-size:150px;color:{ROSE};line-height:1.1">¥{yen(lo)}</div>
<div class="fade" style="animation-delay:.3s;font-size:56px;color:{MUTE};margin:18px 0 18px 8px">〜</div>
<div class="pop serif" style="animation-delay:.4s;font-size:150px;line-height:1.1">¥{yen(hi)}</div>
<p class="up" style="animation-delay:.9s;font-size:58px;font-weight:700;margin-top:60px;line-height:1.5">公式料金で<span style="color:{ROSE}">最大{hi/lo:.0f}倍</span>。<br>安い院TOP{N}は👇</p>
<p class="fade" style="animation-delay:1.1s;font-size:30px;color:{MUTE};margin-top:24px">※製剤・量の違いを含む公式料金の幅</p></div></body></html>''')

def rank(i, p):
    c = C[p["clinicId"]]
    meta = " ｜ ".join(x for x in [where(c), p.get("product") or "", f'{p["cc"]:g}ccメニュー' if p.get("cc") and T["cat"] == "rejuran" else ""] if x)
    n = N - i
    bg = ROSE if n == 1 else BLUSH
    fg = PAPER if n == 1 else INK
    return (BASE + f'<div style="position:absolute;inset:0;background:{bg}"></div>' + brand(fg) +
        f'''<div class="s" style="color:{fg}"><p class="k fade" style="color:{PAPER if n == 1 else ROSE}">{e(T["place"])}で安い{e(T["name"])}</p>
<div class="pop serif" style="font-size:220px;line-height:1;margin:30px 0 40px">{n}<span style="font-size:90px">位</span></div>
<p class="up" style="animation-delay:.15s;font-size:68px;font-weight:700;line-height:1.35">{e(c["name"])}</p>
<p class="up" style="animation-delay:.25s;font-size:40px;opacity:.75;margin-top:18px;line-height:1.5">{e(meta)}</p>
<div class="pop serif" style="animation-delay:.45s;font-size:140px;margin-top:60px;line-height:1">¥{yen(p["_u"])}<span style="font-size:48px"> {e(T["unit"])}</span></div>
</div></body></html>''')

def souba():
    return (BASE + f'<div style="position:absolute;inset:0;background:{PAPER}"></div>' + brand() +
        f'''<div class="s"><p class="k fade">ちなみに{e(T["place"])}の“相場”は</p>
<div class="pop serif" style="animation-delay:.2s;font-size:170px;margin:40px 0 20px;line-height:1">¥{yen(round(med, -2))}</div>
<p class="up" style="animation-delay:.4s;font-size:46px;color:{MUTE}">{e(T["unit"])}・掲載{len(R)}院の中央値</p>
<p class="up" style="animation-delay:.8s;font-size:60px;font-weight:700;margin-top:80px;line-height:1.5">1位なら相場より<br><span style="color:{ROSE}">¥{yen(med - lo)}</span> おトク。</p></div></body></html>''')

def cta():
    return (BASE + f'<div style="position:absolute;inset:0;background:{ROSE}"></div>' + brand(PAPER) +
        f'''<div class="s" style="color:{PAPER}"><p class="up serif" style="font-size:96px;line-height:1.45">予約する前に、<br>保存しておこう。</p>
<p class="up" style="animation-delay:.3s;font-size:50px;margin-top:60px;line-height:1.6">全国のクリニックの料金比較は<br>プロフィールのリンクから</p>
<div class="pop" style="animation-delay:.6s;margin-top:60px;background:{PAPER};color:{INK};border-radius:999px;padding:34px 50px;font-size:54px;font-weight:700;align-self:flex-start">kirei-ne.com</div>
<p class="fade" style="animation-delay:.9s;font-size:28px;margin-top:70px;opacity:.8;line-height:1.7">{dlabel}時点・各院公式サイトの税込通常価格。最新情報・リスクは各院にご確認ください。広告費は受け取っていません。</p></div></body></html>''')

def threads_text():
    lines = [f"{T['place']}の{T['name']}、同じ「{T['unit']}」でも公式料金は ¥{yen(lo)}〜¥{yen(hi)}。", "", f"安い順TOP{N}"]
    lines += [f"{i+1}位 {C[p['clinicId']]['name']}({where(C[p['clinicId']])}) ¥{yen(p['_u'])}" for i, p in enumerate(top)]
    lines += ["", f"{T['place']}の相場(掲載{len(R)}院の中央値)は ¥{yen(round(med, -2))}。", "みんなはいくらで受けた？", "", f"全院の比較 → {T['url']}",
              f"※{dlabel}時点・公式サイトの税込通常価格。製剤・量は院により異なります。"]
    t = "\n".join(lines)
    k = 3 + len(top)                                     # 500字制限(絵文字なし)に収まるまで下位を削る
    while len(t) > 490 and k > 5:
        k -= 1; lines.pop(k); lines[2] = f"安い順TOP{k-3}"; t = "\n".join(lines)
    return t
open(f"{OUT}/threads.txt", "w", encoding="utf-8").write(threads_text())
if TEXT_ONLY:
    print("ok threads text", OUT); sys.exit(0)

scenes = [(hook(), 3.0)] + [(rank(i, p), 1.7) for i, p in enumerate(reversed(top))] + [(souba(), 2.6), (cta(), 2.8)]

tmp = tempfile.mkdtemp()
n = 0
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    for si, (htm, dur) in enumerate(scenes):
        pg.set_content(htm); pg.wait_for_timeout(250)
        pg.evaluate("document.fonts.ready")
        pg.evaluate("document.getAnimations().forEach(a=>a.pause())")
        for f in range(int(dur * FPS)):
            t = f * 1000 / FPS
            pg.evaluate(f"document.getAnimations().forEach(a=>a.currentTime={t})")
            pg.screenshot(path=f"{tmp}/{n:05d}.jpg", type="jpeg", quality=90); n += 1
            if si == 0 and f == int(2.2 * FPS):
                shutil.copy(f"{tmp}/{n-1:05d}.jpg", f"{OUT}/cover.jpg")
    b.close()

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/%05d.jpg",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", f"{OUT}/reel.mp4"], check=True)
shutil.rmtree(tmp)

caption = f"""{T["place"]}の{T["name"]}、同じ施術でも公式料金で最大{hi/lo:.0f}倍の差がありました(製剤・量の違いを含む)。

安い順TOP{N}と{T["place"]}の“相場”をまとめたので、予約前に保存してね。
お友だちとの施術の相談にも、送ってあげてください。

全国のクリニックの料金比較はプロフィールのリンク(kirei-ne.com)から。

※{dlabel}時点・各院公式サイトの税込通常価格(初回・モニター価格を除く)。単位数・部位・製剤は院により異なります。最新情報は各院にご確認ください。広告費は受け取っていません。
{T["tags"]}"""
open(f"{OUT}/caption.txt", "w", encoding="utf-8").write(caption)
print("ok reel", n, "frames", OUT)
