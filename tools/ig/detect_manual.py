#!/usr/bin/env python3
"""オーナーがアプリで手動投稿したリールを見つけて ig/<folder>/posted.json を書く(キャプション冒頭で照合)。
env: IG_TOKEN, IG_USER_ID"""
import json, os, re, urllib.parse, urllib.request
T, U = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
if not T: raise SystemExit(0)
base = "ig"
norm = lambda s: re.sub(r"\s+", "", s or "")[:25]
q = urllib.parse.urlencode({"fields": "id,caption,permalink,timestamp,media_product_type", "limit": 25, "access_token": T})
media = json.load(urllib.request.urlopen(f"https://graph.instagram.com/v26.0/{U}/media?{q}", timeout=60)).get("data", [])
for d in sorted(os.listdir(base)):
    p = os.path.join(base, d)
    if not os.path.exists(os.path.join(p, "reel.mp4")) or os.path.exists(os.path.join(p, "posted.json")): continue
    try: cap = open(os.path.join(p, "caption.txt"), encoding="utf-8").read()
    except Exception: continue
    for m in media:
        if norm(m.get("caption")) and norm(m.get("caption")) == norm(cap):
            json.dump({"ig": {"media_id": m["id"], "permalink": m.get("permalink", ""), "posted_at": m.get("timestamp"), "manual": True}},
                      open(os.path.join(p, "posted.json"), "w"), ensure_ascii=False)
            print("marked", d, m.get("permalink")); break
