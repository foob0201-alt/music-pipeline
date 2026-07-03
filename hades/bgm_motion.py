#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hades/bgm_motion.py — BGM 모션 표준 v1 (VISUAL §7.2) · 루프 오버레이 아키텍처.

파이썬은 **짧은 심리스 투명 루프(RGBA, 저해상도)** 를 1회만 생성한다.
배경 Ken Burns 와 무한 반복 합성·밝기 호흡은 전부 ffmpeg 가 처리(프레임 전수 생성 없음).

  build_loop()  : 파티클 + 음표 심리스 루프(예 24s@1280x720) → qtrle .mov(알파). 1회.
  render_bgm()  : cover(zoompan) + [stream_loop] 루프 overlay(업스케일) + 오디오 → 하우스 표준.
  (--glow)      : 오디오 저역 RMS → eq brightness sendcmd 로 ±3~5% 호흡(파형/스펙트럼 금지).

원칙(§7.2): 파티클 30~60개·2~8px(소수 12px)·opacity 0.10~0.20·BPM 비례 저속·배경 팔레트
밝은 톤(순백 금지)·씬 무관 연속. 음표 선화 흰~하늘빛·opacity 0.30~0.45·동시 최대 3·제목 회피.

CLI:
  python hades/bgm_motion.py <cover> <audio> <out.mp4> [--seconds 6] [--glow] [--bpm 72]
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

W, H = 2560, 1440
LOOP_DUR = 24.0                      # 루프 길이(초) — note_life 의 정수배(심리스)
NOTE_LIFE = 6.0
NOTE_SPAWN = 2.0                     # 스폰 간격 = note_life/3 → 동시 최대 3개
LOOP_W, LOOP_H = 1280, 720           # 루프 해상도(업스케일 허용 — 파티클 소프트)


# ─────────────────────────────────────────────────────── 팔레트 / 스프라이트
def extract_palette(cover, n: int = 3) -> list[tuple[int, int, int]]:
    with Image.open(cover) as im:
        im = im.convert("RGB"); im.thumbnail((160, 160))
        arr = np.asarray(im, np.float32).reshape(-1, 3)
    luma = arr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    bright = arr[luma > np.percentile(luma, 65)]
    if len(bright) < 8:
        bright = arr
    idx = np.linspace(0, len(bright) - 1, n).astype(int)
    return [tuple(int(v) for v in np.clip(bright[i], 150, 235)) for i in idx]   # 밝되 순백 금지


def _gauss_sprite(radius: int) -> np.ndarray:
    d = max(3, radius * 2 + 1)
    y, x = np.mgrid[0:d, 0:d].astype(np.float32)
    c = (d - 1) / 2.0
    r2 = ((x - c) ** 2 + (y - c) ** 2) / (radius * radius + 1e-6)
    s = np.exp(-2.2 * r2); s[r2 > 1.6] = 0.0
    return s


def _note_sprite(color=(226, 240, 255), flag=True, px=300) -> np.ndarray:
    base = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    core = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    cx, cy, s = px * 0.42, px * 0.62, px * 0.16
    lw = max(2, int(px * 0.018))

    def draw(d, wid):
        Wc = (255, 255, 255, 255)
        hrx, hry = 0.62 * s, 0.46 * s
        d.ellipse([cx - hrx, cy - hry, cx + hrx, cy + hry], outline=Wc, width=max(2, int(wid * 0.8)))
        sx = cx + hrx * 0.86; st = cy - 2.9 * s
        d.line([(sx, cy - hry * 0.15), (sx, st)], fill=Wc, width=wid)
        if flag:
            d.arc([sx - 0.10 * s, st, sx + 1.25 * s, st + 1.5 * s], -95, 35, fill=Wc, width=wid)

    draw(ImageDraw.Draw(base), lw + 5)
    glow = base.filter(ImageFilter.GaussianBlur(px * 0.02))
    draw(ImageDraw.Draw(core), lw)
    out = Image.alpha_composite(glow, core)
    arr = np.asarray(out, np.float32)
    a = arr[:, :, 3:4] / 255.0
    rgb = np.broadcast_to(np.array(color, np.float32), arr[:, :, :3].shape)
    return np.concatenate([rgb, a * 255.0], axis=2)


