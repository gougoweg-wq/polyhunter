"""Аватарка бота: радар с «умными деньгами». python assets/make_avatar.py → assets/avatar.png"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

S = 1280                      # рисуем в 2× и уменьшаем до 640 — гладкие края
C = S // 2
img = Image.new("RGB", (S, S))
px = img.load()
for y in range(S):            # радиальный градиент: центр темно-бирюзовый, края почти чёрные
    for x in range(S):
        d = math.hypot(x - C, y - C) / (S * 0.72)
        k = max(0.0, 1 - d)
        px[x, y] = (int(8 + 14 * k), int(14 + 40 * k), int(28 + 52 * k))

glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
g = ImageDraw.Draw(glow)
# луч радара: сектор с затуханием
for i in range(60):
    a0 = -40 - i * 0.9
    alpha = int(150 * (1 - i / 60) ** 2)
    g.pieslice([C - 520, C - 520, C + 520, C + 520], a0 - 0.9, a0, fill=(40, 230, 190, alpha))
glow = glow.filter(ImageFilter.GaussianBlur(6))
img.paste(glow, (0, 0), glow)

d = ImageDraw.Draw(img, "RGBA")
for r, a in ((520, 90), (390, 70), (260, 60), (130, 60)):   # кольца
    d.ellipse([C - r, C - r, C + r, C + r], outline=(60, 220, 190, a), width=5)
d.line([C - 520, C, C + 520, C], fill=(60, 220, 190, 45), width=4)
d.line([C, C - 520, C, C + 520], fill=(60, 220, 190, 45), width=4)

def blip(x, y, r, col):
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([x - r * 3, y - r * 3, x + r * 3, y + r * 3], fill=col[:3] + (90,))
    halo = halo.filter(ImageFilter.GaussianBlur(r * 1.2))
    img.paste(halo, (0, 0), halo)
    ImageDraw.Draw(img).ellipse([x - r, y - r, x + r, y + r], fill=col)

gold = (255, 196, 64, 255)
blip(C + 250, C - 300, 26, gold)          # крупная «умная» ставка на луче
blip(C + 380, C - 90, 16, gold)
blip(C - 300, C + 210, 12, (120, 240, 210, 255))
blip(C - 150, C - 330, 10, (120, 240, 210, 255))
blip(C + 120, C + 360, 9, (120, 240, 210, 255))
ImageDraw.Draw(img).ellipse([C - 18, C - 18, C + 18, C + 18], fill=(170, 255, 230))

out = img.resize((640, 640), Image.LANCZOS)
out.save(Path(__file__).with_name("avatar.png"))
print("saved", Path(__file__).with_name("avatar.png"))
