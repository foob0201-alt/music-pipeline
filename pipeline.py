#!/usr/bin/env python3
"""
pipeline.py — 오케스트레이터 (실행자)

단계: align → video → upload → threads
- `--steps all` 또는 쉼표 조합(`align,video`).
- 선행 산출물이 없으면 앞 단계를 자동 보장(예: video 요청 시 ass 없으면 align 먼저).
- 단계 사이로 Context(ass_map/video_map/youtube_urls)를 전달. (HADES §3.3)

판단은 없다. 정해진 순서를 수행할 뿐. (HADES §2.1)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import align
import make_video
import preflight
import upload_youtube
import post_threads
from hades_util import Context, load_config, get_logger

log = get_logger("pipeline")

ORDER = ["align", "video", "upload", "threads"]
DEPS = {"video": "align", "upload": "video", "threads": "upload"}


def _expand(steps: list[str]) -> list[str]:
    if "all" in steps:
        return list(ORDER)
    # 의존성 자동 보강(요청 단계의 선행을 채움)
    want = set(steps)
    changed = True
    while changed:
        changed = False
        for s in list(want):
            dep = DEPS.get(s)
            if dep and dep not in want:
                want.add(dep)
                changed = True
    return [s for s in ORDER if s in want]


def _ensure_align(ctx: Context) -> None:
    if not ctx.ass_map:
        modes = ctx.cfg.get("subtitle", {}).get("modes", ["dual"])
        for m in modes:
            p = ctx.out_dir / f"{ctx.track_dir.name}_{m}.ass"
            if p.exists():
                ctx.ass_map[m] = p


def _ensure_video(ctx: Context) -> None:
    if not ctx.video_map:
        for m in ctx.ass_map or {}:
            p = ctx.out_dir / f"{ctx.track_dir.name}_{m}.mp4"
            if p.exists():
                ctx.video_map[m] = p


def main() -> int:
    ap = argparse.ArgumentParser(description="HADES 음악 파이프라인")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--track", help="곡별 config.yaml 경로(루트 위에 병합)")
    ap.add_argument("--steps", default="all",
                    help="all 또는 쉼표 조합: align,video,upload,threads")
    args = ap.parse_args()

    cfg = load_config(args.config, args.track)
    ctx = Context.from_cfg(cfg)
    steps = _expand([s.strip() for s in args.steps.split(",") if s.strip()])
    log.info("실행 단계: %s | 곡: %s", steps, ctx.title)

    need_align = "align" in steps
    need_video = "video" in steps
    preflight.check(ctx, need_video=need_video, need_align=need_align)

    if "align" in steps:
        ctx = align.run(ctx)
    else:
        _ensure_align(ctx)

    if "video" in steps:
        ctx = make_video.run(ctx)
    else:
        _ensure_video(ctx)

    if "upload" in steps:
        ctx = upload_youtube.run(ctx)

    if "threads" in steps:
        ctx = post_threads.run(ctx)

    log.info("파이프라인 종료. 산출물: %s", ctx.out_dir)
    if ctx.youtube_urls:
        for v, u in ctx.youtube_urls.items():
            log.info("  %s → %s", v, u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