# ─────────────────────────────────────────────────────── 오버 합성(투명 위)
def _over(layer, x, y, src_rgb, src_a):
    """src(RGB,alpha[0..1]) 를 layer(RGBA float) 위에 'over' 합성 (경계 클립).
    src_rgb 가 (1,1,3) 이면 브로드캐스트(슬라이스 안 함), 아니면 영역 슬라이스."""
    sh, sw = src_a.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi), min(LOOP_W, xi + sw)
    y0, y1 = max(0, yi), min(LOOP_H, yi + sh)
    if x0 >= x1 or y0 >= y1:
        return
    ay0, ay1, ax0, ax1 = y0 - yi, y1 - yi, x0 - xi, x1 - xi
    a = src_a[ay0:ay1, ax0:ax1]
    if src_rgb.shape[0] == 1 and src_rgb.shape[1] == 1:
        rgb = src_rgb                                   # (1,1,3) 브로드캐스트(파티클 단색)
    else:
        rgb = src_rgb[ay0:ay1, ax0:ax1]                 # 풀 스프라이트(음표)
    reg = layer[y0:y1, x0:x1]
    reg[:, :, :3] = reg[:, :, :3] * (1 - a) + rgb * a
    reg[:, :, 3:4] = 1 - (1 - reg[:, :, 3:4]) * (1 - a)


# ─────────────────────────────────────────────────────── 루프 생성 (1회)
def build_loop(cover, out_loop, *, bpm: float = 72.0, note_source=(0.37, 0.33),
               fps: int = 30, seed: int = 20260703) -> Path:
    """심리스 투명 루프(qtrle .mov, 알파) 1회 생성. 파티클 + 음표."""
    out_loop = Path(out_loop)
    palette = extract_palette(cover)
    rnd = np.random.default_rng(seed)
    nframes = int(LOOP_DUR * fps)
    sx, sy = note_source[0] * LOOP_W, note_source[1] * LOOP_H

    # 파티클(심리스): 세로 이동거리 = m*H (정수) → 루프 끝에서 위치 복귀
    NP = 46
    p_x0 = rnd.uniform(0, LOOP_W, NP)
    p_y0 = rnd.uniform(0, LOOP_H, NP)
    p_m = np.where(rnd.random(NP) < (bpm / 144.0), 2, 1)          # BPM↑ → 일부 2배 상승(저속 유지)
    p_rad = rnd.integers(2, 9, NP)
    p_rad[rnd.random(NP) < 0.12] = 12                            # 소수 12px 보케
    p_op = rnd.uniform(0.10, 0.20, NP).astype(np.float32)
    p_col = np.array([palette[i % len(palette)] for i in range(NP)], np.float32)
    p_c = rnd.integers(1, 3, NP)                                 # 가로 사인 정수배(심리스)
    p_ph = rnd.uniform(0, 6.28, NP)
    p_amp = rnd.uniform(6, 18, NP)
    sprites = {int(r): _gauss_sprite(int(r)) for r in np.unique(p_rad)}

    note_a = _note_sprite(flag=True)
    note_b = _note_sprite(flag=False)
    base_note_px = int(LOOP_H * 0.14)

    ff = _pipe_qtrle(out_loop, fps)
    try:
        for f in range(nframes):
            t = f / fps
            layer = np.zeros((LOOP_H, LOOP_W, 4), np.float32)
            # 파티클
            for i in range(NP):
                y = (p_y0[i] - p_m[i] * LOOP_H * (t / LOOP_DUR)) % LOOP_H
                x = (p_x0[i] + p_amp[i] * math.sin(2 * math.pi * p_c[i] * t / LOOP_DUR + p_ph[i])) % LOOP_W
                spr = sprites[int(p_rad[i])]
                a = (spr * p_op[i])[:, :, None]
                _over(layer, x - spr.shape[1] / 2, y - spr.shape[0] / 2,
                      p_col[i][None, None, :], a)
            # 음표(≤3, 심리스: 스폰 0,2,4,… 각 6s)
            s0 = NOTE_SPAWN * math.floor(t / NOTE_SPAWN)
            for j in range(3):
                s = s0 - j * NOTE_SPAWN
                age = t - s
                if age < 0 or age >= NOTE_LIFE:
                    continue
                pr = age / NOTE_LIFE
                op = 0.42 * math.sin(math.pi * pr)
                if op <= 0.02:
                    continue
                ny = sy - pr * (LOOP_H * 0.22)
                nx = sx + pr * (LOOP_W * 0.12) + ((round(s / NOTE_SPAWN) % 3) - 1) * LOOP_W * 0.05
                scpx = max(8, int((1.0 - 0.40 * pr) * base_note_px))
                spr = note_a if (round(s / NOTE_SPAWN) % 2 == 0) else note_b
                im = Image.fromarray(spr.astype(np.uint8), "RGBA").resize((scpx, scpx), Image.BILINEAR)
                sa = np.asarray(im, np.float32)
                _over(layer, nx - scpx / 2, ny - scpx / 2,
                      sa[:, :, :3], (sa[:, :, 3:4] / 255.0) * op)
            # RGBA uint8 → 파이프
            rgba = np.empty((LOOP_H, LOOP_W, 4), np.uint8)
            rgba[:, :, :3] = np.clip(layer[:, :, :3], 0, 255).astype(np.uint8)
            rgba[:, :, 3] = np.clip(layer[:, :, 3] * 255, 0, 255).astype(np.uint8)
            ff.stdin.write(rgba.tobytes())
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError(f"루프 인코딩 실패: {ff.stderr.read()[-400:] if ff.stderr else ''}")
    finally:
        if ff.stdin and not ff.stdin.closed:
            ff.stdin.close()
    return out_loop


