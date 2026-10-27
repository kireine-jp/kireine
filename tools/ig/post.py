#!/usr/bin/env python3
"""ig/ の一番古い未投稿フォルダを Instagram にカルーセル投稿する (Instagram API with Instagram Login)。
env: IG_TOKEN, IG_USER_ID, [SITE], [IG_DIR], [DRY_RUN=1]"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://graph.instagram.com/v26.0"
SITE = os.environ.get("SITE", "https://kirei-ne.com").rstrip("/")
TOKEN, UID = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
DRY = os.environ.get("DRY_RUN") == "1"
repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
base = os.path.join(repo, "ig")

def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}" + ("?" + data.decode() if method == "GET" else "")
    req = urllib.request.Request(url, data=None if method == "GET" else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {path}: {e.code} {e.read().decode()[:500]}")

def wait_public(url, tries=20):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
                if r.status == 200 and "image/jpeg" in r.headers.get("Content-Type", ""):
                    return
        except Exception:
            pass
        print(f"waiting for deploy: {url} ({i+1}/{tries})"); time.sleep(30)
    sys.exit(f"image not public: {url}")

def wait_ready(cid):
    for _ in range(10):
        s = call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED": return
        if s in ("ERROR", "EXPIRED"): sys.exit(f"container {cid} {s}")
        time.sleep(15)
    sys.exit(f"container {cid} not ready")

pick = os.environ.get("IG_DIR", "").strip()
dirs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and not os.path.exists(os.path.join(base, d, "posted.json")))
def seq(d):
    try: return json.load(open(os.path.join(base, d, "meta.json")))["seq"]
    except Exception: return 0
dirs.sort(key=lambda d: (seq(d), d))
if pick: dirs = [pick] if pick in dirs else []
if not dirs:
    print("nothing to post"); sys.exit(0)
name = dirs[0]; d = os.path.join(base, name)
imgs = sorted(f for f in os.listdir(d) if f.endswith(".jpg"))[:20]
caption = open(os.path.join(d, "caption.txt"), encoding="utf-8").read().strip()
urls = [f"{SITE}/ig/{name}/{f}" for f in imgs]
print("post", name, len(urls), "images")
for u in urls: wait_public(u)
if DRY:
    print("DRY_RUN ok"); sys.exit(0)
if not TOKEN or not UID: sys.exit("IG_TOKEN / IG_USER_ID が未設定です")

children = []
for u in urls:
    cid = call("POST", f"{UID}/media", image_url=u, is_carousel_item="true")["id"]
    children.append(cid)
for c in children: wait_ready(c)
car = call("POST", f"{UID}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
wait_ready(car)
mid = call("POST", f"{UID}/media_publish", creation_id=car)["id"]
link = call("GET", mid, fields="permalink").get("permalink", "")
json.dump({"media_id": mid, "permalink": link, "posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
          open(os.path.join(d, "posted.json"), "w"), ensure_ascii=False)
print("published", mid, link)
