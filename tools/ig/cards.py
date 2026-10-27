"""Instagram carousel generator (1080x1350, theme C) from data/*.json.
Usage: python3 tools/ig/cards.py <repo_dir> <out_dir> [topic]
topic: botox-tokyo (default) | booster-tokyo | filler-tokyo | hair-tokyo
Writes 01.jpg..07.jpg and caption.txt into out_dir.
"""
import json, os, sys, statistics, datetime, html
from playwright.sync_api import sync_playwright

REPO, OUT = sys.argv[1], sys.argv[2]
TOPIC = sys.argv[3] if len(sys.argv) > 3 else "botox-tokyo"
os.makedirs(OUT, exist_ok=True)
C = {c["id"]: c for c in json.load(open(f"{REPO}/data/clinics.json", encoding="utf-8"))}
P = json.load(open(f"{REPO}/data/prices.json", encoding="utf-8"))
U = json.load(open(f"{REPO}/data/updates.json", encoding="utf-8"))
day = (U[0]["date"] if U else datetime.date.today().isoformat())
y, m, d = day.split("-"); dlabel = f"{int(y)}年{int(m)}月{int(d)}日"; mlabel = f"{y}.{m}"
e = html.escape
yen = lambda n: f"{int(round(n)):,}"
INK, MUTE, ROSE, ROSE2, BLUSH, PAPER, LINE = "#3B2A2C", "#7E6E70", "#9A554D", "#B0675F", "#F6EEEC", "#FFFDFC", "#EADFDC"
SERIF, SANS = "'Noto Serif JP','Noto Serif CJK JP',serif", "'Noto Sans JP','Noto Sans CJK JP',sans-serif"

def where(c):
    if c.get("scope") == "national": return "都内各院"
    a = (c.get("area") or "").split("(")
    return (a[1].rstrip(")") if len(a) > 1 else a[0]).split("・")[0]

def pool(cat, origins=None, pref="東京都"):
    rows = [p for p in P if p["cat"] == cat and p.get("cond") == "通常" and p.get("tax") and p["clinicId"] in C
            and (C[p["clinicId"]].get("pref") == pref or C[p["clinicId"]].get("scope") == "national")
            and (origins is None or p.get("origin") in origins)]
    unit = (lambda p: p["price"] / p["cc"]) if cat == "rejuran" else (lambda p: p["price"])
    rows.sort(key=unit)
    seen, out = set(), []
    for p in rows:
        if p["clinicId"] in seen: continue
        seen.add(p["clinicId"]); out.append(p)
    return out

def median(cat, origins=None, pref="東京都"):
    v = [p["price"] for p in P if p["cat"] == cat and p.get("cond") == "通常" and p["clinicId"] in C
         and (C[p["clinicId"]].get("pref") == pref or C[p["clinicId"]].get("scope") == "national") and (origins is None or p.get("origin") in origins)]
    return statistics.median(v) if v else None

def frame(inner, bg=PAPER, color=INK):
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>body{{margin:0}}*{{box-sizing:border-box}}</style></head><body>
<div style="width:1080px;height:1350px;background:{bg};color:{color};font-family:{SANS};padding:84px 84px 70px;display:flex;flex-direction:column;position:relative;overflow:hidden">{inner}</div></body></html>'''

TOTAL = [7]
def head(kicker, title, n, total=None):
    total = total or TOTAL[0]
    return f'''<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:22px">
<span style="font-size:30px;color:{ROSE};letter-spacing:.04em">{e(kicker)}</span><span style="font-family:{SERIF};font-size:28px;color:{MUTE}">{n} / {total}</span></div>
<h2 style="margin:0 0 44px;font-family:{SERIF};font-weight:500;font-size:74px;line-height:1.35;letter-spacing:.02em">{title}</h2>'''

def rank_slide(kicker, title, rows, n, note):
    lis = ""
    for i, p in enumerate(rows[:5]):
        c = C[p["clinicId"]]
        meta = [where(c), p.get("product", "")]
        if p.get("units"): meta.append(f'{p["units"]:g}単位')
        if p.get("cc") and p["cat"] == "rejuran": meta.append(f'{p["cc"]:g}cc')
        price = p["price"] / p["cc"] if p["cat"] == "rejuran" else p["price"]
        first = i == 0
        lis += f'''<div style="display:flex;align-items:center;gap:30px;padding:30px 0;border-bottom:1.5px solid {LINE}">
