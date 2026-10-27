"""Instagram ハイライトカバー (1080x1920, theme C)。アイコンは円の中央 ~600px に収める。
usage: python3 tools/ig/highlights.py <out_dir>"""
import os, sys
from playwright.sync_api import sync_playwright

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
INK, ROSE, BLUSH = "#3B2A2C", "#9A554D", "#F6EEEC"
S = 'fill="none" stroke="#9A554D" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "botox": f'''<g {S}><path d="M70 230 L150 150"/><path d="M130 110 L190 170"/><path d="M150 130 L250 30 L270 50 L170 150"/>
<path d="M225 55 L245 75"/><path d="M200 80 L220 100"/><path d="M175 105 L195 125"/><path d="M255 25 L275 5 M265 15 L285 35"/></g>''',
    "filler": f'''<g {S}><path d="M150 30 C150 30 70 130 70 185 A80 80 0 0 0 230 185 C230 130 150 30 150 30 Z"/>
<path d="M115 190 A38 38 0 0 0 150 225"/></g>''',
    "rejuran": f'''<g {S}><path d="M150 40 L170 110 L240 130 L170 150 L150 220 L130 150 L60 130 L130 110 Z"/>
<path d="M235 200 L243 222 L265 230 L243 238 L235 260 L227 238 L205 230 L227 222 Z"/><path d="M65 205 L71 220 L86 226 L71 232 L65 247 L59 232 L44 226 L59 220 Z"/></g>''',
    "spot": f'''<g {S}><circle cx="150" cy="150" r="52"/>
<path d="M150 40 V62 M150 238 V260 M40 150 H62 M238 150 H260 M72 72 L88 88 M212 212 L228 228 M228 72 L212 88 M88 212 L72 228"/></g>''',
    "hair": f'''<g {S}><path d="M90 250 C120 170 190 100 240 50"/><path d="M240 50 C200 70 150 80 120 130 C100 165 105 200 120 215"/>
<path d="M140 150 L205 95"/><path d="M125 185 L170 160"/></g>''',
    "howto": f'''<g {S}><circle cx="150" cy="150" r="105"/><path d="M118 118 A32 32 0 1 1 162 148 C152 154 150 160 150 172"/>
<circle cx="150" cy="208" r="3" fill="#9A554D"/></g>''',
}
LABEL = {"botox": "ボトックス", "filler": "ヒアル", "rejuran": "リジュラン", "spot": "シミ・光治療", "hair": "医療脱毛", "howto": "使い方"}

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    for k, svg in ICONS.items():
        pg.set_content(f'''<!doctype html><html><body style="margin:0;width:1080px;height:1920px;background:{BLUSH};display:grid;place-items:center">
<div style="width:620px;height:620px;border-radius:50%;background:#FFFDFC;display:grid;place-items:center;box-shadow:0 0 0 2px #EADFDC">
<svg viewBox="0 0 300 300" width="330" height="330">{svg}</svg></div></body></html>''')
        pg.screenshot(path=f"{OUT}/highlight-{k}.jpg", type="jpeg", quality=92)
    b.close()
print("ok", OUT, ", ".join(f"{k}={v}" for k, v in LABEL.items()))