def _pipe_qtrle(out: Path, fps: int) -> subprocess.Popen:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-video_size", f"{LOOP_W}x{LOOP_H}", "-framerate", str(fps), "-i", "-",
           "-c:v", "qtrle", "-pix_fmt", "argb", str(out)]        # 무손실·알파
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)


# ─────────────────────────────────────────────────────── 밝기 호흡 sendcmd(옵션)
def _glow_sendcmd(audio: Path, dur: float, fps: int, *, amp: float = 0.04,
                  smooth_s: float = 4.0, step: float = 0.25) -> str | None:
    """저역 RMS(4s 스무딩) → eq@e brightness 명령 파일 텍스트. 실패 시 None."""
    sr = 1000
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(audio), "-af", "lowpass=f=200",
             "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
            capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32)
    except Exception:  # noqa: BLE001
        return None
    if x.size == 0:
        return None
    win = int(smooth_s * sr)
    k = np.ones(win, np.float32) / max(1, win)
    e = np.convolve(x ** 2, k, mode="same")
    e = np.sqrt(np.maximum(e, 0))
    lo, hi = e.min(), e.max()
    lines = []
    t = 0.0
    while t < dur:
        idx = min(len(e) - 1, int(t * sr))
        norm = (e[idx] - lo) / (hi - lo + 1e-9) * 2 - 1          # -1..1
        val = amp * float(norm)
        lines.append(f"{t:.2f} eq@e brightness {val:.4f};")
        t += step
    return "\n".join(lines)


# ─────────────────────────────────────────────────────── 렌더(오버레이)
def render_bgm(cover, audio, loop, out, cfg: dict, *, glow: bool = False,
               seconds: float | None = None, preset: str | None = None) -> Path:
    cover, audio, loop, out = Path(cover), Path(audio), Path(loop), Path(out)
    v = cfg.get("video", {}); enc = dict(v.get("encode", {}))
    if preset:                                          # 테스트 가속(ultrafast 등). 최종본은 표준 preset.
        enc["preset"] = preset
    fps = int(v.get("fps", 30))
    zmax = float(v.get("ken_burns", {}).get("zoom_end", 1.08))
    dur = min(_probe_dur(audio), seconds) if seconds else _probe_dur(audio)
    frames = int(round(dur * fps))
    zstep = max(0.00005, (zmax - 1.0) / max(1, frames))

    kb = (f"[0:v]scale={W}:{H}:flags=lanczos,"
          f"zoompan=z='min(zoom+{zstep:.6f}\\,{zmax})':d={frames}"
          f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={fps}[bg]")
    ov = f"[1:v]scale={W}:{H}[ovl]"
    comp = "[bg][ovl]overlay=format=auto[m]"
    tail = f"[m]{{GLOW}}scale={W}:{H}:in_range=full:out_range=tv,format=yuv420p," \
           f"setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709[v]"

    tmp = tempfile.TemporaryDirectory()
    glow_ins = ""
    if glow:
        cmds = _glow_sendcmd(audio, dur, fps)
        if cmds:
            cf = Path(tmp.name) / "glow.cmds"; cf.write_text(cmds, encoding="utf-8")
            glow_ins = f"sendcmd=f='{cf.as_posix()}',eq@e=brightness=0,"
    out.parent.mkdir(parents=True, exist_ok=True)

    def _run(glow_chain: str):
        filt = ";".join([kb, ov, comp, tail.replace("{GLOW}", glow_chain)])
        cmd = ["ffmpeg", "-y",
               "-loop", "1", "-framerate", str(fps), "-i", str(cover),
               "-stream_loop", "-1", "-i", str(loop),
               "-i", str(audio),
               "-filter_complex", filt, "-map", "[v]", "-map", "2:a",
               "-t", f"{dur:.3f}",
               "-c:v", "libx264", "-profile:v", enc.get("profile", "high"),
               "-crf", str(enc.get("crf", 16)), "-preset", enc.get("preset", "medium"),
               "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
               "-color_range", "tv",
               "-c:a", enc.get("acodec", "aac"), "-b:a", enc.get("audio_bitrate", "384k"),
               "-ar", str(enc.get("audio_rate", 48000)),
               "-shortest", "-movflags", "+faststart", str(out)]
        return subprocess.run(cmd, capture_output=True, text=True)

    r = _run(glow_ins)
    if r.returncode != 0 and glow_ins:
        # --glow 필터 실패 시 밝기 호흡 없이 재시도(렌더 자체는 살린다)
        print("[bgm_motion] ⚠️ --glow 필터 실패 → 호흡 없이 재렌더", file=sys.stderr)
        r = _run("")
    tmp.cleanup()
    if r.returncode != 0:
        raise RuntimeError(f"오버레이 인코딩 실패: {r.stderr[-600:]}")
    return out


def _probe_dur(audio) -> float:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(audio)],
                       capture_output=True, text=True, check=True).stdout.strip()
    return float(o)