<span style="flex:0 0 64px;height:64px;border-radius:50%;display:grid;place-items:center;font-family:{SERIF};font-size:34px;background:{ROSE if first else BLUSH};color:{"#fff" if first else INK}">{i+1}</span>
<div style="flex:1;min-width:0"><div style="font-size:36px;font-weight:700;line-height:1.35">{e(c["name"])}</div>
<div style="font-size:26px;color:{MUTE};margin-top:6px">{e("｜".join(x for x in meta if x))}</div></div>
<div style="font-family:{SERIF};font-size:{58 if first else 50}px;font-weight:600;color:{ROSE if first else INK};white-space:nowrap">¥{yen(price)}</div></div>'''
    return frame(head(kicker, title, n) + f'<div style="flex:1">{lis}</div><p style="margin:0;font-size:23px;line-height:1.7;color:{MUTE}">{e(note)}</p>')

def cover(big, sub, chip):
    return frame(f'''
<div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-family:{SERIF};font-size:42px;letter-spacing:.16em">キレイネ</span><span style="font-size:28px;color:{MUTE}">{mlabel} 東京版</span></div>
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:44px">
<p style="margin:0;font-size:34px;color:{ROSE};letter-spacing:.04em">公式サイトの料金だけで比較</p>
<h1 style="margin:0;font-family:{SERIF};font-weight:500;font-size:104px;line-height:1.38;letter-spacing:.02em">{big}</h1>
<div style="display:flex;gap:16px;flex-wrap:wrap"><span style="background:{PAPER};border-radius:999px;padding:18px 34px;font-size:36px">{e(chip)}</span></div>
<p style="margin:0;font-size:30px;color:{MUTE};line-height:1.7">{e(sub)}</p></div>
<div style="display:flex;justify-content:space-between;font-size:28px;color:{MUTE}"><span>保存して予約前に見返してね</span><span>スワイプ ›</span></div>''', bg=BLUSH)

def souba(n, items, takeaway, kicker="東京で掲載中の料金の中央値"):
    cells = "".join(f'''<div style="background:{PAPER};border-radius:28px;padding:38px 36px;display:flex;flex-direction:column;gap:12px">
<span style="font-size:28px;color:{MUTE}">{e(a)}</span><span style="font-family:{SERIF};font-size:72px;font-weight:600;color:{ROSE if hi else INK}">¥{yen(v)}</span></div>''' for a, v, hi in items)
    return frame(head(kicker, "そもそも<br>“相場”はいくら?", n) +
                 f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:22px">{cells}</div><div style="flex:1"></div>'
                 f'<p style="margin:0 0 20px;font-family:{SERIF};font-size:44px;line-height:1.6">{takeaway}</p>'
                 f'<p style="margin:0;font-size:23px;color:{MUTE};line-height:1.7">{dlabel}時点・通常価格の中央値(100円単位で概算)。単位数・部位の違いを含みます。</p>', bg=BLUSH)

def checks(n, items):
    lis = "".join(f'''<div style="display:flex;gap:34px;padding:40px 0;border-bottom:1.5px solid {LINE}"><span style="font-family:{SERIF};font-size:80px;color:{ROSE};line-height:.9">{i+1}</span>
<div><div style="font-family:{SERIF};font-size:46px;font-weight:600">{e(t)}</div><div style="font-size:31px;color:{MUTE};line-height:1.7;margin-top:12px">{e(s)}</div></div></div>''' for i, (t, s) in enumerate(items))
    return frame(head("保存して予約前に見返してね", "安さで選ぶ前に<br>3つのチェック", n) + f'<div style="flex:1">{lis}</div>')

def cta(n):
    return frame(f'''
