#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# cover_render.py — HADES 커버 렌더러 (네비게이터 설계 / 경로 A: 코드 제너러티브)
# ---------------------------------------------------------------------------
# VISUAL.md §3 불변 시그니처(밝은 톤·Reina·디더·타이포) + §4 가변 4축.
# 기본 스타일: Luminous Dawn (여명 글로우 + 보케 + 빛 라인아트 모티프).
#   출력 : tracks/<track>/cover.jpg  (2560×1440, 2× 슈퍼샘플, 디더 1.5 LSB)
#   실행 : python cover_render.py <track>
# ---------------------------------------------------------------------------

import sys, os, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 2560, 1440
SS   = 2                       # 슈퍼샘플 배율 (라인·글자 앤티앨리어싱)
ROOT = Path(__file__).resolve().parent

# ── 곡별 레지스트리 (네비게이터가 곡마다 추가) ────────────────────────────
TRACKS = {
    "amumaldo": {
        "style": "luminous_dawn",
        "title_ko": "아무말도",
        "title_latin": "I Said Nothing",
        "motif": "playground",          # 벤치 + 그네 (빛 라인아트)
        # 여명 팔레트(위→아래): 페리윙클 하늘 → 라벤더 → 모브로즈 → 살구 → 크림골드. 밝되 채도 유지.
        "sky": [(138,170,214), (172,168,208), (210,176,196), (244,192,148), (251,221,176)],
        "glows": [  # (x비율, y비율, 반경비율, (r,g,b), 세기) — 액센트만, 워시아웃 금지
            (0.50, 0.84, 0.50, (255, 230, 188), 0.30),   # 수평선 해(여명)
            (0.25, 0.30, 0.34, (255, 244, 222), 0.16),
            (0.80, 0.22, 0.30, (255, 232, 208), 0.14),
        ],
        "bokeh_tint": (255, 238, 206),
    },
    "bomnal": {
        "style": "bright_nocturne",
        "title_ko": "봄날",
        "title_latin": "Spring Day",
        "motif": "bomnal",              # 펼친 우산 + 남자 실루엣
    },
    "geoul_oneul": {
        "style": "mirror_afterimage",
        "title_ko": "거울 속의 오늘",
        "title_latin": "Today in the Mirror",
        "motif": "geoul",               # 거울 프레임 + 거울 속 발레리나 잔상 + 거울 밖 발레리나 주인공 + 소주잔
    },
    "donghae": {
        "style": "color_field",
        "title_ko": "동해로",
        "title_latin": "To the Sea",    # KO 아래 EN 부제(작게, 같은 좌상단 블록)
        "motif": None,                  # 모티프 생략(배경이 강함)
    },
    "geureoke": {
        "style": "color_field",
        "title_ko": "그렇게 지나간다",
        "title_latin": "That's How It Passes",   # KO 아래 EN 부제
        "motif": None,                  # 사진 배경(Soft Grain Analog 사계절 순환)이 색면 그 자체
    },
    "songdo": {
        "style": "color_field",
        "title_ko": "송도유원지",
        "title_latin": "Songdo Yuwonji",   # KO 아래 EN 부제
        "motif": None,                  # 사진 배경(송도유원지 노을·따뜻한 필름 그레인)이 색면 그 자체
    },
    "okryeon": {
        "style": "color_field",
        "title_ko": "옥련동",
        "title_latin": "Okryeon-dong",  # KO 아래 EN 부제
        "motif": None,                  # 사진 배경(옥련동 대낮 블루·바다 향한 길)이 색면 그 자체
    },
    "radio": {                          # 인스트루멘털 BGM — BGM 모션 표준 v1 (VISUAL §7)
        "style": "bgm_notes",
        "title_ko": "새벽 라디오",
        "title_latin": "Early Morning Radio",
        "motif": None,                  # 음표 선화 모티프는 render_bgm_notes 가 직접 합성
        "note_source": (0.37, 0.33),    # 음표 발원점(seed05 라디오/안테나 상단, 정규화)
        "note_count": 3,                # 정적 커버 음표 수(2~3, §7.1)
    },
}

# ── 스타일 프리셋 (팔레트 토큰) ───────────────────────────────────────────
STYLES = {
    "bright_nocturne": {
        "sky":        [(231, 243, 243), (210, 234, 235), (191, 226, 225)],  # 수직
        "ground":     [(191, 224, 223), (169, 212, 210)],
        "glow":       (246, 217, 168),   # amber 라디얼
        "window":     (245, 212, 155),   # 원경 창
        "mullion":    (233, 193, 121),   # 멀리언
        "rain":       (234, 246, 246),   # 빗줄기
        "ripple":     (127, 212, 168),   # 민트 물결
        "silhouette": (61, 90, 99),      # 실루엣 단색
        "umbrella":   (207, 155, 62),    # 우산 골드 라인
        "canopy":     (236, 205, 140),   # 캐노피 채움(40%)
        "scrim":      (20, 49, 56),      # 코너 스크림(라디얼 페이드)
        "text":       (255, 255, 255),   # 글자
        "outline":    (14, 43, 48),      # 외곽선
    },
    # ── Mirror Afterimage (거울 속의 오늘 / 잔상·Afterimage) ──
    # 발레리나 롱라인 실루엣 + 거울 속 잔상 + 달빛 푸른 톤(밝게·우중충 금지).
    # 봄날 Bright Nocturne(차갑고 어두운 야경)과 구분: 밝은 아이스블루·여백·달빛 글로우.
    "mirror_afterimage": {
        "base":       [(233, 238, 247), (212, 221, 238), (188, 200, 224)],  # 페일아이스→페리윙클→블루그레이(수직)
        "frame":      (198, 168, 96),    # 앤티크 골드 — 쿨 블루 위 거울테두리 포인트
        "dancer":     (96, 116, 150),    # 발레리나 주인공 실루엣(딥 블루그레이)
        "afterimage": (132, 150, 184),   # 거울 속 잔상(옅은 블루)
        "soju_line":  (150, 166, 196),   # 소주잔 라인(쿨)
        "glow":       (205, 217, 239),   # 달빛 후광(블루-화이트)
        "text":       (35, 48, 68),      # 딥 네이비 글자
        "scrim":      (238, 243, 251),   # 라이트 스크림(외곽)
    },
    # ── Color-Field (동해로 / fal 사진 배경 + 시그니처만) ──
    # 사진(노을 해안 로드)이 색면 그 자체. glow/모티프 없음·워시아웃 방지, 시그니처만 얹음.
    "color_field": {
        "text":    (255, 255, 255),   # 흰 제목
        "outline": (18, 26, 38),      # 딥 외곽(차콜-네이비) — 밝은 사진 위 또렷하게
    },
    "bgm_notes": {                    # 인스트루멘털(사진 위) — color_field 와 동일 가독 처리
        "text":    (255, 255, 255),
        "outline": (18, 26, 38),
    },
}

