#!/usr/bin/env python3
"""
make_cover.py — 커버 이미지 생성 헬퍼 (선택)

장소 무드 그라데이션 + 한글 타이포로 1440p 커버를 만든다.
정교한 아트가 필요하면 외부 생성 이미지를 cover.jpg로 직접 넣어도 된다.

사용:
  python scripts/make_cover.py --title "관람차" --subtitle "월미도" \
      --out tracks/gwanramcha/cover.jpg --top 0a1428 --bottom 1b3a5f
"""
import argparse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",  # Linux
    "C:/Windows/Fonts/malgunbd.ttf",                         # Windows 맑은 고딕 Bold
    "C:/Windows/Fonts/malgun.ttf",
]
_FONT_REG_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "C:/Windows/Fonts/malgun.ttf",                             # Windows 맑은 고딕
]


def _pick_font(candidates):
    import os
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


FONT_BOLD = _pick_font(_FONT_BOLD_CANDIDATES)
FONT_REG = _pick_font(_FONT_REG_CANDIDATES)


def hex2rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w, h, top, bottom, dither=1.0):
    t = np.array(top, float)
    b = np.array(bottom, float)
    ramp = np.linspace(0, 1, h)[:, None]
    arr = (t[None, :] * (1 - ramp) + b[None, :] * ramp)
    arr = np.repeat(arr[:, None, :], w, axis=1)  # float (h,w,3)
    if dither > 0:
        # 약한 TPDF(삼각분포) 디더 — 8-bit 밴딩(계단)을 미세 노이즈로 흩뜨린다.
        noise = np.random.triangular(-dither, 0.0, dither, size=arr.shape)
        arr = arr + noise
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", default="0a1428")
    ap.add_argument("--bottom", default="1b3a5f")
    ap.add_argument("--size", default="2560x1440")
    ap.add_argument("--dither", type=float, default=1.0,
                    help="그라데이션 디더 강도(LSB). 0=끔, 1.0=약(권장)")
    a = ap.parse_args()

    w, h = (int(x) for x in a.size.lower().split("x"))
    img = gradient(w, h, hex2rgb(a.top), hex2rgb(a.bottom), dither=a.dither)
    d = ImageDraw.Draw(img)

    tf = ImageFont.truetype(FONT_BOLD, int(h * 0.16)) if FONT_BOLD else ImageFont.load_default()
    sf = ImageFont.truetype(FONT_REG, int(h * 0.05)) if FONT_REG else ImageFont.load_default()

    tb = d.textbbox((0, 0), a.title, font=tf)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx, ty = (w - tw) // 2, int(h * 0.40)
    # 부드러운 그림자
    d.text((tx + 4, ty + 4), a.title, font=tf, fill=(0, 0, 0))
    d.text((tx, ty), a.title, font=tf, fill=(245, 245, 240))

    if a.subtitle:
        sb = d.textbbox((0, 0), a.subtitle, font=sf)
        sw = sb[2] - sb[0]
        sx = (w - sw) // 2
        sy = ty + th + int(h * 0.06)
        d.text((sx, sy), a.subtitle, font=sf, fill=(200, 215, 220))

    img.save(a.out, quality=95)
    print(f"커버 저장: {a.out} ({w}x{h})")


if __name__ == "__main__":
    main()
