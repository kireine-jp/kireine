#!/usr/bin/env python3
"""投稿キュー: 未投稿が KEEP 件になるまで、リールとカルーセルを交互に ig/<日付>-<kind>-<topic>/ に生成する。
usage: python3 tools/ig/enqueue.py <repo_dir> [--force]"""
import datetime, html, json, os, subprocess, sys

ROT = {"card": ["botox-tokyo", "booster-tokyo", "hair-tokyo", "filler-tokyo", "spot-tokyo"],
       "reel": ["botox-tokyo", "filler-tokyo", "booster-tokyo", "spot-tokyo"]}
repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
try: PLAN = json.load(open(os.path.join(repo, "tools/ig/plan.json"), encoding="utf-8"))
except Exception: PLAN = {}
ROT = {"card": PLAN.get("card", ROT["card"]), "reel": PLAN.get("reel", ROT["reel"]), "screen": PLAN.get("screen", PLAN.get("reel", ROT["reel"]))}
PATTERN = PLAN.get("pattern", ["reel", "card"])
KEEP = PLAN.get("keep", 2)
force = "--force" in sys.argv
base = os.path.join(repo, "ig")
os.makedirs(base, exist_ok=True)

def meta(d):
    try: return json.load(open(os.path.join(base, d, "meta.json")))
    except Exception: return {}

def is_pending(d):
    try: return "ig" not in json.load(open(os.path.join(base, d, "posted.json"))) and "media_id" not in json.load(open(os.path.join(base, d, "posted.json")))
    except Exception: return True

def preview(out, name, kind):
    cap = open(os.path.join(out, "caption.txt"), encoding="utf-8").read()
    if kind in ("reel", "screen"):
        media = ('<video src="reel.mp4" poster="cover.jpg" controls playsinline style="width:min(90vw,360px);border-radius:12px"></video>'
                 '<p><a href="reel.mp4" download style="display:inline-block;background:#3B2A2C;color:#fff;padding:12px 18px;border-radius:999px;text-decoration:none">動画を保存</a> '
                 '<button onclick="navigator.clipboard.writeText(document.querySelector(\'pre\').innerText).then(()=>this.textContent=\'コピーしました\')" style="padding:12px 18px;border-radius:999px;border:1px solid #3B2A2C;background:#fff">キャプションをコピー</button></p>')
    else:
        imgs = sorted(f for f in os.listdir(out) if f.endswith(".jpg") and not f.startswith("story"))
        media = ('<div class="g">' + "".join(f'<img src="{i}" alt="">' for i in imgs) + "</div>"
                 '<p>画像を長押し →「写真に保存」(01から順に)</p>'
                 '<p><button onclick="navigator.clipboard.writeText(document.querySelector(\'pre\').innerText).then(()=>this.textContent=\'コピーしました\')" style="padding:12px 18px;border-radius:999px;border:1px solid #3B2A2C;background:#fff">キャプションをコピー</button></p>')
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>投稿プレビュー {name}</title><style>body{{margin:0;background:#FFFDFC;color:#3B2A2C;font-family:sans-serif;padding:16px}}
.g{{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory}}.g img{{width:min(80vw,360px);border-radius:10px;scroll-snap-align:start;border:1px solid #EFE5E2}}
pre{{white-space:pre-wrap;background:#F6EEEC;padding:14px;border-radius:10px;font-size:14px;line-height:1.6}}</style></head><body>
<h3>{name}（{'リール' if kind in ('reel', 'screen') else 'カルーセル'}）</h3>{media}<pre>{html.escape(cap)}</pre></body></html>""")

today = datetime.date.today().isoformat()
made = 0
while True:
    dirs = sorted((d for d in os.listdir(base) if d not in ("stories", "threads", "report") and os.path.isdir(os.path.join(base, d))), key=lambda d: (meta(d).get("seq", 0), d))
    pend = [d for d in dirs if is_pending(d)]
    if len(pend) >= KEEP and not (force and made == 0):
        print(f"queue full ({len(pend)} pending): {pend}"); break
    kind = PATTERN[sum(1 for x in dirs if meta(x).get("kind")) % len(PATTERN)]
    last_topic = next((meta(d).get("topic") for d in reversed(dirs) if meta(d).get("kind", "card") == kind), None)
    rot = ROT[kind]
    i0 = (rot.index(last_topic) + 1) % len(rot) if last_topic in rot else 0
    script = {"reel": "reel.py", "screen": "screenreel.py"}.get(kind, "cards.py")
    out = None
    for j in range(len(rot)):                     # データ不足のテーマは飛ばして次へ
        topic = rot[(i0 + j) % len(rot)]
        name = f"{today}-{kind}-{topic}"
        out = os.path.join(base, name)
        if os.path.exists(out): out = None; continue
        r = subprocess.run([sys.executable, os.path.join(repo, "tools/ig", script), repo, out, topic])
        if r.returncode == 0: break
        print("skip", topic); subprocess.run(["rm", "-rf", out]); out = None
    if not out:
        print("nothing generated"); break
    if kind != "reel" and topic.split("-")[0] in ("botox", "filler", "booster", "spot"):   # Threads用テキスト
        subprocess.run([sys.executable, os.path.join(repo, "tools/ig/reel.py"), repo, out, topic, "--text-only"], check=True)
    subprocess.run([sys.executable, os.path.join(repo, "tools/ig/newstory.py"), out], check=True)
    preview(out, name, kind)
    json.dump({"seq": max([meta(x).get("seq", 0) for x in dirs] + [0]) + 1, "kind": kind, "topic": topic, "created": today},
              open(os.path.join(out, "meta.json"), "w"), ensure_ascii=False)
    print("queued", name); made += 1