# ── 폰트 탐색 (실제 머신: 받은 ttf / 컨테이너: 폴백) ───────────────────────
def _first_font(paths, size, index=0):
    for p, idx in paths:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size, index=idx)
        except Exception:
            continue
    return None

def font_reina(size):
    # Reina 사인: Great Vibes 흘림. 없으면 흘림계 세리프 이탤릭 폴백.
    f = _first_font([
        (str(ROOT / "assets/fonts/GreatVibes-Regular.ttf"), 0),
        (str(ROOT / "GreatVibes-Regular.ttf"), 0),
        (r"C:\Windows\Fonts\GreatVibes-Regular.ttf", 0),
        ("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", 0),
    ], size)
    return f or ImageFont.load_default()

def font_latin(size):
    # 라틴 부제: Italiana. 없으면 세리프 폴백.
    f = _first_font([
        (str(ROOT / "assets/fonts/Italiana-Regular.ttf"), 0),
        (str(ROOT / "Italiana-Regular.ttf"), 0),
        (r"C:\Windows\Fonts\Italiana-Regular.ttf", 0),
        ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 0),
    ], size)
    return f or ImageFont.load_default()

def font_ko(size):
    # 한국어 제목: Noto Serif CJK KR Bold → Malgun → ttc 인덱스 스캔.
    cand = [
        (r"C:\Windows\Fonts\malgunbd.ttf", 0),
        (r"C:\Windows\Fonts\malgun.ttf", 0),
        (str(ROOT / "assets/fonts/NotoSerifCJK-Bold.ttc"), 0),
    ]
    f = _first_font(cand, size)
    if f and f.getbbox("아")[2] > 0:
        return f
    # ttc 인덱스 스캔(KR 페이스 찾기)
    for p in [
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    ]:
        if not os.path.exists(p):
            continue
        for idx in range(8):
            try:
                ff = ImageFont.truetype(p, size, index=idx)
                if ff.getbbox("아")[2] > 0:
                    return ff
            except Exception:
                continue
    return ImageFont.load_default()

# ── 배경: 여명 그라데이션 ─────────────────────────────────────────────────
def dawn_gradient(w, h, stops):
    cols = np.array(stops, dtype=np.float32)
    n = len(cols)
    ys = np.linspace(0, n - 1, h)
    lo = np.floor(ys).astype(int); hi = np.minimum(lo + 1, n - 1)
    t = (ys - lo)[:, None]
    grad = cols[lo] * (1 - t) + cols[hi] * t      # (h,3)
    img = np.repeat(grad[:, None, :], w, axis=1)   # (h,w,3)
    return img

# ── 빛(라디얼 글로우) 가산 ────────────────────────────────────────────────
def add_glow(img, cx, cy, rad, color, strength):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w]
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / float(rad ** 2)
    falloff = np.exp(-d2 * 3.2)[:, :, None]        # 부드럽되 가파른 감쇠(채도 보존)
    img += np.array(color, np.float32) * strength * falloff
    return img

# ── 보케(부드러운 빛망울) ─────────────────────────────────────────────────
def add_bokeh(base_img, tint, n=9, seed=7):
    rnd = random.Random(seed)
    h, w = base_img.size[1], base_img.size[0]
    layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        r = rnd.randint(int(w*0.012), int(w*0.045))
        x = rnd.randint(0, w); y = rnd.randint(0, int(h*0.55))
        a = rnd.randint(10, 26)
        d.ellipse([x-r, y-r, x+r, y+r], fill=tint + (a,))
    layer = layer.filter(ImageFilter.GaussianBlur(int(w*0.012)))
    return Image.alpha_composite(base_img.convert("RGBA"), layer)

# ── 상승 입자 ─────────────────────────────────────────────────────────────
def add_particles(base_img, n=70, seed=11):
    rnd = random.Random(seed)
    w, h = base_img.size
    layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x = rnd.randint(0, w); y = rnd.randint(int(h*0.25), h)
        r = rnd.randint(1, 4) * SS
        a = rnd.randint(40, 130)
        d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 250, 235, a))
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    return Image.alpha_composite(base_img, layer)

