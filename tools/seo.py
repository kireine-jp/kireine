"""Static SEO pages for kirei-ne.com, generated from data/*.json.

Pages (all /<path>/index.html):
  /<group>/                     nationwide page per treatment (相場・最安・都道府県リンク)
  /<pref>/                      prefecture hub
  /<pref>/<group>/              prefecture x treatment
  /<pref>/<area>/<group>/       Tokyo ward/city or station x treatment (2+ clinics)
  /clinic/<id>/                 clinic price list
Called from build.py: generate(out_dir, clinics, prices, updates, groups, css, site)
"""
import os, re, json, html, statistics, datetime

PREFS = [("北海道","hokkaido"),("青森県","aomori"),("岩手県","iwate"),("宮城県","miyagi"),("秋田県","akita"),("山形県","yamagata"),("福島県","fukushima"),("茨城県","ibaraki"),("栃木県","tochigi"),("群馬県","gunma"),("埼玉県","saitama"),("千葉県","chiba"),("東京都","tokyo"),("神奈川県","kanagawa"),("新潟県","niigata"),("富山県","toyama"),("石川県","ishikawa"),("福井県","fukui"),("山梨県","yamanashi"),("長野県","nagano"),("岐阜県","gifu"),("静岡県","shizuoka"),("愛知県","aichi"),("三重県","mie"),("滋賀県","shiga"),("京都府","kyoto"),("大阪府","osaka"),("兵庫県","hyogo"),("奈良県","nara"),("和歌山県","wakayama"),("鳥取県","tottori"),("島根県","shimane"),("岡山県","okayama"),("広島県","hiroshima"),("山口県","yamaguchi"),("徳島県","tokushima"),("香川県","kagawa"),("愛媛県","ehime"),("高知県","kochi"),("福岡県","fukuoka"),("佐賀県","saga"),("長崎県","nagasaki"),("熊本県","kumamoto"),("大分県","oita"),("宮崎県","miyazaki"),("鹿児島県","kagoshima"),("沖縄県","okinawa")]
PREF_SLUG = dict(PREFS)

# Tokyo wards / cities and station-area names that appear in clinic "area" fields.
WARDS = {"千代田区":"chiyoda-ku","中央区":"chuo-ku","港区":"minato-ku","新宿区":"shinjuku-ku","文京区":"bunkyo-ku","台東区":"taito-ku","墨田区":"sumida-ku","江東区":"koto-ku","品川区":"shinagawa-ku","目黒区":"meguro-ku","大田区":"ota-ku","世田谷区":"setagaya-ku","渋谷区":"shibuya-ku","中野区":"nakano-ku","杉並区":"suginami-ku","豊島区":"toshima-ku","北区":"kita-ku","荒川区":"arakawa-ku","板橋区":"itabashi-ku","練馬区":"nerima-ku","足立区":"adachi-ku","葛飾区":"katsushika-ku","江戸川区":"edogawa-ku",
         "八王子市":"hachioji-shi","立川市":"tachikawa-shi","武蔵野市":"musashino-shi","三鷹市":"mitaka-shi","調布市":"chofu-shi","国分寺市":"kokubunji-shi","町田市":"machida-shi","府中市":"fuchu-shi"}
WARD_ALIAS = {"新宿":"新宿区","渋谷":"渋谷区","池袋":"豊島区","銀座":"中央区","立川":"立川市"}
STATIONS = {"銀座":"ginza","恵比寿":"ebisu","表参道":"omotesando","青山":"omotesando","南青山":"omotesando","池袋":"ikebukuro","東池袋":"ikebukuro","新宿":"shinjuku","新宿南口":"shinjuku","渋谷":"shibuya",
            "六本木":"roppongi","麻布":"azabu","麻布十番":"azabu","赤坂":"akasaka","上野":"ueno","御徒町":"ueno","浅草":"asakusa","秋葉原":"akihabara","五反田":"gotanda","品川":"shinagawa","新橋":"shimbashi","浜松町":"hamamatsucho",
            "吉祥寺":"kichijoji","三軒茶屋":"sangenjaya","下北沢":"shimokitazawa","二子玉川":"futakotamagawa","自由が丘":"jiyugaoka","錦糸町":"kinshicho","北千住":"kitasenju","代官山":"daikanyama","原宿":"harajuku","広尾":"hiroo","日本橋":"nihonbashi","東日本橋":"nihonbashi"}
