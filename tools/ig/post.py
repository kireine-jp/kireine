#!/usr/bin/env python3
"""ig/ の一番古い未投稿フォルダを Instagram(カルーセル or リール)と Threads に投稿する。
- フォルダに reel.mp4 があればリール、無ければ *.jpg のカルーセル
- Instagram: env IG_TOKEN, IG_USER_ID   (Instagram API with Instagram Login)
- Threads:   env TH_TOKEN, TH_USER_ID   (未設定ならスキップ)
- 投稿済みは posted.json に {"ig": {...}, "threads": {...}} で記録。片方だけ失敗しても次回もう片方は再投稿しない。
env: [SITE], [IG_DIR], [DRY_RUN=1]"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

IG_API = "https://graph.instagram.com/v26.0"
TH_API = "https://graph.threads.net/v1.0"
SITE = os.environ.get("SITE", "https://kirei-ne.com").rstrip("/")
IG_TOKEN, IG_UID = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
TH_TOKEN, TH_UID = os.environ.get("TH_TOKEN", ""), os.environ.get("TH_USER_ID", "")
DRY = os.environ.get("DRY_RUN") == "1"
repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
base = os.path.join(repo, "ig")
errors = []

def fail(msg):
    print(f"::error::{msg}"); sys.exit(1)

class ApiError(Exception): pass

def call(api, token, method, path, **params):
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{api}/{path}" + ("?" + data.decode() if method == "GET" else "")
    req = urllib.request.Request(url, data=None if method == "GET" else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise ApiError(f"{path}: {e.code} {e.read().decode()[:400]}")

UA = {"User-Agent": "Mozilla/5.0 (compatible; kireine-bot/1.0; +https://kirei-ne.com)"}
def wait_public(url, kind, tries=12):
    last = ""
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                ct = r.headers.get("Content-Type", "")
                if r.status == 200 and kind in ct:
                    return
                last = f"{r.status} {ct}"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:
            last = repr(e)[:200]
        print(f"waiting for deploy: {url} -> {last} ({i+1}/{tries})", flush=True); time.sleep(20)
    fail(f"file not public: {url} ({last})")

def wait_ready(fn, cid, done=("FINISHED",), bad=("ERROR", "EXPIRED"), tries=40, gap=10):
    for _ in range(tries):
        s = fn(cid)
        if s in done: return
        if s in bad: raise ApiError(f"container {cid} {s}")
        time.sleep(gap)
    raise ApiError(f"container {cid} not ready")

# ---------- Instagram ----------
def ig(method, path, **p): return call(IG_API, IG_TOKEN, method, path, **p)
def ig_status(cid): return ig("GET", cid, fields="status_code").get("status_code")

def post_instagram(imgs, video, cover, caption):
    if video:
        cid = ig("POST", f"{IG_UID}/media", media_type="REELS", video_url=video, caption=caption,
                 share_to_feed="true", **({"cover_url": cover} if cover else {}))["id"]
        wait_ready(ig_status, cid)
    else:
        kids = [ig("POST", f"{IG_UID}/media", image_url=u, is_carousel_item="true")["id"] for u in imgs]
        for k in kids: wait_ready(ig_status, k)
        cid = ig("POST", f"{IG_UID}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
        wait_ready(ig_status, cid)
    mid = ig("POST", f"{IG_UID}/media_publish", creation_id=cid)["id"]
    return {"media_id": mid, "permalink": ig("GET", mid, fields="permalink").get("permalink", "")}

# ---------- Threads ----------
def th(method, path, **p): return call(TH_API, TH_TOKEN, method, path, **p)
def th_status(cid): return th("GET", cid, fields="status").get("status")

def threads_text(caption):
    """IGキャプション → Threads用(500字以内・ハッシュタグは1つまで・リンク付き)"""
    lines = [l for l in caption.splitlines() if not l.strip().startswith("#")]
    tags = re.findall(r"#(\S+)", caption)
    body = "\n".join(lines).strip()
    body = body.replace("プロフィールのリンク(kirei-ne.com)から", "こちらから👉 https://kirei-ne.com")
    if "https://kirei-ne.com" not in body:
        body += "\n\n料金比較はこちら👉 https://kirei-ne.com"
    if len(body) > 490:
        body = body[:487] + "…"
    return body, (tags[0] if tags else None)

def post_threads(imgs, video, caption):
    text, tag = threads_text(caption)
    extra = {"topic_tag": tag} if tag else {}
    if video:
        cid = th("POST", f"{TH_UID}/threads", media_type="VIDEO", video_url=video, text=text, **extra)["id"]
        wait_ready(th_status, cid)
    elif len(imgs) == 1:
        cid = th("POST", f"{TH_UID}/threads", media_type="IMAGE", image_url=imgs[0], text=text, **extra)["id"]
        wait_ready(th_status, cid)
    else:
        kids = [th("POST", f"{TH_UID}/threads", media_type="IMAGE", image_url=u, is_carousel_item="true")["id"] for u in imgs[:20]]
        for k in kids: wait_ready(th_status, k)
        cid = th("POST", f"{TH_UID}/threads", media_type="CAROUSEL", children=",".join(kids), text=text, **extra)["id"]
        wait_ready(th_status, cid)
    mid = th("POST", f"{TH_UID}/threads_publish", creation_id=cid)["id"]
    try: link = th("GET", mid, fields="permalink").get("permalink", "")
    except ApiError: link = ""
    return {"media_id": mid, "permalink": link}

# ---------- main ----------
def load_posted(d):
    try:
        j = json.load(open(os.path.join(d, "posted.json")))
        return j if "ig" in j or "threads" in j else {"ig": j}  # 旧形式(IGのみ)
    except Exception:
        return {}

def seq(n):
    try: return json.load(open(os.path.join(base, n, "meta.json")))["seq"]
    except Exception: return 0

def pending(n):
    p = load_posted(os.path.join(base, n))
    return "ig" not in p or (TH_TOKEN and "threads" not in p and "threads_skip" not in p)

pick = os.environ.get("IG_DIR", "").strip()
dirs = sorted((x for x in os.listdir(base) if os.path.isdir(os.path.join(base, x))), key=lambda x: (seq(x), x))
# 未投稿: IG未投稿のもの。Threadsだけ残っているものは直近1件のみ追いかける
dirs = [x for x in dirs if pending(x)]
if pick: dirs = [pick] if pick in dirs else []
if not dirs:
    print("nothing to post"); sys.exit(0)
name = dirs[0]; d = os.path.join(base, name)
posted = load_posted(d)
caption = open(os.path.join(d, "caption.txt"), encoding="utf-8").read().strip()
video = f"{SITE}/ig/{name}/reel.mp4" if os.path.exists(os.path.join(d, "reel.mp4")) else None
cover = f"{SITE}/ig/{name}/cover.jpg" if video and os.path.exists(os.path.join(d, "cover.jpg")) else None
imgs = [] if video else [f"{SITE}/ig/{name}/{f}" for f in sorted(x for x in os.listdir(d) if re.fullmatch(r"\d+\.jpg", x))][:20]
print("post", name, "reel" if video else f"{len(imgs)} images", flush=True)
for u in ([video] if video else imgs): wait_public(u, "video/mp4" if video else "image/jpeg")
if cover: wait_public(cover, "image/jpeg")
if DRY:
    print("DRY_RUN ok"); sys.exit(0)

def save():
    json.dump(posted, open(os.path.join(d, "posted.json"), "w"), ensure_ascii=False)

if "ig" not in posted:
    if not IG_TOKEN or not IG_UID: fail("IG_TOKEN / IG_USER_ID が未設定です")
    try:
        posted["ig"] = post_instagram(imgs, video, cover, caption) | {"posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        save(); print("instagram published", posted["ig"]["permalink"], flush=True)
    except ApiError as e:
        errors.append(f"Instagram {e}")

if TH_TOKEN and TH_UID and "threads" not in posted:
    try:
        posted["threads"] = post_threads(imgs, video, caption) | {"posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        save(); print("threads published", posted["threads"]["permalink"], flush=True)
    except ApiError as e:
        errors.append(f"Threads {e}")
        if "ig" in posted:  # IGは出たのにThreadsだけ失敗 → 何度も同じ投稿を追いかけないよう記録
            posted["threads_skip"] = str(e)[:300]; save()

if errors:
    fail(" / ".join(errors))
