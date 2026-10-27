#!/usr/bin/env python3
"""ig/threads/queue.json の次の未投稿を Threads に投稿する(テキスト / アンケート / 連投スレッド)。
記録: ig/threads/posted.json   env: TH_TOKEN, [TH_USER_ID]"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://graph.threads.net/v1.0"
TOKEN, UID = os.environ.get("TH_TOKEN", ""), os.environ.get("TH_USER_ID", "")
repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
qf, pf = os.path.join(repo, "ig/threads/queue.json"), os.path.join(repo, "ig/threads/posted.json")
if not TOKEN:
    print("TH_TOKEN 未設定: スキップ"); sys.exit(0)

def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}" + ("?" + data.decode() if method == "GET" else "")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=None if method == "GET" else data, method=method), timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"::error::{path}: {e.code} {e.read().decode()[:400]}"); sys.exit(1)

def publish(**p):
    c = call("POST", f"{UID}/threads", media_type="TEXT", **p)["id"]
    for _ in range(30):
        s = call("GET", c, fields="status").get("status")
        if s == "FINISHED": break
        if s in ("ERROR", "EXPIRED"): print(f"::error::container {s}"); sys.exit(1)
        time.sleep(5)
    return call("POST", f"{UID}/threads_publish", creation_id=c)["id"]

Q = json.load(open(qf, encoding="utf-8"))
done = json.load(open(pf)) if os.path.exists(pf) else {}
nxt = next((q for q in Q if q["id"] not in done), None)
if not nxt:
    print("::warning::Threads のストックがありません"); sys.exit(0)
UID = UID or call("GET", "me", fields="id")["id"]
extra = {"topic_tag": nxt["topic"]} if nxt.get("topic") else {}
if nxt["type"] == "poll":
    o = nxt["poll"]; extra["poll_attachment"] = json.dumps({k: v for k, v in zip(["option_a", "option_b", "option_c", "option_d"], o)}, ensure_ascii=False)
mid = publish(text=nxt["text"], **extra)
ids = [mid]
for r in nxt.get("replies", []):          # 連投: 直前の投稿への返信としてつなげる
    time.sleep(3); ids.append(publish(text=r, reply_to_id=ids[-1]))
try: link = call("GET", mid, fields="permalink").get("permalink", "")
except SystemExit: link = ""
done[nxt["id"]] = {"ids": ids, "permalink": link, "posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
json.dump(done, open(pf, "w"), ensure_ascii=False, indent=1)
print("threads published", nxt["id"], link)