STATION_LABEL = {"omotesando":"表参道・青山","ikebukuro":"池袋","shinjuku":"新宿","azabu":"麻布・麻布十番","ueno":"上野・御徒町","nihonbashi":"日本橋"}

COND_ORDER = {"通常":0,"2回目以降":1,"初回":2,"モニター":3,"キャンペーン":4}
ORIGIN = {"allergan":"アラガン","korea":"韓国製","unknown":"製剤記載なし","other":"その他製剤","allergan_unclear":"メーカー記載なし"}
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
yen = lambda n: f"{int(round(n)):,}"

def area_keys(c):
    """Return [(kind,label,slug)] for a Tokyo local clinic: wards/cities and station areas."""
    a = c.get("area") or ""
    out = []
    for w in re.findall(r"([^\s・()（）]+?[区市])", a):
        w = re.sub(r"^(東京都)", "", w)
        if w in WARDS: out.append(("ward", w, WARDS[w]))
    toks = re.findall(r"[^\s・()（）]+", a)
    for t in toks:
        t2 = re.sub(r"(区|市).*$", r"\1", t)
        if t in WARD_ALIAS and WARD_ALIAS[t] in WARDS: out.append(("ward", WARD_ALIAS[t], WARDS[WARD_ALIAS[t]]))
        if t in STATIONS:
            s = STATIONS[t]; out.append(("st", STATION_LABEL.get(s, t), s))
    for m in re.findall(r"\(([^)]*)\)", a):
        for t in m.split("・"):
            if t in STATIONS:
                s = STATIONS[t]; out.append(("st", STATION_LABEL.get(s, t), s))
    seen, res = set(), []
    for k in out:
        if k[2] not in seen: seen.add(k[2]); res.append(k)
    return res

def unit_price(p):
    if p["cat"] == "rejuran" and p.get("cc"): return p["price"] / p["cc"]
    return p["price"]

def generate(OUT, clinics, prices, updates, groups, css, SITE):
    C = {c["id"]: c for c in clinics}
    P = [p for p in prices if p.get("clinicId") in C and isinstance(p.get("price"), (int, float))]
    G = {g["id"]: g for g in groups}
    CAT2G = {s[0]: g for g in groups for s in g["subs"]}
    SUB = {s[0]: s[1] for g in groups for s in g["subs"]}
    last = (updates[0]["date"] if updates else datetime.date.today().isoformat())
    lastj = last.replace("-", "/")
    urls = []

    def write(path, title, desc, crumbs, body, extra_head=""):
        d = os.path.join(OUT, path.strip("/"))
        os.makedirs(d, exist_ok=True)
        url = f"{SITE}/{path.strip('/')}/"
        bc = "".join(f'<a href="{esc(u)}">{esc(n)}</a><span>›</span>' for n, u in crumbs[:-1]) + f"<b>{esc(crumbs[-1][0])}</b>"
        ld = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":i+1,"name":n,"item":SITE+u} for i,(n,u) in enumerate(crumbs)]}
        page = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="article"><meta property="og:site_name" content="キレイネ"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}/og.png"><meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{extra_head}<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;600&display=swap">
