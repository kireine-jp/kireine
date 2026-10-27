#!/usr/bin/env python3
"""毎晩 23:30(JST/KST)に実行。今日(JST)リールが1本も投稿されていなければ、未投稿の一番古いリールのフォルダ名を出力する。
出力が空なら何もしない。env: IG_TOKEN, IG_USER_ID"""
import datetime, json, os, urllib.parse, urllib.request
T, U = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
JST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(JST).date()
q = urllib.parse.urlencode({"fields": "id,timestamp,media_product_type", "limit": 15, "access_token": T})
media = json.load(urllib.request.urlopen(f"https://graph.instagram.com/v26.0/{U}/media?{q}", timeout=60)).get("data", [])
posted_today = [m for m in media if m.get("media_product_type") == "REELS"
                and datetime.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(JST).date() == today]
if posted_today:
    print("", end=""); raise SystemExit(0)
def seq(d):
    try: return json.load(open(f"ig/{d}/meta.json"))["seq"]
    except Exception: return 0
pend = sorted((d for d in os.listdir("ig") if os.path.exists(f"ig/{d}/reel.mp4") and not os.path.exists(f"ig/{d}/posted.json")), key=lambda d: (seq(d), d))
print(pend[0] if pend else "", end="")