# ── 모티프: 빛 라인아트 (글로우 라인) ─────────────────────────────────────
def _glow_lines(size, draw_fn, color=(255, 248, 232), width=6, glow=18):
    """draw_fn(draw,width) 로 그린 선을 흐려서 글로우 + 또렷한 코어 합성."""
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    draw_fn(d, max(2, width + 6))                 # 굵게 → 글로우 소스
    glow_img = base.filter(ImageFilter.GaussianBlur(glow))
    core = Image.new("RGBA", size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(core)
    draw_fn(dc, width)                            # 또렷한 코어
    out = Image.alpha_composite(glow_img, core)
    # 색 입히기
    arr = np.array(out).astype(np.float32)
    a = arr[:, :, 3:4] / 255.0
    arr[:, :, :3] = np.array(color, np.float32)
    arr[:, :, 3] = (a[:, :, 0] * 255)
    return Image.fromarray(arr.astype(np.uint8))

def motif_playground(size):
    """놀이터: 그네(A프레임) + 벤치 를 빛 라인으로. 우측 하단 배치, 여백은 좌측 제목용."""
    w, h = size
    cx = int(w * 0.70)            # 모티프 중심 (우측)
    base = h * 0.78              # 지면 라인 y

    def draw(d, lw):
        # ── 그네 A프레임 ──
        sw = w * 0.20            # 그네 폭
        top = h * 0.34
        lx, rx = cx - sw/2, cx + sw/2
        apex_l = (cx - sw*0.16, top); apex_r = (cx + sw*0.16, top)
        d.line([ (lx, base), apex_l ], fill=(255,255,255,255), width=lw)   # 좌 다리
        d.line([ (cx - sw*0.34, base), apex_l ], fill=(255,255,255,255), width=lw)
        d.line([ (rx, base), apex_r ], fill=(255,255,255,255), width=lw)   # 우 다리
        d.line([ (cx + sw*0.34, base), apex_r ], fill=(255,255,255,255), width=lw)
        d.line([ apex_l, apex_r ], fill=(255,255,255,255), width=lw)       # 상단 바
        # 그네 줄 + 좌석 2
        for off in (-sw*0.08, sw*0.08):
            sx = cx + off
            d.line([ (sx, top + h*0.01), (sx, base - h*0.16) ], fill=(255,255,255,255), width=max(2,lw-2))
            d.line([ (sx - w*0.018, base - h*0.16), (sx - w*0.018, top + h*0.01) ], fill=(255,255,255,255), width=max(2,lw-2))
            seat_y = base - h*0.16
            d.line([ (sx - w*0.026, seat_y), (sx + w*0.010, seat_y) ], fill=(255,255,255,255), width=lw)

        # ── 벤치 (좌측, 모티프와 분리) ──
        bx = w * 0.30; by = base
        bw = w * 0.17; bh = h * 0.10
        seat = by - bh*0.55
        d.line([ (bx, seat), (bx+bw, seat) ], fill=(255,255,255,255), width=lw)         # 좌석
        d.line([ (bx, seat-bh*0.7), (bx+bw, seat-bh*0.7) ], fill=(255,255,255,255), width=lw)  # 등받이 상단
        for k in range(5):                                                              # 등받이 살
            sx = bx + bw*(0.08 + k*0.21)
            d.line([ (sx, seat), (sx, seat-bh*0.7) ], fill=(255,255,255,255), width=max(2,lw-3))
        for sx in (bx+bw*0.08, bx+bw*0.92):                                             # 다리
            d.line([ (sx, seat), (sx, by) ], fill=(255,255,255,255), width=lw)

    return _glow_lines(size, draw, color=(247, 185, 92), width=6*SS, glow=9*SS)

MOTIFS = {"playground": motif_playground}

# ── 모티프: 음표 선화 (BGM 모션 표준 v1 · 정적 레이어 — VISUAL §7.1) ────────
def _draw_note(d, cx, cy, s, lw, flag=True):
    """8분음표 선화(윤곽선만). 머리=타원 아웃라인, 기둥=선, 꼬리=arc. 채움 없음."""
    W = (255, 255, 255, 255)
    hrx, hry = 0.62 * s, 0.46 * s
    d.ellipse([cx - hrx, cy - hry, cx + hrx, cy + hry], outline=W, width=max(2, int(lw * 0.8)))
    stem_x = cx + hrx * 0.86
    stem_top = cy - 2.9 * s
    d.line([(stem_x, cy - hry * 0.15), (stem_x, stem_top)], fill=W, width=lw)
    if flag:                                            # 꼬리(우하향 곡선)
        d.arc([stem_x - 0.10 * s, stem_top, stem_x + 1.25 * s, stem_top + 1.5 * s],
              start=-95, end=35, fill=W, width=lw)


def motif_radio(size, source=(0.37, 0.33), n=3, seed=13):
    """라디오(안테나)에서 피어오르는 선화 음표 n개(2~3). 흰~하늘빛·윤곽선만·
    위로 갈수록 축소·상단 제목영역 회피, opacity 0.30~0.45(§7.1)."""
    w, h = size
    sx, sy = source[0] * w, source[1] * h
    top_limit = h * 0.16                                # 제목 영역 위 한계(회피)
    notes = []
    for i in range(n):
        t = i / max(1, n - 1)                           # 0(아래)→1(위)
        ny = sy - t * (sy - top_limit)
        nx = sx + (0.06 + 0.10 * t) * w                 # 위로 갈수록 우측 드리프트(좌상단 제목 회피)
        scale = (1.0 - 0.42 * t) * (h * 0.060)          # 위로 갈수록 축소
        notes.append((nx, ny, scale, i % 2 == 0))

    def draw(d, lw):
        for (nx, ny, s, flag) in notes:
            _draw_note(d, nx, ny, s, lw, flag=flag)

    layer = _glow_lines(size, draw, color=(226, 240, 255), width=4 * SS, glow=5 * SS)
    arr = np.array(layer).astype(np.float32)
    arr[:, :, 3] *= 0.42                                # opacity 상한 근처(0.30~0.45)
    return Image.fromarray(arr.astype(np.uint8))

# ── 텍스트(외곽선) ────────────────────────────────────────────────────────
def text_outlined(draw, xy, s, font, fill, stroke, sw, anchor=None):
    draw.text(xy, s, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)

# ── 디더 (삼각 분포 ~1.5 LSB) ─────────────────────────────────────────────
def dither(arr_uint8):
    a = arr_uint8.astype(np.float32)
    noise = (np.random.random(a.shape) - np.random.random(a.shape)) * 1.5  # 삼각
    return np.clip(a + noise, 0, 255).astype(np.uint8)

# ── motif: 봄날 (펼친 우산 focal + 남자 실루엣) ───────────────────────────
def motif_bomnal(size, st):
    """펼친 우산(중앙하단, 골드 라인아트·캐노피 옅은 채움) + 남자 실루엣(우측, 단색·얼굴없음)."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    gold = st["umbrella"] + (255,)
    lw = max(3, int(w * 0.0022))

    # ── 남자 실루엣 (우산 오른쪽 ~0.63w) ──
    sil = st["silhouette"] + (255,)
    cx = int(w * 0.63)
    feet = h * 0.82; top = h * 0.53            # 키 0.29h
    height = feet - top
    head_r = int(height * 0.21)                # 큰 머리(귀여움)
    head_cy = int(top + head_r)
    body_w = int(head_r * 1.7)
    body_top = head_cy + int(head_r * 0.7)
    body_bot = int(feet - height * 0.16)
    d.rounded_rectangle([cx - body_w // 2, body_top, cx + body_w // 2, body_bot],
                        radius=int(body_w * 0.45), fill=sil)              # 둥근 몸통
    d.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=sil)  # 머리
    nb = int(head_r * 0.32)                                              # 코 bump(고개 듦)
    ncx = cx + head_r - int(head_r * 0.1); ncy = head_cy - int(head_r * 0.35)
    d.ellipse([ncx - nb, ncy - nb, ncx + nb, ncy + nb], fill=sil)
    leg_w = max(4, int(body_w * 0.22))                                   # 다리 2
    for lx in (cx - body_w // 4, cx + body_w // 4):
        d.line([(lx, body_bot), (lx, int(feet))], fill=sil, width=leg_w)
    arm_y = int(body_top + (body_bot - body_top) * 0.30)                 # 짧은 팔(우산쪽)
    d.line([(cx - body_w // 2, arm_y), (int(w * 0.525), int(h * 0.66))], fill=sil, width=leg_w)

    # ── 우산 (focal, 중앙하단) ──
    ucx = w * 0.49; ctop = h * 0.39; hbot = h * 0.78
    half = w * 0.135; rim_y = h * 0.51; ry = rim_y - ctop
    dome = [int(ucx - half), int(ctop), int(ucx + half), int(rim_y + ry)]
    fill_layer = Image.new("RGBA", size, (0, 0, 0, 0))                   # 캐노피 옅은 채움(40%)
    ImageDraw.Draw(fill_layer).pieslice(dome, 180, 360, fill=st["canopy"] + (102,))
    layer = Image.alpha_composite(layer, fill_layer)
    d = ImageDraw.Draw(layer)
    d.arc(dome, 180, 360, fill=gold, width=lw)                          # 돔 외곽
    pan = 4                                                             # 스캘럽 4패널
    pts = [ucx - half + (2 * half) * k / pan for k in range(pan + 1)]
    dip = h * 0.022; mids = []
    for k in range(pan):
        x0 = pts[k]; x1 = pts[k + 1]; xm = (x0 + x1) / 2.0; mids.append(xm)
        d.line([(x0, rim_y), (xm, rim_y + dip)], fill=gold, width=lw)
        d.line([(xm, rim_y + dip), (x1, rim_y)], fill=gold, width=lw)
    for xm in mids:                                                     # 우산살 4
        d.line([(ucx, ctop), (xm, rim_y + dip)], fill=gold, width=max(2, lw - 2))
    d.line([(ucx, ctop), (ucx, hbot)], fill=gold, width=lw)             # 샤프트
    ftop = ctop - h * 0.022                                             # 꼭지(finial)
    d.line([(ucx, ctop), (ucx, ftop)], fill=gold, width=lw)
    fr = max(3, int(w * 0.004))
    d.ellipse([int(ucx - fr), int(ftop - fr), int(ucx + fr), int(ftop + fr)], fill=gold)
    cr = w * 0.022                                                      # 손잡이 크룩(J)
    d.arc([int(ucx - cr), int(hbot - cr), int(ucx + cr), int(hbot + cr)], 0, 180, fill=gold, width=lw)
    return layer

# ── bright_nocturne 레이어 헬퍼 ───────────────────────────────────────────
def vstack_gradient(w, h, sky, ground, split=0.62):
    hs = int(h * split)
    top = dawn_gradient(w, hs, sky)
    bot = dawn_gradient(w, h - hs, ground)
    return np.vstack([top, bot])

def add_window(pim, st, w, h):
    """원경 창: 따뜻한 빛 창 + 멀리언 십자 + 소프트 글로우(상단 중앙)."""
    layer = Image.new("RGBA", pim.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    wx, wy = int(w * 0.50), int(h * 0.205)
    ww, wh = int(w * 0.060), int(h * 0.125)
    x0, y0, x1, y1 = wx - ww // 2, wy - wh // 2, wx + ww // 2, wy + wh // 2
    d.rectangle([x0, y0, x1, y1], fill=st["window"] + (205,))
    mc = st["mullion"] + (235,); mw = max(2, int(w * 0.0016))
    d.line([((x0 + x1) // 2, y0), ((x0 + x1) // 2, y1)], fill=mc, width=mw)
    d.line([(x0, (y0 + y1) // 2), (x1, (y0 + y1) // 2)], fill=mc, width=mw)
    glow = layer.filter(ImageFilter.GaussianBlur(int(w * 0.010)))
    pim = Image.alpha_composite(pim, glow)
    return Image.alpha_composite(pim, layer)

def add_mint_ripple(pim, st, w, h):
    """젖은 바닥 반영: 민트 물결 밴드(블러)."""
    layer = Image.new("RGBA", pim.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer); rnd = random.Random(23)
    cy = int(h * 0.86)
    for _ in range(8):
        yy = cy + rnd.randint(int(-h * 0.04), int(h * 0.05))
        x0 = rnd.randint(int(w * 0.18), int(w * 0.48))
        x1 = x0 + rnd.randint(int(w * 0.10), int(w * 0.30))
        a = rnd.randint(16, 38)
        d.line([(x0, yy), (x1, yy)], fill=st["ripple"] + (a,), width=max(2, int(h * 0.004)))
    layer = layer.filter(ImageFilter.GaussianBlur(int(w * 0.006)))
    return Image.alpha_composite(pim, layer)

def add_rain(pim, st, w, h, n=150, seed=29):
    """빗줄기: 전체 세로, 미세 좌경사, 옅게."""
    rnd = random.Random(seed)
    layer = Image.new("RGBA", pim.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x = rnd.randint(0, w); y = rnd.randint(0, h)
        ln = rnd.randint(int(h * 0.03), int(h * 0.08))
        dx = -int(ln * 0.18)
        a = rnd.randint(18, 55)
        d.line([(x, y), (x + dx, y + ln)], fill=st["rain"] + (a,), width=max(1, int(w * 0.0008)))
    layer = layer.filter(ImageFilter.GaussianBlur(0.6 * SS))
    return Image.alpha_composite(pim, layer)

def add_corner_scrims(pim, st, w, h):
    """좌상단·우상단 라디얼 다크 페이드 — 제목/Reina 가독성."""
    yy, xx = np.mgrid[0:h, 0:w]
    def corner(ccx, ccy, rad, strg):
        d2 = ((xx - ccx) ** 2 + (yy - ccy) ** 2) / float(rad ** 2)
        return np.exp(-d2 * 2.2) * strg
    a = np.clip(corner(0, 0, h * 0.85, 0.60) + corner(w, 0, h * 0.80, 0.55), 0, 1)
    ov = np.zeros((h, w, 4), np.uint8)
    ov[..., 0], ov[..., 1], ov[..., 2] = st["scrim"]
    ov[..., 3] = (a * 255).astype(np.uint8)
    return Image.alpha_composite(pim, Image.fromarray(ov, "RGBA"))

# ── 외부 배경 이미지 베이스 (선택, --bg) ──────────────────────────────────
def _bg_base(bg_path, w, h):
    """외부 배경 이미지를 작업 캔버스(w,h)에 LANCZOS 맞춤 → RGB float (h,w,3) 베이스.
    dawn_gradient 출력과 동일 형식이라 이후 add_glow/add_grain/motif 를 그대로 적용."""
    im = Image.open(bg_path).convert("RGB").resize((w, h), Image.LANCZOS)
    return np.asarray(im).astype(np.float32)

# ── 스타일별 배경 합성 ────────────────────────────────────────────────────
def render_luminous_dawn(cfg, w, h, bg=None):
    img = _bg_base(bg, w, h) if bg else dawn_gradient(w, h, cfg["sky"])
    for gx, gy, gr, col, stg in cfg["glows"]:
        img = add_glow(img, gx * w, gy * h, gr * h, col, stg * 255)
    img = np.clip(img, 0, 255).astype(np.uint8)
    pim = Image.fromarray(img, "RGB")
    pim = add_bokeh(pim, cfg["bokeh_tint"])
    pim = add_particles(pim)
    motif = MOTIFS.get(cfg["motif"])
    if motif:
        pim = Image.alpha_composite(pim, motif((w, h)))
    return pim.convert("RGBA")

def render_bright_nocturne(cfg, w, h, bg=None):
    st = STYLES["bright_nocturne"]
    img = _bg_base(bg, w, h) if bg else vstack_gradient(w, h, st["sky"], st["ground"], 0.62)  # sky→ground 수직
    img = add_glow(img, w * 0.50, h * 0.40, h * 0.55, st["glow"], 0.20 * 255)  # amber
    img = np.clip(img, 0, 255).astype(np.uint8)
    pim = Image.fromarray(img, "RGB").convert("RGBA")
    pim = add_window(pim, st, w, h)             # 원경 창
    pim = add_mint_ripple(pim, st, w, h)        # 민트 물결
    pim = add_rain(pim, st, w, h)               # 빗줄기
    pim = Image.alpha_composite(pim, motif_bomnal((w, h), st))  # 우산+실루엣
    pim = add_corner_scrims(pim, st, w, h)      # 코너 스크림(가독성)
    return pim

# ── 필름 그레인(쿨 틴트) ──────────────────────────────────────────────────
def add_grain(pim, amount=0.05, seed=17):
    """반해상도 노이즈를 키워 부드러운 클럼프 그레인 → 쿨 틴트로 가산. 우중충 금지(밝기 유지)."""
    w, h = pim.size
    rng = np.random.default_rng(seed)
    nh, nw = max(1, h // 2), max(1, w // 2)
    noise = rng.standard_normal((nh, nw)).astype(np.float32)
    rng_span = float(noise.max() - noise.min()) or 1.0
    nimg = Image.fromarray(((noise - noise.min()) / rng_span * 255).astype(np.uint8))
    n = np.asarray(nimg.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0 - 0.5  # -0.5..0.5
    base = np.asarray(pim.convert("RGB")).astype(np.float32)
    tint = np.array([0.82, 0.90, 1.0], np.float32)        # B↑ R↓ = 쿨(달빛) 그레인
    base += (n[:, :, None] * tint[None, None, :]) * (amount * 255)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

# ── 발레리나 롱라인 실루엣(머리 위 둥근 팔·쪽머리·모은 긴 다리 푸앵트) ──────
def _ballerina(sd, cx, y0, H, fill, lw):
    """롱라인 발레리나: 오버헤드 포르드브라(머리 위 둥근 아치 팔) + 작은 머리·쪽머리(번) +
    갸름한 몸 + 모은 긴 다리, 발목→푸앵트. y0=팔 정점 y, H=정점→발끝 총 높이."""
    sh_y  = y0 + 0.215 * H
    sh_dx = 0.072 * H
    # 팔(오버헤드 둥근 아치) — 타원 상단호 + 어깨로 내려오는 짧은 전완
    arm_rx, arm_ry = 0.085 * H, 0.135 * H
    arm_cy = y0 + arm_ry                                   # 호의 정점 = y0
    sd.arc([cx - arm_rx, arm_cy - arm_ry, cx + arm_rx, arm_cy + arm_ry],
           180, 360, fill=fill, width=lw)
    sd.line([(cx - arm_rx, arm_cy), (cx - sh_dx, sh_y)], fill=fill, width=lw, joint="curve")
    sd.line([(cx + arm_rx, arm_cy), (cx + sh_dx, sh_y)], fill=fill, width=lw, joint="curve")
    # 머리 + 쪽머리(번, 정수리에 작게 겹침)
    head_rx, head_ry = 0.038 * H, 0.046 * H
    head_cy = y0 + 0.150 * H
    bun_r = 0.016 * H
    sd.ellipse([cx - bun_r, head_cy - head_ry - bun_r * 0.6, cx + bun_r, head_cy - head_ry + bun_r * 1.0], fill=fill)
    sd.ellipse([cx - head_rx, head_cy - head_ry, cx + head_rx, head_cy + head_ry], fill=fill)
    # 몸통(어깨→잘록 허리→골반) — 채움 폴리곤
    sh_pt   = sh_y + 0.01 * H
    waist_y = y0 + 0.45 * H; waist_w = 0.036 * H
    hip_y   = y0 + 0.53 * H; hip_w   = 0.056 * H
    sd.polygon([
        (cx - sh_dx * 0.66, sh_pt),
        (cx - waist_w, waist_y),
        (cx - hip_w,   hip_y),
        (cx + hip_w,   hip_y),
        (cx + waist_w, waist_y),
        (cx + sh_dx * 0.66, sh_pt),
    ], fill=fill)
    # 두 갈래 긴 다리(모은 듯, 발끝만 작은 V로 푸앵트) — 단검형 방지
    knee_y  = y0 + 0.73 * H
    ankle_y = y0 + 0.92 * H
    toe_y   = y0 + H
    gap     = 0.005 * H                                   # 다리 사이 가는 분리선
    thigh_w = 0.030 * H                                   # 허벅지(외측)
    calf_w  = 0.022 * H                                   # 종아리(외측)
    toe_w   = 0.013 * H
    for s in (-1, +1):                                    # 좌(-1)·우(+1) 다리
        sd.polygon([
            (cx + s * hip_w,            hip_y),           # 외측 골반
            (cx + s * gap,              hip_y),           # 내측 골반(중앙 근접)
            (cx + s * gap,              ankle_y),         # 내측 발목(수직 = 모은 다리)
            (cx + s * (gap + toe_w),    toe_y),           # 내측 발끝
            (cx + s * (calf_w + toe_w), toe_y),           # 외측 발끝(작은 V)
            (cx + s * calf_w,           ankle_y),         # 외측 발목
            (cx + s * thigh_w,          knee_y),          # 외측 무릎
        ], fill=fill)

# ── motif: 거울 프레임 + 거울 속 발레리나 잔상 + 거울 밖 발레리나 주인공 + 소주잔 ──
def motif_geoul(size, st):
    """잔상·Afterimage: 중앙 타원 거울(골드) 안에 발레리나의 옅은·어긋난 다중 잔상(블러),
    거울 바깥(좌측)에 롱라인 발레리나 주인공(푸앵트), 그 아래 작은 소주잔 1개."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    frame = st["frame"] + (255,)
    lw = max(3, int(w * 0.0024))

    # ── 거울 기하(스탠딩 타원 거울, 중앙) ──
    mcx, mcy = w * 0.50, h * 0.49
    mrx, mry = w * 0.116, h * 0.298
    outer = [mcx - mrx, mcy - mry, mcx + mrx, mcy + mry]
    inset = w * 0.013
    inner = [outer[0] + inset, outer[1] + inset, outer[2] - inset, outer[3] - inset]
    gin = inset * 1.7
    glass = [outer[0] + gin, outer[1] + gin, outer[2] - gin, outer[3] - gin]

    # ── 거울 속 잔상(afterimage): 같은 발레리나의 옅은 반영, 어긋난 다중 고스트(블러) ──
    ghost = Image.new("RGBA", size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(ghost)
    gH = h * 0.400                                                   # 유리 안에 온전히 들어오게 축소
    gy0 = mcy - mry + h * 0.050
    glw = max(2, int(w * 0.0026))
    for dx, a in ((w * 0.022, 55), (-w * 0.011, 80), (0.0, 120)):    # 뒤→앞, 어긋난 3겹 옅은 잔상
        _ballerina(gd, mcx + dx, gy0, gH, st["afterimage"] + (a,), glw)
    ghost = ghost.filter(ImageFilter.GaussianBlur(int(w * 0.0024)))
    gmask = Image.new("L", size, 0)
    ImageDraw.Draw(gmask).ellipse(glass, fill=255)                   # 유리면 안으로 클립
    ghost.putalpha(ImageChops.multiply(ghost.getchannel("A"), gmask))
    layer = Image.alpha_composite(layer, ghost)

    # ── 거울 프레임(앤티크 골드, 이중선 + 상단 꼭지) ──
    d = ImageDraw.Draw(layer)
    d.ellipse(outer, outline=frame, width=lw)
    d.ellipse(inner, outline=frame, width=max(2, lw - 2))
    fr = max(3, int(w * 0.004))
    d.ellipse([mcx - fr, outer[1] - fr * 2.2, mcx + fr, outer[1] - fr * 0.2], fill=frame)

    # ── 주인공: 롱라인 발레리나(거울 바깥·좌측, 푸앵트) ──
    real = Image.new("RGBA", size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(real)
    _ballerina(rd, w * 0.295, h * 0.250, h * 0.595, st["dancer"] + (200,), max(3, int(w * 0.0040)))
    layer = Image.alpha_composite(layer, real)
    d = ImageDraw.Draw(layer)

    # ── 하단 소주잔 1개(쿨 라인아트) ──
    sg = st["soju_line"] + (255,)
    glw2 = max(2, int(w * 0.0019))
    gcx, gtop = w * 0.50, h * 0.792
    gw_top, gw_bot, gh = w * 0.027, w * 0.021, h * 0.058
    gbot = gtop + gh
    d.line([(gcx - gw_top / 2, gtop), (gcx - gw_bot / 2, gbot)], fill=sg, width=glw2)   # 좌 벽
    d.line([(gcx + gw_top / 2, gtop), (gcx + gw_bot / 2, gbot)], fill=sg, width=glw2)   # 우 벽
    d.line([(gcx - gw_bot / 2, gbot), (gcx + gw_bot / 2, gbot)], fill=sg, width=glw2)   # 바닥
    d.ellipse([gcx - gw_top / 2, gtop - gh * 0.07, gcx + gw_top / 2, gtop + gh * 0.07],
              outline=sg, width=glw2)                                                    # 잔 입구
    d.line([(gcx - gw_top * 0.34, gtop + gh * 0.30), (gcx + gw_top * 0.34, gtop + gh * 0.30)],
           fill=sg, width=max(1, glw2 - 1))                                              # 술 수면
    return layer

def render_mirror_afterimage(cfg, w, h, bg=None):
    st = STYLES["mirror_afterimage"]
    img = _bg_base(bg, w, h) if bg else dawn_gradient(w, h, st["base"])  # 페일아이스→블루그레이(수직)
    img = add_glow(img, w * 0.50, h * 0.45, h * 0.40, st["glow"], 0.08 * 255)   # 달빛 후광(거울 뒤)
    img = np.clip(img, 0, 255).astype(np.uint8)
    pim = Image.fromarray(img, "RGB").convert("RGBA")
    pim = add_grain(pim, amount=0.05)                                    # 쿨 필름 그레인
    pim = Image.alpha_composite(pim, motif_geoul((w, h), st))            # 거울+잔상+발레리나+소주잔
    return pim

def render_color_field(cfg, w, h, bg=None):
    # 사진 배경(--bg)이 색면 그 자체 — glow/그레인/모티프 없음, 워시아웃 방지. 시그니처는 render()에서.
    if bg:
        img = _bg_base(bg, w, h)
    else:
        img = dawn_gradient(w, h, [(38, 58, 86), (18, 33, 58)])         # bg 없을 때 쿨 폴백
    img = np.clip(img, 0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGB").convert("RGBA")

def render_bgm_notes(cfg, w, h, bg=None, no_notes=False):
    """인스트루멘털 BGM 커버: 사진 배경 + 빛가루(상승 입자) + 음표 선화 모티프.
    (BGM 모션 표준 v1 정적 레이어 — VISUAL §7.1) 시그니처는 render()에서.
    no_notes=True: 음표·빛가루 생략(영상 베이스용 — 모션 루프가 음표·파티클을 담당해 중복 방지)."""
    if bg:
        img = _bg_base(bg, w, h)
    else:
        img = dawn_gradient(w, h, [(150, 200, 235), (120, 180, 225)])   # bg 없을 때 새벽블루 폴백
    img = np.clip(img, 0, 255).astype(np.uint8)
    pim = Image.fromarray(img, "RGB").convert("RGBA")
    if no_notes:
        return pim                                                      # 영상 베이스: 사진+시그니처만
    pim = add_particles(pim)                                             # 빛가루(상승 입자, §7.2 공존 기반)
    src = cfg.get("note_source", (0.37, 0.33))
    pim = Image.alpha_composite(pim, motif_radio((w, h), source=src, n=int(cfg.get("note_count", 3))))
    return pim

# ── 곡별 config.yaml 커버 오버라이드 (선택) ───────────────────────────────
def _track_overrides(track):
    """곡별 config.yaml 의 커버 미세조정 키만 추출(없으면 빈 dict).
    cover_render 는 본래 config.yaml 을 안 읽지만, title_ko_scale(제목 %)·
    title_en_gap(EN 부제 간격 px) 같은 per-track 오버라이드는 여기서만 선택 반영.
    로드 실패(yaml 미설치·파일 없음)해도 커버는 기본값으로 렌더된다."""
    try:
        from hades_util import load_config
        c = load_config("config.yaml", f"tracks/{track}/config.yaml")
        return {k: c[k] for k in ("title_ko_scale", "title_en_gap", "title_en_scale") if k in c}
    except Exception:        # noqa: BLE001 — 오버라이드는 부가기능, 실패해도 렌더 지속
        return {}

# ── 메인 렌더 ─────────────────────────────────────────────────────────────
def render(track, style=None, bg=None, no_notes=False, out_name="cover.jpg"):
    cfg = TRACKS.get(track)
    if cfg is None:
        raise SystemExit(f"[ERR] TRACKS에 '{track}' 정의 없음 — cover_render.py 레지스트리에 추가 필요")
    w, h = W * SS, H * SS
    style = style or cfg.get("style", "luminous_dawn")
    ov = _track_overrides(track)                       # 곡별 커버 미세조정(config.yaml)
    ko_scale = float(ov.get("title_ko_scale", 100)) / 100.0   # KO 제목 배율(기본 100%)
    en_gap   = float(ov.get("title_en_gap", 30))              # EN 부제 간격 px(기본 30)
    en_scale = float(ov.get("title_en_scale", 100)) / 100.0   # EN 부제 배율(기본 100%)

    # 1) 스타일별 배경+모티프 합성 (bg 지정 시 dawn_gradient 대신 외부 이미지 베이스)
    if style == "bright_nocturne":
        pim = render_bright_nocturne(cfg, w, h, bg=bg); legible = True
    elif style == "mirror_afterimage":
        pim = render_mirror_afterimage(cfg, w, h, bg=bg); legible = "bright_dark"
    elif style == "color_field":
        pim = render_color_field(cfg, w, h, bg=bg); legible = "photo"
    elif style == "bgm_notes":
        pim = render_bgm_notes(cfg, w, h, bg=bg, no_notes=no_notes); legible = "photo"
    else:
        pim = render_luminous_dawn(cfg, w, h, bg=bg);   legible = False

    # 2) 제목 (좌상단 mx=0.07w locked) — KO + 라틴
    ko = font_ko(int(120 * SS * ko_scale)); la = font_latin(int(42 * SS * en_scale))
    mx, my = int(w * 0.07), int(h * 0.08)
    bb = ko.getbbox(cfg["title_ko"]); ly = my + (bb[3] - bb[1]) + int(en_gap * SS)
    lx_center = mx + int(ko.getlength(cfg["title_ko"]) / 2)   # EN 부제: KO 폭 중심선에 센터(모든 트랙 공통 디폴트)

    if legible == "bright_dark":
        sty = STYLES[style]
        # 라이트 헤일로(스크림 블러) — 딥 네이비 글자를 밝은 배경 위로 띄움
        halo = Image.new("RGBA", pim.size, (0, 0, 0, 0))
        dh = ImageDraw.Draw(halo)
        dh.text((mx, my), cfg["title_ko"], font=ko, fill=sty["scrim"] + (225,),
                stroke_width=6 * SS, stroke_fill=sty["scrim"] + (225,))
        dh.text((lx_center, ly), cfg["title_latin"], font=la, anchor="ma", fill=sty["scrim"] + (205,),
                stroke_width=4 * SS, stroke_fill=sty["scrim"] + (205,))
        halo = halo.filter(ImageFilter.GaussianBlur(5 * SS))
        pim = Image.alpha_composite(pim, halo)
        draw = ImageDraw.Draw(pim)
        text_outlined(draw, (mx, my), cfg["title_ko"], ko,
                      fill=sty["text"], stroke=sty["scrim"], sw=4 * SS)    # 딥브라운+라이트 외곽
        text_outlined(draw, (lx_center, ly), cfg["title_latin"], la,
                      fill=sty["text"], stroke=sty["scrim"], sw=2 * SS, anchor="ma")
        rstroke = sty["text"]                                             # Reina 딥 외곽(번짐 없음)
    elif legible:
        sty = STYLES[style]
        # 그림자 레이어(딥, 블러)
        shadow = Image.new("RGBA", pim.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(shadow); off = 5 * SS
        ds.text((mx + off, my + off), cfg["title_ko"], font=ko, fill=sty["outline"] + (190,))
        ds.text((lx_center + off, ly + off), cfg["title_latin"], font=la, anchor="ma", fill=sty["outline"] + (170,))
        shadow = shadow.filter(ImageFilter.GaussianBlur(4 * SS))
        pim = Image.alpha_composite(pim, shadow)
        draw = ImageDraw.Draw(pim)
        text_outlined(draw, (mx, my), cfg["title_ko"], ko,
                      fill=sty["text"], stroke=sty["outline"], sw=4 * SS)   # 흰 글자+굵은 외곽
        text_outlined(draw, (lx_center, ly), cfg["title_latin"], la,
                      fill=sty["text"], stroke=sty["outline"], sw=2 * SS, anchor="ma")
        rstroke = sty["outline"]
    else:
        draw = ImageDraw.Draw(pim)
        text_outlined(draw, (mx, my), cfg["title_ko"], ko,
                      fill=(40, 32, 44), stroke=(255, 252, 245), sw=2 * SS)
        text_outlined(draw, (lx_center, ly), cfg["title_latin"], la,
                      fill=(70, 58, 64), stroke=(255, 250, 240), sw=1 * SS, anchor="ma")
        rstroke = (60, 50, 70)

    # 3) Reina 사인 (우상단 — §3 불변)
    rf = font_reina(int(96 * SS))
    text_outlined(draw, (w - int(w * 0.065), int(h * 0.075)), "Reina", rf,
                  fill=(255, 255, 255), stroke=rstroke, sw=3 * SS, anchor="ra")

    # 4) 다운샘플 + 디더(1.5 LSB) + 저장
    final = pim.convert("RGB").resize((W, H), Image.LANCZOS)
    final = Image.fromarray(dither(np.array(final)))
    outdir = ROOT / "tracks" / track
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / out_name
    final.save(out, "JPEG", quality=95, subsampling=0)
    print(f"[OK] {out}  ({W}x{H}, style={style}{', no-notes' if no_notes else ''})")
    return out

if __name__ == "__main__":
    argv = sys.argv[1:]
    style = None; bg = None; no_notes = False; out_name = "cover.jpg"
    if "--style" in argv:
        i = argv.index("--style"); style = argv[i + 1]; del argv[i:i + 2]
    if "--bg" in argv:
        i = argv.index("--bg"); bg = argv[i + 1]; del argv[i:i + 2]
    if "--out" in argv:
        i = argv.index("--out"); out_name = argv[i + 1]; del argv[i:i + 2]
    if "--no-notes" in argv:
        argv.remove("--no-notes"); no_notes = True
        if out_name == "cover.jpg":
            out_name = "cover_base.jpg"                 # 영상 베이스 기본 파일명(썸네일 cover.jpg 보존)
    if not argv:
        print("usage: python cover_render.py <track> [--style <name>] [--bg <path>] "
              "[--no-notes] [--out <name.jpg>]"); sys.exit(1)
    render(argv[0], style, bg, no_notes=no_notes, out_name=out_name)