<style>{css}</style>
</head>
<body>
<header><a class="logo" href="/"><i>¥</i>キレイネ<small>美容医療の最安値を比較</small></a></header>
<main>
<nav class="bc" aria-label="パンくず">{bc}</nav>
{body}
<p class="disc">掲載料金は各クリニック公式サイトの掲載額(確認日時点)です。初診料・麻酔代などが別途かかる場合があり、最終的な金額・施術内容・リスクは診察でご確認ください。キレイネは特定の医療機関を推奨するものではなく、掲載院から広告費を受け取っていません。</p>
</main>
<footer><nav class="glinks">{''.join(f'<a href="/{g["id"]}/">{esc(g["name"])}</a>' for g in groups)}</nav><nav><a href="/">トップ</a><a href="/about.html">運営者情報</a><a href="/terms.html">利用規約</a><a href="/privacy.html">プライバシーポリシー</a><a href="/contact.html">お問い合わせ</a></nav><p>© {datetime.date.today().year} キレイネ</p></footer>
</body>
</html>
"""
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
        urls.append(path.strip("/") + "/")

    def row(p, rank=None, compact=False):
        c = C[p["clinicId"]]
        loc = "全国チェーン" if c.get("scope") == "national" else (c.get("pref", "") + " " + (c.get("area") or ""))
        meta = [] if compact else [esc(p.get("product", ""))]
        if p.get("origin") in ORIGIN and ORIGIN[p["origin"]] not in (p.get("product") or "") and not (p["origin"] == "allergan" and "ビスタ" in (p.get("product") or "")): meta.append(ORIGIN[p["origin"]])
        if p.get("units"): meta.append(f'{p["units"]:g}単位')
        if p.get("cc") and p["cat"] != "filler": meta.append(f'{p["cc"]:g}cc')
        if p.get("note"): meta.append(esc(p["note"]))
        tags = []
        if p.get("cond") and p["cond"] != "通常": tags.append(f'<em class="t c">{esc(p["cond"])}</em>')
        tags.append('<em class="t">税込</em>' if p.get("tax") else '<em class="t w">税表記要確認</em>')
        up = f'<small>1ccあたり {yen(unit_price(p))}円</small>' if p["cat"] == "rejuran" and p.get("cc") and p["cc"] != 1 else ""
        rk = f'<b class="rk">{rank}</b>' if rank else ""
        head = (f'<span class="cn">{esc(p.get("product", ""))}</span>' if compact else
                f'<a class="cn" href="/clinic/{esc(c["id"])}/">{esc(c["name"])}</a><span class="m">{esc(loc)}</span>')
        return (f'<li>{rk}<div class="b">{head}'
                f'<span class="m">{" · ".join(meta)}</span><span class="tg">{"".join(tags)}'
                f'<a class="src" href="{esc(p.get("source") or c.get("web"))}" rel="nofollow noopener" target="_blank">公式の料金表 ({esc((p.get("checkedDate") or "").replace("-","/"))}確認)</a></span></div>'
                f'<div class="p">{yen(p["price"])}<small>円</small>{up}</div></li>')

    def price_list(ps, limit=None):
        ps = sorted(ps, key=lambda p: (unit_price(p), COND_ORDER.get(p.get("cond"), 9)))
        seen, out = {}, []
        for p in ps:
            k = (p["clinicId"], p.get("cond"))
            if k in seen: continue
            seen[k] = 1; out.append(p)
        if limit: out = out[:limit]
        rank, lis = 0, []
        for p in out:
            rank += 1; lis.append(row(p, rank))
        return '<ol class="pl">' + "".join(lis) + "</ol>"

    def stats(ps):
        v = [unit_price(p) for p in ps if p.get("cond") == "通常"]
        if not v: return None
        return min(v), statistics.median(v), max(v), len(v)

    def facts(g):
        f = "".join(f"<dt>{esc(a)}</dt><dd>{esc(b)}</dd>" for a, b in g.get("facts", []))
        r = "".join(f"<li>{esc(x)}</li>" for x in g.get("risk", []))
        return (f'<h2>{esc(g["name"])}の基本</h2><p>{esc(g.get("lead",""))}</p><div class="card"><dl>{f}</dl></div>'
                f'<h3>主なリスク・副作用</h3><ul>{r}</ul><p class="note">一般的な目安です。効果や経過には個人差があります。</p>')

    def gsections(ps, g, limit=None, show_stats=True):
        h = ""
        for cat, label in g["subs"]:
            sp = [p for p in ps if p["cat"] == cat]
            if not sp: continue
            st = stats(sp)
            unit = "1ccあたり" if cat == "rejuran" else ""
            h += f'<h2 id="{cat}">{esc(g["short"])} {esc(label)}の料金</h2>'
            if st and show_stats:
                h += (f'<div class="stat"><div><b>{yen(st[0])}<small>円</small></b><span>最安({unit or "通常価格"})</span></div>'
                      f'<div><b>{yen(st[1])}<small>円</small></b><span>中央値</span></div><div><b>{yen(st[2])}<small>円</small></b><span>最高</span></div></div>')
            h += price_list(sp, limit)
        return h

    def app_cta(text="アプリで製剤・条件を絞り込んで比べる"):
        return f'<a class="cta" href="/">{esc(text)} ›</a>'

    local = {}
    for c in clinics:
        if c.get("scope") != "national" and c.get("pref") in PREF_SLUG:
            local.setdefault(c["pref"], []).append(c["id"])
    national = {c["id"] for c in clinics if c.get("scope") == "national"}

    # ---- clinic pages ----
    for c in clinics:
        ps = [p for p in P if p["clinicId"] == c["id"]]
        if not ps: continue
        gs = [g for g in groups if any(CAT2G.get(p["cat"]) is g for p in ps)]
        info = f'<dt>所在地</dt><dd>{esc(c.get("address") or (c.get("pref","") + " " + c.get("area","")).strip())}</dd>'
        if c.get("access"): info += f'<dt>アクセス</dt><dd>{esc(c["access"])}</dd>'
        if c.get("note"): info += f'<dt>備考</dt><dd>{esc(c["note"])}</dd>'
        info += f'<dt>公式サイト</dt><dd><a href="{esc(c.get("web"))}" rel="nofollow noopener" target="_blank">{esc((c.get("web") or "").replace("https://","").replace("http://","").rstrip("/"))}</a></dd><dt>情報確認日</dt><dd>{esc((c.get("checkedDate") or last).replace("-","/"))}</dd>'
        body = f'<h1>{esc(c["name"])}の料金一覧</h1><p class="lead">{esc(c["name"])}の{"・".join(g["short"] for g in gs)}の料金を、公式サイトの料金表から掲載しています({lastj}更新)。</p><div class="card"><dl>{info}</dl></div>'
        for g in gs:
            gp = [p for p in ps if CAT2G.get(p["cat"]) is g]
            body += f'<h2>{esc(g["name"])}</h2>'
            for cat, label in g["subs"]:
                sp = sorted([p for p in gp if p["cat"] == cat], key=lambda p: (COND_ORDER.get(p.get("cond"), 9), p["price"]))
                if sp: body += f'<h3>{esc(label)}</h3><ol class="pl np">' + "".join(row(p, compact=True) for p in sp) + "</ol>"
        rel = []
        if c.get("pref") in PREF_SLUG:
            ps_ = PREF_SLUG[c["pref"]]
            rel = [f'<a href="/{ps_}/{g["id"]}/">{esc(c["pref"])}の{esc(g["name"])}料金比較</a>' for g in gs]
        else:
            rel = [f'<a href="/{g["id"]}/">{esc(g["name"])}の料金相場(全国)</a>' for g in gs]
        body += f'<a class="cta" href="{esc(c.get("web"))}" rel="nofollow noopener" target="_blank">公式サイトで予約・問い合わせ ›</a><h2>近くのクリニックと比べる</h2><div class="links">{"".join(rel)}</div>'
        where = "全国" if c.get("scope") == "national" else c.get("pref", "")
        title = f'{c["name"]}の料金一覧｜{"・".join(g["short"] for g in gs[:3])}【{lastj}更新】｜キレイネ'
        desc = f'{c["name"]}({where})の{"・".join(g["short"] for g in gs)}の料金を公式サイトの料金表から掲載。製剤・単位・初回価格の違いもわかります。'
        crumbs = [("トップ", "/")] + ([(c["pref"], f'/{PREF_SLUG[c["pref"]]}/')] if c.get("pref") in PREF_SLUG else []) + [(c["name"], f'/clinic/{c["id"]}/')]
        write(f'clinic/{c["id"]}', title, desc, crumbs, body)

    # ---- nationwide treatment pages ----
    for g in groups:
        gp = [p for p in P if CAT2G.get(p["cat"]) is g]
        if not gp: continue
        ncl = len({p["clinicId"] for p in gp})
        prefs = []
        for pref, slug in PREFS:
            n = len({p["clinicId"] for p in gp if C[p["clinicId"]].get("pref") == pref})
            if n: prefs.append(f'<a href="/{slug}/{g["id"]}/">{esc(pref)}<small>{n}院</small></a>')
        body = (f'<h1>{esc(g["name"])}の料金相場と最安値【全国{ncl}院】</h1><p class="lead">全国{ncl}院の公式サイトに掲載された{esc(g["name"])}の料金{len(gp)}件をもとに、相場(中央値)と安い順のランキングをまとめました。{lastj}更新。</p>'
                + gsections(gp, g, limit=15) + f'<h2>都道府県から探す</h2><div class="links grid">{"".join(prefs)}</div>' + app_cta() + facts(g))
        title = f'{g["name"]}の料金相場・最安値ランキング【全国{ncl}院・{lastj}更新】｜キレイネ'
        st = stats([p for p in gp if p["cat"] == g["subs"][0][0]])
        desc = f'{g["name"]}の料金を全国{ncl}院の公式サイトから比較。' + (f'{g["subs"][0][1]}の中央値は{yen(st[1])}円、最安は{yen(st[0])}円。' if st else "") + "安い順のランキングと都道府県別の料金がわかります。"
        write(g["id"], title, desc, [("トップ", "/"), (g["name"], f'/{g["id"]}/')], body)

    # ---- prefecture hubs and prefecture x treatment ----
    for pref, slug in PREFS:
        ids = set(local.get(pref, []))
        if not ids: continue
        areas = {}
        if pref == "東京都":
            for cid in ids:
                for k in area_keys(C[cid]): areas.setdefault(k[2], [k[0], k[1], set()])[2].add(cid)
        gl = []
        for g in groups:
            lp = [p for p in P if p["clinicId"] in ids and CAT2G.get(p["cat"]) is g]
            if not lp: continue
            nloc = len({p["clinicId"] for p in lp})
            np_ = [p for p in P if p["clinicId"] in national and CAT2G.get(p["cat"]) is g]
            gl.append(f'<a href="/{slug}/{g["id"]}/">{esc(g["name"])}<small>{nloc}院</small></a>')
            sub_areas = []
            for aslug, (kind, label, cids) in sorted(areas.items(), key=lambda x: -len(x[1][2])):
                n = len({p["clinicId"] for p in lp if p["clinicId"] in cids})
                if n >= 2: sub_areas.append(f'<a href="/{slug}/{aslug}/{g["id"]}/">{esc(label)}<small>{n}院</small></a>')
            body = (f'<h1>{esc(pref)}の{esc(g["name"])}料金比較【{nloc}院・安い順】</h1>'
                    f'<p class="lead">{esc(pref)}で{esc(g["name"])}を受けられるクリニック{nloc}院の料金を、各院の公式サイトの料金表から安い順に並べました。{lastj}更新。</p>'
                    + (f'<h2>エリアで絞り込む</h2><div class="links grid">{"".join(sub_areas)}</div>' if sub_areas else "")
                    + gsections(lp, g))
            if np_:
                body += (f'<h2>全国チェーンの{esc(g["name"])}料金</h2><p class="note">全国展開のクリニックの共通料金です。{esc(pref)}内に院があるか、院ごとに料金が異なるかは各公式サイトでご確認ください。</p>'
                         + gsections(np_, g, limit=10, show_stats=False))
            other = [f'<a href="/{s2}/{g["id"]}/">{esc(p2)}</a>' for p2, s2 in PREFS if p2 != pref and local.get(p2) and any(p["clinicId"] in local[p2] and CAT2G.get(p["cat"]) is g for p in P)]
            body += app_cta() + facts(g) + f'<h2>他の都道府県の{esc(g["name"])}料金</h2><div class="links grid">{"".join(other)}</div><p><a href="/{g["id"]}/">{esc(g["name"])}の全国相場を見る ›</a></p>'
            st = stats([p for p in lp if p["cat"] == g["subs"][0][0]])
            title = f'{pref}の{g["name"]}料金比較・最安値【{nloc}院｜{lastj}更新】｜キレイネ'
            desc = f'{pref}の{g["name"]}の料金を{nloc}院の公式サイトから比較。' + (f'{g["subs"][0][1]}は最安{yen(st[0])}円・中央値{yen(st[1])}円。' if st else "") + "製剤・単位・初回価格の違いもわかります。"
            write(f'{slug}/{g["id"]}', title, desc, [("トップ", "/"), (pref, f'/{slug}/'), (g["name"], f'/{slug}/{g["id"]}/')], body)
            # area x treatment
            for aslug, (kind, label, cids) in areas.items():
                ap = [p for p in lp if p["clinicId"] in cids]
                n = len({p["clinicId"] for p in ap})
                if n < 2: continue
                where = label if kind == "ward" else f"{label}周辺"
                body = (f'<h1>{esc(where)}の{esc(g["name"])}料金比較【{n}院・安い順】</h1>'
                        f'<p class="lead">{esc(pref)}{esc(where)}で{esc(g["name"])}を受けられるクリニック{n}院の公式料金を安い順に掲載しています。{lastj}更新。</p>'
                        + gsections(ap, g) + app_cta() + f'<p><a href="/{slug}/{g["id"]}/">{esc(pref)}全体の{esc(g["name"])}料金を見る ›</a></p>' + facts(g))
                st = stats([p for p in ap if p["cat"] == g["subs"][0][0]])
                title = f'{label}の{g["name"]}料金比較・最安値【{n}院｜{lastj}更新】｜キレイネ'
                desc = f'{where}の{g["name"]}の料金を{n}院の公式サイトから比較。' + (f'{g["subs"][0][1]}は最安{yen(st[0])}円。' if st else "") + "安い順にわかります。"
                write(f'{slug}/{aslug}/{g["id"]}', title, desc, [("トップ", "/"), (pref, f'/{slug}/'), (g["name"], f'/{slug}/{g["id"]}/'), (label, f'/{slug}/{aslug}/{g["id"]}/')], body)
        cl = sorted(ids, key=lambda i: C[i]["name"])
        clinic_links = "".join(f'<a href="/clinic/{esc(i)}/">{esc(C[i]["name"])}<small>{esc(C[i].get("area",""))}</small></a>' for i in cl if any(p["clinicId"] == i for p in P))
        area_links = "".join(f'<a href="/{slug}/{a}/{g["id"]}/">{esc(v[1])}の{esc(g["short"])}</a>' for a, v in sorted(areas.items(), key=lambda x: -len(x[1][2])) for g in groups
                             if len({p["clinicId"] for p in P if p["clinicId"] in v[2] and CAT2G.get(p["cat"]) is g}) >= 2)
        body = (f'<h1>{esc(pref)}の美容皮膚科 料金比較【{len(ids)}院】</h1><p class="lead">{esc(pref)}の美容皮膚科・美容クリニック{len(ids)}院の料金を、公式サイトの料金表から施術別に比較できます。{lastj}更新。</p>'
                f'<h2>施術から探す</h2><div class="links grid">{"".join(gl)}</div>'
                + (f'<h2>エリア×施術から探す</h2><div class="links grid">{area_links}</div>' if area_links else "")
                + f'<h2>{esc(pref)}のクリニック一覧</h2><div class="links grid">{clinic_links}</div>' + app_cta())
        write(slug, f'{pref}の美容皮膚科 料金比較【{len(ids)}院｜{lastj}更新】｜キレイネ', f'{pref}の美容皮膚科{len(ids)}院のボトックス・ヒアルロン酸・リジュラン・シミ治療・医療脱毛の料金を公式サイトから比較。', [("トップ", "/"), (pref, f"/{slug}/")], body)

    return urls

def home_links(clinics, prices, groups):
    """Static link block appended to index.html so crawlers can reach the generated pages."""
    have = {c["id"] for c in clinics}
    loc = {}
    for c in clinics:
        if c.get("scope") != "national" and c.get("pref") in PREF_SLUG: loc[c["pref"]] = loc.get(c["pref"], 0) + 1
    g = "".join(f'<a href="/{x["id"]}/">{html.escape(x["name"])}の料金相場</a>' for x in groups)
    p = "".join(f'<a href="/{PREF_SLUG[k]}/">{html.escape(k)}</a>' for k, _ in PREFS if k in loc)
    return f'<footer class="kn-seo"><b>施術から探す</b><nav>{g}</nav><b>都道府県から探す</b><nav>{p}</nav><nav class="kn-legal"><a href="/about.html">運営者情報</a><a href="/terms.html">利用規約</a><a href="/privacy.html">プライバシーポリシー</a><a href="/contact.html">お問い合わせ</a></nav></footer>'