<div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-family:{SERIF};font-size:42px;letter-spacing:.16em">キレイネ</span><span style="font-family:{SERIF};font-size:28px;color:rgba(255,253,252,.75)">{n} / {TOTAL[0]}</span></div>
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:40px">
<p style="margin:0;font-size:34px;color:rgba(255,253,252,.85)">全国の公式料金を毎朝チェック中</p>
<h2 style="margin:0;font-family:{SERIF};font-weight:500;font-size:92px;line-height:1.42">エリア×施術で、<br>いちばん安い院が<br>すぐ分かる。</h2>
<div style="display:flex;flex-wrap:wrap;gap:14px">{"".join(f'<span style="border:1.5px solid rgba(255,253,252,.6);border-radius:999px;padding:12px 26px;font-size:30px">{t}</span>' for t in ["ボトックス","ヒアルロン酸","リジュラン","シミ・光治療","医療脱毛"])}</div></div>
<div style="background:{PAPER};color:{INK};border-radius:999px;padding:34px 46px;display:flex;justify-content:space-between;align-items:center;font-size:40px;font-weight:700"><span>プロフィールのリンクから</span><span style="font-family:{SERIF}">kirei-ne.com</span></div>
<p style="margin:30px 0 0;font-size:22px;line-height:1.7;color:rgba(255,253,252,.82)">掲載料金は各院公式サイトより({dlabel}時点)。最新の料金・施術内容・リスクは必ず各院にご確認ください。特定の医療機関を推奨するものではなく、掲載院から広告費を受け取っていません。</p>''', bg=ROSE, color=PAPER)

NOTE = f"{dlabel}時点・各院公式サイトの税込通常価格(初回・モニター価格を除く)。単位数・部位は院により異なります。"
KOREA, ALLER = {"korea"}, {"allergan"}
CHECK = [("単位数を見る", "10単位と50単位では量が5倍ちがう。1部位あたり何単位かを確認。"),
         ("通常価格か、初回価格か", "初回だけ安い価格も多い。2回目以降の料金も見ておくと安心。"),
         ("税込・追加料金", "麻酔・針代・診察料が別のことも。合計いくらかで比べよう。")]

slides, caption = [], ""
if TOPIC == "botox-tokyo":
    k, a, j = pool("wrinkle", KOREA), pool("wrinkle", ALLER), pool("jaw", KOREA)
    mk, ma, mjk, mja = median("wrinkle", KOREA), median("wrinkle", ALLER), median("jaw", KOREA), median("jaw", ALLER)
    lo = min(k[0]["price"], a[0]["price"])
    slides = [cover("東京で<br>ボトックスが<br>安いクリニック<br>TOP5", "韓国製・アラガン製・エラ別に、東京の公式料金を安い順に並べました。", f"シワ1部位 最安 ¥{yen(lo)}〜"),
              rank_slide("シワ(額・眉間・目尻)1部位", "韓国製ボトックス<br>最安TOP5", k, 2, NOTE),
              rank_slide("シワ(額・眉間・目尻)1部位", "アラガン製(米国)<br>最安TOP5", a, 3, NOTE),
              rank_slide("小顔・エラ(両側)｜韓国製", "エラボトックス<br>最安TOP5", j, 4, NOTE + "エラは単位数で効果が変わります。"),
              souba(5, [("シワ1部位｜韓国製", round(mk, -2), False), ("シワ1部位｜アラガン", round(ma, -2), True), ("エラ｜韓国製", round(mjk, -2), False), ("エラ｜アラガン", round(mja, -2), True)],
                    f"アラガン製は韓国製の<br>約{ma/mk:.1f}倍が目安。"),
              checks(6, CHECK), cta(7)]
    caption = f"""【保存版】東京でボトックスが安いクリニックTOP5
各クリニックの公式サイトに載っている料金だけで比較しました。

✔ 韓国製・アラガン製・エラ別ランキング
✔ 東京の“相場”もチェック
✔ 安さで選ぶ前の3つのポイント

予約前に保存して見返してね。
エリア×施術の料金比較はプロフィールのリンク(kirei-ne.com)から。

※{dlabel}時点の税込通常価格。最新情報は各院にご確認ください。広告費は受け取っていません。
#ボトックス #エラボトックス #美容皮膚科 #東京美容 #美容医療 #ボトックス注射 #小顔 #美容垢"""
elif TOPIC in ("booster-tokyo", "filler-tokyo", "spot-tokyo", "hair-tokyo"):
    TOTAL[0] = 5
    if TOPIC == "booster-tokyo":
        r = pool("rejuran"); m = median("rejuran")
        mv = statistics.median([p["price"] / p["cc"] for p in P if p["cat"] == "rejuran" and p.get("cc") and p.get("cond") == "通常" and p["clinicId"] in C and (C[p["clinicId"]].get("pref") == "東京都" or C[p["clinicId"]].get("scope") == "national")])
        name, tag = "リジュラン", "#リジュラン #リジュランi #肌育注射 #サーモン注射 #美容皮膚科 #東京美容 #美容医療 #美容垢"
        ranks = [rank_slide("1ccあたりの料金で比較", "リジュラン<br>最安TOP5", r, 2, NOTE + "複数ccのメニューは1ccあたりに換算しています。")]
        sv = [("1ccあたり 最安", r[0]["price"] / r[0]["cc"], True), ("1ccあたり 中央値", round(mv, -2), False)]
        tk = "同じリジュランでも、<br>院によって倍以上の差。"
        chk = [("ccと種類を見る", "1cc・2cc・顔全体などメニューで量が違う。i・HB・Sなど種類も確認。"), CHECK[1], ("打ち方と麻酔", "手打ち・機械(水光)で料金が違う。麻酔クリーム代が別のことも。")]
        chip = f"1ccあたり ¥{yen(r[0]['price'] / r[0]['cc'])}〜"
    elif TOPIC == "filler-tokyo":
        r = pool("filler"); mv = median("filler")
        name, tag = "ヒアルロン酸", "#ヒアルロン酸 #ヒアルロン酸注入 #涙袋 #ほうれい線 #美容皮膚科 #東京美容 #美容医療 #美容垢"
        ranks = [rank_slide("1cc(1本)あたり", "ヒアルロン酸<br>最安TOP5", r, 2, NOTE + "製剤によって持続期間・硬さが異なります。")]
        sv = [("1cc 最安", r[0]["price"], True), ("1cc 中央値", round(mv, -2), False)]
        tk = "製剤によって<br>料金も持ちも変わる。"
        chk = [("製剤名を見る", "韓国製・アラガン(ジュビダーム)・レスチレンなどで料金と持続が違う。"), CHECK[1], ("溶解・修正の料金", "ヒアルロニダーゼ(溶解)が別料金のことも。事前に確認を。")]
        chip = f"1cc ¥{yen(r[0]['price'])}〜"
    elif TOPIC == "spot-tokyo":
        r = pool("ipl"); mv = median("ipl")
        name, tag = "フォトフェイシャル(IPL)", "#フォトフェイシャル #IPL #シミ取り #くすみ #美容皮膚科 #東京美容 #美容医療 #美容垢"
        ranks = [rank_slide("顔全体 1回", "シミ・くすみの光治療<br>最安TOP5", r, 2, NOTE + "機器(M22・ルメッカなど)によって内容が異なります。")]
        sv = [("顔全体1回 最安", r[0]["price"], True), ("顔全体1回 中央値", round(mv, -2), False)]
        tk = "回数を重ねる治療だから、<br>2回目以降の料金も大事。"
        chk = [("機器名を見る", "M22・ルメッカ・BBLなど機器で料金と強さが違う。"), CHECK[1], ("肝斑がある人は注意", "光治療で悪化することも。診察で相談を。")]
        chip = f"顔全体 ¥{yen(r[0]['price'])}〜"
    else:
        TOTAL[0] = 6
        a5, b5, f5 = pool("armpit5"), pool("body5"), pool("bodyfull5")
        name, tag = "医療脱毛", "#医療脱毛 #全身脱毛 #脇脱毛 #VIO脱毛 #美容皮膚科 #東京美容 #美容医療 #美容垢"
        ranks = [rank_slide("全身(顔・VIO除く) 5回", "全身脱毛<br>安い順", b5, 2, NOTE),
                 rank_slide("全身(顔・VIO含む) 5回", "全身+顔+VIO<br>最安TOP5", f5, 3, NOTE)]
        sv = [("全身5回 中央値", round(median("body5"), -2), False), ("全身5回 最安", b5[0]["price"], True),
              ("全身+顔+VIO 中央値", round(median("bodyfull5"), -2), True), ("全身+顔+VIO 最安", f5[0]["price"], True)]
        tk = "コース料金は、<br>回数と範囲で比べよう。"
        chk = [("範囲を見る", "「全身」に顔・VIO・うなじが入るかは院によって違う。"), ("回数と追加料金", "5回で終わらないことも。追加1回の料金も確認。"), CHECK[2]]
        chip = f"全身5回 ¥{yen(b5[0]['price'])}〜"
    n = 2 + len(ranks)
    cname = {"spot-tokyo": "フォト<br>フェイシャル"}.get(TOPIC, e(name))
    slides = [cover(f"東京で<br>{cname}が<br>安いクリニック<br>TOP5", f"東京の{name}の公式料金を安い順に並べました。", chip)] + ranks + [souba(n, sv, tk), checks(n + 1, chk), cta(n + 2)]
    caption = f"""【保存版】東京で{name}が安いクリニックTOP5
各クリニックの公式サイトに載っている料金だけで比較しました。

✔ 安い順ランキング
✔ 東京の“相場”もチェック
✔ 予約前の3つのポイント

予約前に保存して見返してね。
エリア×施術の料金比較はプロフィールのリンク(kirei-ne.com)から。

※{dlabel}時点の税込通常価格。最新情報は各院にご確認ください。広告費は受け取っていません。
{tag}"""
else:
    raise SystemExit("unknown topic")

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1350})
    for i, h in enumerate(slides, 1):
        pg.set_content(h); pg.wait_for_timeout(250)
        pg.screenshot(path=f"{OUT}/{i:02d}.jpg", type="jpeg", quality=92)
    b.close()
open(f"{OUT}/caption.txt", "w", encoding="utf-8").write(caption)
print("ok", len(slides), "slides", OUT)
