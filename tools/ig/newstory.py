"""新しい投稿のお知らせストーリー(1080x1920)を作る。usage: python3 tools/ig/newstory.py <post_dir>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

d = sys.argv[1]
src = os.path.join(d, "cover.jpg") if os.path.exists(os.path.join(d, "cover.jpg")) else os.path.join(d, "01.jpg")
INK, ROSE, BLUSH = (59, 42, 44), (154, 85, 77), (246, 238, 236)
def font(names, size):
    for n in names:
        for p in ["/usr/share/fonts/opentype/noto/", "/usr/share/fonts/truetype/noto/", "/usr/share/fonts/noto-cjk/"]:
            if os.path.exists(p + n): return ImageFont.truetype(p + n, size)
    return ImageFont.load_default()
serif = lambda s: font(["NotoSerifCJK-Medium.ttc", "NotoSerifCJK-Regular.ttc"], s)
sans = lambda s: font(["NotoSansCJK-Bold.ttc", "NotoSansCJK-Regular.ttc"], s)

bg = Image.new("RGB", (1080, 1920), BLUSH)
im = Image.open(src).convert("RGB")
w = 780; h = int(im.height * w / im.width)
if h > 1100: h = 1100; w = int(im.width * h / im.height)
im = im.resize((w, h))
sh = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((40, 50, w + 40, h + 50), 36, fill=(59, 42, 44, 60))
bg.paste(sh.filter(ImageFilter.GaussianBlur(24)), ((1080 - w) // 2 - 40, 430 - 40), sh.filter(ImageFilter.GaussianBlur(24)))
m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 36, fill=255)
bg.paste(im, ((1080 - w) // 2, 430), m)
dr = ImageDraw.Draw(bg)
dr.text((540, 250), "キレイネ", font=serif(46), fill=INK, anchor="mm")
dr.text((540, 335), "新しい投稿をアップしました", font=sans(44), fill=ROSE, anchor="mm")
y = 430 + h + 90
dr.rounded_rectangle((250, y, 830, y + 110), 55, fill=INK)
dr.text((540, y + 55), "プロフィールから見てね", font=sans(40), fill=BLUSH, anchor="mm")
bg.save(os.path.join(d, "story_new.jpg"), quality=90)
print("ok", d)
