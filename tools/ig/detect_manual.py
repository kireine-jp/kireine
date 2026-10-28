#!/usr/bin/env python3
"""オーナーがアプリで手動投稿したリールを見つけて ig/<folder>/posted.json を書く。
1) キャプション冒頭で照合 2) 照合できなければ、どのフォルダにも記録されていない新しいリールを古い未投稿リールに順に割り当て。
env: IG_TOKEN, IG_USER_ID"""
import json, os, re, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iglist import list_media, is_reel
T, U = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
if not T: raise SystemExit(0)
base = "ig"
norm = lambda s: re.sub(r"[\s#、。，,.!！?？…・「」『』()（）]+", "", s or "")[:15]
media = list_media(U, T)
for m in media: print("::notice::media", m.get("timestamp"), m.get("media_product_type"), (m.get("caption") or "")[:30].replace("\n", " "))
known = set()
for d in os.listdir(base):
    try: known.add(json.load(open(os.path.join(base, d, "posted.json")))["ig"]["media_id"])
    except Exception: pass
def seq(d):
    try: return json.load(open(os.path.join(base, d, "meta.json")))["seq"]
    except Exception: return 0
pend = sorted((d for d in os.listdir(base) if os.path.exists(os.path.join(base, d, "reel.mp4")) and not os.path.exists(os.path.join(base, d, "posted.json"))), key=lambda d: (seq(d), d))
reels = [m for m in media if is_reel(m) and m["id"] not in known]
# オーナー確認済み(media_id 未取得)のフォルダは、キャプション一致で media_id を補完する
for d in os.listdir(base):
    pj = os.path.join(base, d, "posted.json")
    try: rec = json.load(open(pj))
    except Exception: continue
    if rec.get("ig", {}).get("media_id") or not os.path.exists(os.path.join(base, d, "caption.txt")): continue
    cap = norm(open(os.path.join(base, d, "caption.txt"), encoding="utf-8").read())
    hit = next((m for m in reels if m["id"] not in known and cap and norm(m.get("caption")) == cap), None)
    if hit:
        rec["ig"].update(media_id=hit["id"], permalink=hit.get("permalink", ""), posted_at=hit.get("timestamp"))
        json.dump(rec, open(pj, "w"), ensure_ascii=False); known.add(hit["id"]); print("::notice::filled", d)
def mark(d, m, how):
    json.dump({"ig": {"media_id": m["id"], "permalink": m.get("permalink", ""), "posted_at": m.get("timestamp"), "manual": True, "matched": how}},
              open(os.path.join(base, d, "posted.json"), "w"), ensure_ascii=False)
    known.add(m["id"]); print("::notice::marked", d, how, m.get("permalink"))
for d in list(pend):
    cap = open(os.path.join(base, d, "caption.txt"), encoding="utf-8").read()
    hit = next((m for m in reels if m["id"] not in known and norm(m.get("caption")) and norm(m.get("caption")) == norm(cap)), None)
    if hit: mark(d, hit, "caption"); pend.remove(d)
left = sorted((m for m in reels if m["id"] not in known), key=lambda m: m["timestamp"])
for d in pend:
    created = json.load(open(os.path.join(base, d, "meta.json"))).get("created", "") if os.path.exists(os.path.join(base, d, "meta.json")) else ""
    m = next((m for m in left if m["timestamp"][:10] >= created and m["id"] not in known), None)
    if m: mark(d, m, "order")
