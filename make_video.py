"""
make_video.py — 커버 Ken Burns + 자막 굽기 + 최상화질 2-pass 인코딩

기준(HADES §4.3, 서치 확정):
- 1440p(2560x1440) · H.264 High · yuv420p · BT.709 · +faststart
- 2-pass VBR ~20Mbps(maxrate 24) · AAC-LC 48kHz 384k · 60fps · preset slow
- 모드(ko/en/dual)당 영상 1개.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

from hades_util import Context, get_logger, cover_gate_ok

log = get_logger("video")


def _probe_dur(audio: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(audio)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def _esc_sub(path: Path) -> str:
    """subtitles 필터용 경로 이스케이프(Linux)."""
    s = str(path.resolve())
    s = s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return s


def _filter(cfg: dict, ass: Path, frames: int) -> str:
    v = cfg.get("video", {})
    w, h = v.get("resolution", [2560, 1440])
    fps = v.get("fps", 60)
    kb = v.get("ken_burns", {})
    zmax = kb.get("zoom_end", 1.12)
    # 프레임당 증가량으로 곡 전체에 걸쳐 zmax까지 천천히 줌인
    zstep = max(0.00005, (zmax - 1.0) / max(1, frames))
    # 네이티브 해상도 줌(슈퍼샘플 5120x2880 미적용 — 표준 지시).
    return (
        f"[0:v]scale={w}:{h}:flags=lanczos,"
        f"zoompan=z='min(zoom+{zstep:.6f}\\,{zmax})':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
        # JPEG 소스 풀레인지 → BT.709 리미티드(tv)로 변환 후 색 파라미터 태깅(§4.1)
        f"scale={w}:{h}:in_range=full:out_range=tv,"
        f"format=yuv420p,"
        f"setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709,"
        f"subtitles=filename='{_esc_sub(ass)}'[v]"
    )


def _encode(ctx: Context, ass: Path, out: Path) -> Path:
    cfg = ctx.cfg
    v = cfg.get("video", {})
    enc = v.get("encode", {})
    dur = _probe_dur(ctx.audio)
    fps = v.get("fps", 60)
    frames = int(round(dur * fps))
    fchain = _filter(cfg, ass, frames)

    bitrate = enc.get("bitrate", "20M")
    maxrate = enc.get("maxrate", "24M")
    bufsize = enc.get("bufsize", "48M")
    preset = enc.get("preset", "slow")
    profile = enc.get("profile", "high")
    two_pass = enc.get("two_pass", True)

    common_in = ["-loop", "1", "-framerate", fps, "-i", str(ctx.cover),
                 "-i", str(ctx.audio)]
    common_in = [str(x) for x in common_in]
    color = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
             "-color_range", "tv"]
    # 길이 경계: 커버는 -loop 1(무한)이라 명시적 -t 없으면 pass 1(-an)이 끝나지 않는다.
    dur_args = ["-t", f"{dur:.3f}"]
    audio_args = ["-c:a", enc.get("acodec", "aac"),
                  "-b:a", enc.get("audio_bitrate", "384k"),
                  "-ar", str(enc.get("audio_rate", 48000))]

    out.parent.mkdir(parents=True, exist_ok=True)

    if two_pass:
        with tempfile.TemporaryDirectory() as td:
            passlog = os.path.join(td, "ffpass")
            log.info("2-pass 인코딩 (pass 1) — %s", out.name)
            subprocess.run(
                ["ffmpeg", "-y", *common_in,
                 "-filter_complex", fchain, "-map", "[v]",
                 "-c:v", "libx264", "-profile:v", profile, "-b:v", bitrate,
                 "-preset", preset, "-pass", "1", "-passlogfile", passlog,
                 *dur_args, "-an", "-f", "mp4", os.devnull],
                check=True)
            log.info("2-pass 인코딩 (pass 2) — %s", out.name)
            subprocess.run(
                ["ffmpeg", "-y", *common_in,
                 "-filter_complex", fchain, "-map", "[v]", "-map", "1:a",
                 "-c:v", "libx264", "-profile:v", profile, "-b:v", bitrate,
                 "-maxrate", maxrate, "-bufsize", bufsize,
                 "-preset", preset, "-pass", "2", "-passlogfile", passlog,
                 *dur_args, *color, *audio_args, "-shortest",
                 "-movflags", "+faststart", str(out)],
                check=True)
    else:
        crf = enc.get("crf")
        if crf is not None:
            # 1-pass CRF(품질기준 단일 패스) — 정적 커버+자막 콘텐츠엔 2-pass와 화질 동등하되 시간 ½.
            log.info("1-pass CRF 인코딩 (crf=%s) — %s", crf, out.name)
            rate_args = ["-crf", str(crf)]
        else:
            log.info("단일 패스 VBR 인코딩 — %s", out.name)
            rate_args = ["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize]
        subprocess.run(
            ["ffmpeg", "-y", *common_in,
             "-filter_complex", fchain, "-map", "[v]", "-map", "1:a",
             "-c:v", "libx264", "-profile:v", profile, *rate_args, "-preset", preset,
             *dur_args, *color, *audio_args, "-shortest",
             "-movflags", "+faststart", str(out)],
            check=True)
    log.info("완료: %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


def run(ctx: Context) -> Context:
    if not ctx.ass_map:
        raise RuntimeError("ass_map 없음 — align 단계 선행 필요")
    # 코드 1차 커버 게이트: 승인(.cover_ok)과 현재 cover.jpg 해시가 일치해야만 인코딩 진행
    if not cover_gate_ok(ctx.track_dir.name):
        raise SystemExit("커버 게이트 미통과 - 인코딩 중단")
    vmap: Dict[str, Path] = {}
    for mode, ass in ctx.ass_map.items():
        out = ctx.out_dir / f"{ctx.track_dir.name}_{mode}.mp4"
        vmap[mode] = _encode(ctx, ass, out)
    ctx.video_map = vmap
    return ctx
