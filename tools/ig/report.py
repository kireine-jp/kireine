#!/usr/bin/env python3
"""週次の成果レポート: 直近の Instagram 投稿ごとの数字と、アカウント全体の数字を ig/report/<日付>.json と .md に書く。
インサイト権限(instagram_business_manage_insights)が無い指標は空欄になるだけで止まらない。
env: IG_TOKEN, IG_USER_ID"""
import datetime, json, os, sys, urllib.error, urllib.parse, urllib.request

API = "https://graph.instagram.com/v26.0"
TOKEN, UID = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
out = os.path.join(repo, "ig", "report"); os.makedirs(out, exist_ok=True)
today = datetime.date.today(); since = today - datetime.timedelta(days=7)
notes = []

def get(path, **p):
    p["access_token"] = TOKEN
    try:
        with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(p)}", timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        notes.append(f"{path.split('/')[-1]} {p.get('metric', '')}: {e.code} {e.read().decode()[:160]}"); return None

def insight(mid, metric):
    r = get(f"{mid}/insights", metric=metric)
    try: return r["data"][0]["values"][0]["value"] if "values" in r["data"][0] else r["data"][0]["total_value"]["value"]
    except Exception: return None

acct = get(UID, fields="username,followers_count,media_count") or {}
media = (get(f"{UID}/media", fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", limit=30) or {}).get("data", [])
rows = []
for m in media:
    ts = datetime.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
    if ts.date() < today - datetime.timedelta(days=28): continue
    reel = m.get("media_product_type") == "REELS"
    r = {"date": ts.date().isoformat(), "type": "reel" if reel else m.get("media_type", "").lower(),
         "title": (m.get("caption") or "").split("\n")[0][:40], "link": m.get("permalink"),
         "likes": m.get("like_count"), "comments": m.get("comments_count")}
    for k in ["reach", "saved", "shares", "views", "total_interactions"] + (["ig_reels_avg_watch_time"] if reel else []):
        r[k] = insight(m["id"], k)
    if r.get("reach"):
        r["save_rate"] = round(100 * (r.get("saved") or 0) / r["reach"], 1)
        r["share_rate"] = round(100 * (r.get("shares") or 0) / r["reach"], 1)
    rows.append(r)

acc = {}
for k in ["reach", "profile_views", "website_clicks", "accounts_engaged", "follows_and_unfollows"]:
    r = get(f"{UID}/insights", metric=k, period="day", metric_type="total_value",
            since=int(datetime.datetime.combine(since, datetime.time()).timestamp()), until=int(datetime.datetime.combine(today, datetime.time()).timestamp()))
    try: acc[k] = r["data"][0]["total_value"]["value"]
    except Exception: acc[k] = None

rep = {"date": today.isoformat(), "followers": acct.get("followers_count"), "media_count": acct.get("media_count"), "week": acc, "posts": rows, "notes": notes[:10]}
prev = sorted(f for f in os.listdir(out) if f.endswith(".json") and f[:10] < today.isoformat())
if prev:
    try: rep["followers_prev"] = json.load(open(os.path.join(out, prev[-1])))["followers"]
    except Exception: pass
json.dump(rep, open(os.path.join(out, f"{today}.json"), "w"), ensure_ascii=False, indent=1)

f = lambda v: "-" if v is None else (f"{v:,}" if isinstance(v, int) else str(v))
md = [f"# キレイネ Instagram 週次レポート {today}", "",
      f"フォロワー: {f(rep['followers'])}" + (f"(先週 {f(rep.get('followers_prev'))})" if rep.get("followers_prev") is not None else ""),
      f"7日間: リーチ {f(acc.get('reach'))} / プロフィール表示 {f(acc.get('profile_views'))} / サイトクリック {f(acc.get('website_clicks'))} / 反応した人 {f(acc.get('accounts_engaged'))}", "",
      "| 日付 | 種類 | 内容 | リーチ | 保存 | シェア | 保存率% | シェア率% | いいね | コメント |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in sorted(rows, key=lambda r: -(r.get("reach") or 0)):
    md.append(f"| {r['date']} | {r['type']} | [{r['title']}]({r['link']}) | {f(r.get('reach'))} | {f(r.get('saved'))} | {f(r.get('shares'))} | {f(r.get('save_rate'))} | {f(r.get('share_rate'))} | {f(r.get('likes'))} | {f(r.get('comments'))} |")
if notes: md += ["", "取得できなかった指標(権限不足など):", *[f"- {n}" for n in notes[:5]]]
open(os.path.join(out, f"{today}.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