def render_bgm_video(cover, audio, out, cfg, *, note_source=(0.37, 0.33), bpm=72.0,
                     glow=False, seconds=None, loop_path=None, preset=None,
                     base=None) -> Path:
    """편의 래퍼: 루프 없으면 생성 → 오버레이 렌더. (make_video 에서 호출)
    base: 영상 Ken Burns 베이스(음표 없는 cover_base.jpg). 없으면 cover 사용."""
    out = Path(out)
    loop_path = Path(loop_path) if loop_path else out.parent / "bgm_loop.mov"
    if not loop_path.exists():
        build_loop(cover, loop_path, bpm=bpm, note_source=note_source,
                   fps=int(cfg.get("video", {}).get("fps", 30)))
    return render_bgm(base or cover, audio, loop_path, out, cfg,
                      glow=glow, seconds=seconds, preset=preset)


# ─────────────────────────────────────────────────────── CLI
def main(argv) -> int:
    ap = argparse.ArgumentParser(description="BGM 모션 표준 v1 — 루프 오버레이")
    ap.add_argument("cover"); ap.add_argument("audio"); ap.add_argument("out")
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--bpm", type=float, default=72.0)
    ap.add_argument("--glow", action="store_true")
    ap.add_argument("--note-source", default="0.37,0.33")
    ap.add_argument("--loop", default=None, help="루프 경로(기본 out 옆 bgm_loop.mov)")
    ap.add_argument("--rebuild-loop", action="store_true")
    ap.add_argument("--preset", default=None, help="x264 preset 오버라이드(테스트 ultrafast 등)")
    ap.add_argument("--base", default=None, help="Ken Burns 베이스(음표 없는 cover_base.jpg)")
    args = ap.parse_args(argv)
    import time
    ns = tuple(float(x) for x in args.note_source.split(","))
    cfg = {"video": {"fps": 30, "ken_burns": {"zoom_end": 1.08},
                     "encode": {"crf": 16, "preset": "medium", "profile": "high",
                                "acodec": "aac", "audio_bitrate": "384k", "audio_rate": 48000}}}
    loop = Path(args.loop) if args.loop else Path(args.out).parent / "bgm_loop.mov"
    t0 = time.monotonic()
    if args.rebuild_loop or not loop.exists():
        build_loop(args.cover, loop, bpm=args.bpm, note_source=ns)
        print(f"[loop] {loop} in {time.monotonic()-t0:.1f}s")
    t1 = time.monotonic()
    render_bgm(args.base or args.cover, args.audio, loop, args.out, cfg,
               glow=args.glow, seconds=args.seconds, preset=args.preset)
    print(f"[render] {args.out} in {time.monotonic()-t1:.1f}s (loop+render total {time.monotonic()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
