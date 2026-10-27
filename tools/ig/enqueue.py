#!/usr/bin/env python3
"""Instagram 投稿キュー: 未投稿が KEEP 件未満なら次のテーマのカードを ig/<日付>-<topic>/ に生成する。
usage: python3 tools/ig/enqueue.py <repo_dir> [--force]"""
import datetime, html, json, os, subprocess, sys

ROTATION = ["botox-tokyo", "booster-tokyo", "hair-tokyo", "filler-tokyo", "spot-tokyo"]
KEEP = 2
repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
force = "--force" in sys.argv
base = os.path.join(repo, "ig")
os.makedirs(base, exist_ok=True)
dirs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
pending = [d for d in dirs if not os.path.exists(os.path.join(base, d, "posted.json"))]
if len(pending) >= KEEP and not force:
    print(f"queue full ({len(pending)} pending): {pending}"); sys.exit(0)

def seq(d):
    try: return json.load(open(os.path.join(base, d, "meta.json")))["seq"]
    except Exception: return 0
dirs.sort(key=seq)
last = next((t for d in reversed(dirs) for t in ROTATION if d.endswith(t)), None)
topic = ROTATION[(ROTATION.index(last) + 1) % len(ROTATION)] if last else ROTATION[0]
today = datetime.date.today().isoformat()
name = f"{today}-{topic}"
out = os.path.join(base, name)
if os.path.exists(out):
    print("already generated today:", name); sys.exit(0)
subprocess.run([sys.executable, os.path.join(repo, "tools/ig/cards.py"), repo, out, topic], check=True)

# プレビューページ(検索除外)
imgs = sorted(f for f in os.listdir(out) if f.endswith(".jpg"))
cap = open(os.path.join(out, "caption.txt"), encoding="utf-8").read()
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>投稿プレビュー {name}</title><style>body{{margin:0;background:#FFFDFC;color:#3B2A2C;font-family:sans-serif;padding:16px}}
.g{{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory}}.g img{{width:min(80vw,360px);border-radius:10px;scroll-snap-align:start;border:1px solid #EFE5E2}}
pre{{white-space:pre-wrap;background:#F6EEEC;padding:14px;border-radius:10px;font-size:14px;line-height:1.6}}</style></head><body>
<h3>{name}（{len(imgs)}枚）</h3><div class="g">{''.join(f'<img src="{i}" alt="">' for i in imgs)}</div><pre>{html.escape(cap)}</pre></body></html>""")
json.dump({"seq": max([seq(x) for x in dirs] + [0]) + 1, "topic": topic, "created": today, "images": imgs}, open(os.path.join(out, "meta.json"), "w"), ensure_ascii=False)
print("queued", name)
