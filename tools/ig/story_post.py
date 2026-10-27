#!/usr/bin/env python3
"""ig/stories/<日付>/ の story.jpg を Instagram ストーリーに、threads.txt + 画像を Threads に投稿する。
usage: python3 tools/ig/story_post.py <repo_dir> <YYYY-MM-DD>
env: IG_TOKEN, IG_USER_ID, [TH_TOKEN, TH_USER_ID], [SITE]"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

IG_API, TH_API = "https://graph.instagram.com/v26.0", "https://graph.threads.net/v1.0"
SITE = os.environ.get("SITE", "https://kirei-ne.com").rstrip("/")
IG_TOKEN, IG_UID = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
TH_TOKEN, TH_UID = os.environ.get("TH_TOKEN", ""), os.environ.get("TH_USER_ID", "")
UA = {"User-Agent": "Mozilla/5.0 (compatible; kireine-bot/1.0; +https://kirei-ne.com)"}
repo, day = os.path.abspath(sys.argv[1]), sys.argv[2]
d = os.path.join(repo, "ig", "stories", day)
img = f"{SITE}/ig/stories/{day}/story.jpg"
errors = []

def call(api, token, method, path, **params):
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{api}/{path}" + ("?" + data.decode() if method == "GET" else "")
    req = urllib.request.Request(url, data=None if method == "GET" else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{path}: {e.code} {e.read().decode()[:300]}")

def wait(fn, tries=30):
    for _ in range(tries):
        s = fn()
        if s == "FINISHED": return
        if s in ("ERROR", "EXPIRED"): raise RuntimeError(f"container {s}")
        time.sleep(10)
    raise RuntimeError("container not ready")

for i in range(15):   # Cloudflare のデプロイ待ち
    try:
        with urllib.request.urlopen(urllib.request.Request(img, headers=UA), timeout=60) as r:
            if r.status == 200 and "image/jpeg" in r.headers.get("Content-Type", ""): break
    except Exception: pass
    print("waiting for deploy", i + 1, flush=True); time.sleep(20)
else:
    print(f"::error::not public: {img}"); sys.exit(1)

rec = {}
if IG_TOKEN and IG_UID:
    try:
        c = call(IG_API, IG_TOKEN, "POST", f"{IG_UID}/media", media_type="STORIES", image_url=img)["id"]
        wait(lambda: call(IG_API, IG_TOKEN, "GET", c, fields="status_code").get("status_code"))
        rec["ig_story"] = call(IG_API, IG_TOKEN, "POST", f"{IG_UID}/media_publish", creation_id=c)["id"]
        print("instagram story published", rec["ig_story"], flush=True)
    except RuntimeError as e: errors.append(f"Instagram {e}")
if TH_TOKEN:
    try:
        uid = TH_UID or call(TH_API, TH_TOKEN, "GET", "me", fields="id")["id"]
        text = open(os.path.join(d, "threads.txt"), encoding="utf-8").read().strip()[:490]
        c = call(TH_API, TH_TOKEN, "POST", f"{uid}/threads", media_type="IMAGE", image_url=img, text=text)["id"]
        wait(lambda: call(TH_API, TH_TOKEN, "GET", c, fields="status").get("status"))
        rec["threads"] = call(TH_API, TH_TOKEN, "POST", f"{uid}/threads_publish", creation_id=c)["id"]
        print("threads published", rec["threads"], flush=True)
    except RuntimeError as e: errors.append(f"Threads {e}")
json.dump(rec | {"posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, open(os.path.join(d, "posted.json"), "w"))
for m in errors: print(f"::error::{m}")
sys.exit(1 if errors else 0)
