"""「スマホで実際にサイトを見せる」画面収録風リール(1080x1920, ~13秒)。キレイネの実ページをスマホ表示で
スクロールしながら、Instagram のテキストスタンプ風の字幕を重ねる。AIっぽい作り込みより“人が画面を見せてる感”を優先。
usage: python3 tools/ig/screenreel.py <repo_dir> <out_dir> <topic>   (topic: botox-ginza / filler-tokyo など)
writes reel.mp4, cover.jpg, caption.txt"""
import json, os, re, shutil, subprocess, sys, tempfile, threading, functools, http.server, socketserver, datetime
from playwright.sync_api import sync_playwright

REPO, OUT, TOPIC = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
FPS = 30
grp, place = TOPIC.split("-", 1)
page_grp = {"jaw": "botox"}.get(grp, grp)
path = f"/tokyo/{page_grp}/" if place == "tokyo" else f"/tokyo/{place}/{page_grp}/"
if not os.path.exists(os.path.join(REPO, path.strip("/"), "index.html")):
    sys.exit(f"no page {path}")

# ローカルでサイトを配信
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=REPO)
H.log_message = lambda *a: None
srv = socketserver.TCPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

OVER = """
(()=>{const d=document.createElement('div');d.id='ov';d.style.cssText='position:fixed;left:0;right:0;top:118px;z-index:99;display:flex;justify-content:center;pointer-events:none';
document.body.appendChild(d);const t=document.createElement('div');t.id='tap';t.style.cssText='position:fixed;z-index:100;width:44px;height:44px;border-radius:50%;background:rgba(59,42,44,.18);border:2px solid rgba(255,255,255,.9);opacity:0;pointer-events:none;transform:translate(-50%,-50%)';document.body.appendChild(t);
window.__ov=(s)=>{d.innerHTML=s?'<span style="max-width:340px;word-break:keep-all;text-align:center;background:#fff;color:#3B2A2C;font:700 18px/1.5 \\'Noto Sans JP\\',\\'Noto Sans CJK JP\\',sans-serif;padding:8px 14px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.12);white-space:pre-line">'+s+'</span>':''};
window.__tap=(x,y,a)=>{t.style.left=x+'px';t.style.top=y+'px';t.style.opacity=a};})();
"""

def ease(a, b, t):
    t = max(0, min(1, t)); t = t * t * (3 - 2 * t); return a + (b - a) * t

tmp = tempfile.mkdtemp(); n = 0
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3, is_mobile=True, has_touch=True)
    pg.goto(f"http://127.0.0.1:{port}{path}"); pg.wait_for_timeout(600); pg.evaluate("document.fonts.ready")
    pg.evaluate(OVER)
    info = pg.evaluate("""()=>{const s=document.querySelector('.stat');const li=document.querySelectorAll('.pl li');
      const v=[...(s?s.querySelectorAll('b'):[])].map(b=>b.innerText.replace(/\\s/g,''));
      return {stat:s?s.getBoundingClientRect().top+scrollY:300, li3:li.length>3?li[3].getBoundingClientRect().top+scrollY:900,
              h1:document.querySelector('h1').innerText, v:v, n:li.length}}""")
    place_label = re.sub(r"(周辺)?の.*$", "", info["h1"]).replace("東京都", "東京")
    treat = re.search(r"の(.+?)料金", info["h1"]); treat = treat.group(1) if treat else ""
    lo, med = (info["v"] + ["", ""])[:2]
    y1, y2 = max(0, info["stat"] - 300), max(0, info["li3"] - 260)
    # (開始秒, 終了秒, scroll開始, scroll終了, 字幕, タップ(x,y)or None)
    tl = [(0.0, 2.4, 0, 0, f"{place_label}で{treat}、\nどこが安いか調べてみた", None),
          (2.4, 3.4, 0, y1, f"{place_label}で{treat}、\nどこが安いか調べてみた", None),
          (3.4, 6.2, y1, y1, f"最安 {lo}／真ん中 {med}\n同じ施術でこの差…", (180, 340)),
          (6.2, 9.6, y1, y2, "公式サイトの料金だけで\n安い順に並んでる", None),
          (9.6, 12.8, y2, y2, "初回価格・税込もラベルで\n見分けられるのが地味に便利", None),
          (12.8, 15.0, y2, y2, "予約前に保存しておいてね\nプロフィールのリンクからどうぞ", None)]
    for s0, s1, a, b, text, tap in tl:
        pg.evaluate("t=>window.__ov(t)", text)
        if tap is None: pg.evaluate("window.__tap(0,0,0)")
        if tap and s0 == 3.4:   # 最安の枠をうっすら強調
            pg.evaluate("()=>{const s=document.querySelector('.stat');if(s){s.style.transition='none';s.style.boxShadow='0 0 0 3px #B0675F'}}")
        frames = int((s1 - s0) * FPS)
        for f in range(frames):
            y = ease(a, b, f / max(1, frames - 1))
            pg.evaluate(f"window.scrollTo(0,{y})")
            if tap: pg.evaluate(f"window.__tap({tap[0]},{tap[1]},{0.9 if f < 10 else max(0, 0.9 - (f - 10) / 12)})")
            pg.screenshot(path=f"{tmp}/{n:05d}.jpg", type="jpeg", quality=88); n += 1
            if s0 == 3.4 and f == 20: shutil.copy(f"{tmp}/{n-1:05d}.jpg", f"{OUT}/cover.jpg")
    br.close()
srv.shutdown()

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/%05d.jpg",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", f"{OUT}/reel.mp4"], check=True)
shutil.rmtree(tmp)
U = json.load(open(f"{REPO}/data/updates.json", encoding="utf-8")); day = U[0]["date"] if U else datetime.date.today().isoformat()
y, m, d = day.split("-")
open(f"{OUT}/caption.txt", "w", encoding="utf-8").write(f"""{place_label}の{treat}、どこが安いのか うちのサイトでスマホから見てみました。

最安 {lo}、真ん中 {med}。同じ施術でもこんなに違うんだよね。
初回だけ安い院もあるから、ラベルも見てから決めてね。

予約前に保存しておくと便利です。
{place_label}以外のエリアもプロフィールのリンクから見られます。

※{int(y)}年{int(m)}月{int(d)}日時点・各院公式サイトの税込料金。最新情報は各院にご確認ください。
#{treat.replace(' ', '')} #美容医療 #美容皮膚科 #{place_label.split('・')[0]}美容""")
print("ok screenreel", n, "frames", OUT)
