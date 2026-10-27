#!/usr/bin/env python3
"""新しいコメント(Instagram)・返信(Threads)を見つけたら GitHub Issue を作って知らせる(GitHub からメール通知が届く)。
env: IG_TOKEN, IG_USER_ID, [TH_TOKEN], GITHUB_TOKEN, GITHUB_REPOSITORY"""
import json, os, re, urllib.error, urllib.parse, urllib.request

GH, REPO = os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"]
IG_TOKEN, IG_UID, TH_TOKEN = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", ""), os.environ.get("TH_TOKEN", "")

def api(base, token, path, **p):
    p["access_token"] = token
    try:
        with urllib.request.urlopen(f"{base}/{path}?{urllib.parse.urlencode(p)}", timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"::warning::{path}: {e.code} {e.read().decode()[:200]}"); return {}

def gh(method, path, body=None):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}", method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {GH}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)

seen = set()
for page in (1, 2, 3):
    for i in gh("GET", f"issues?state=all&labels=comment&per_page=100&page={page}"):
        seen.update(re.findall(r"\[c:(\w+)\]", i["title"]))
found = []
if IG_TOKEN and IG_UID:
    me = api("https://graph.instagram.com/v26.0", IG_TOKEN, IG_UID, fields="username").get("username")
    for m in api("https://graph.instagram.com/v26.0", IG_TOKEN, f"{IG_UID}/media", fields="id,permalink,caption", limit=12).get("data", []):
        for c in api("https://graph.instagram.com/v26.0", IG_TOKEN, f"{m['id']}/comments", fields="id,text,username,timestamp", limit=50).get("data", []):
            if c.get("username") != me: found.append(("Instagram", c["id"], c.get("username", ""), c.get("text", ""), m.get("permalink", ""), (m.get("caption") or "").split("\n")[0][:40]))
if TH_TOKEN:
    T = "https://graph.threads.net/v1.0"
    me = api(T, TH_TOKEN, "me", fields="id,username")
    for t in api(T, TH_TOKEN, "me/threads", fields="id,permalink,text", limit=15).get("data", []):
        for c in api(T, TH_TOKEN, f"{t['id']}/replies", fields="id,text,username,timestamp", limit=50).get("data", []):
            if c.get("username") != me.get("username"): found.append(("Threads", c["id"], c.get("username", ""), c.get("text", ""), t.get("permalink", ""), (t.get("text") or "").split("\n")[0][:40]))
new = [x for x in found if x[1] not in seen]
for src, cid, user, text, link, post in new[:20]:
    gh("POST", "issues", {"title": f"💬 {src} @{user}「{text[:30]}」 [c:{cid}]", "labels": ["comment"],
       "body": f"**새 댓글이 달렸어요** ({src})\n\n> {text}\n\n- 작성자: @{user}\n- 게시물: {post}\n- 링크: {link}\n\n1시간 안에 답글을 달면 노출에 도움이 돼요. 답글을 달았으면 이 이슈를 Close 하세요."})
print(f"new comments: {len(new)}")
