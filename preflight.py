"""
preflight.py — 단계 실행 전 선행조건 검증 (P0)

추측으로 진행하다 중간에 깨지지 않도록, 실행 전에 멈춰서 확인한다. (HADES §2.2)
- 입력 파일 존재
- ffmpeg / 폰트 가용
- KO / EN 줄수 1:1 (정의 §2)
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hades_util import Context, read_lyric_lines, get_logger

log = get_logger("preflight")


class PreflightError(RuntimeError):
    pass


def _check_bin(name: str, errors: list[str]) -> None:
    if shutil.which(name) is None:
        errors.append(f"실행파일 없음: {name}")


def _font_available(font_name: str) -> bool:
    try:
        out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=10).stdout
        return font_name.lower() in out.lower()
    except Exception:  # noqa: BLE001 - fc-list 없으면 검사 생략
        return True  # 폰트 확인 불가 시 통과시키되 경고는 호출부에서


def check(ctx: Context, *, need_video: bool, need_align: bool) -> None:
    errors: list[str] = []
    warns: list[str] = []

    # 입력 파일
    if not ctx.lyrics_ko.exists():
        errors.append(f"가사(KO) 없음: {ctx.lyrics_ko}")
    if need_align and not ctx.audio.exists():
        errors.append(f"음원 없음: {ctx.audio}")
    if need_video and not ctx.cover.exists():
        errors.append(f"커버 없음: {ctx.cover}")

    # 도구
    _check_bin("ffmpeg", errors)
    if need_video:
        _check_bin("ffprobe", errors)

    # KO / EN 줄수 1:1 (dual/en 모드일 때 필수)
    modes = ctx.cfg.get("subtitle", {}).get("modes", ["dual"])
    needs_en = any(m in ("en", "dual") for m in modes)
    if needs_en:
        if not ctx.lyrics_en or not ctx.lyrics_en.exists():
            errors.append(f"EN 가사 필요(모드 {modes})하나 없음: {ctx.lyrics_en}")
        elif ctx.lyrics_ko.exists():
            ko = read_lyric_lines(ctx.lyrics_ko)
            en = read_lyric_lines(ctx.lyrics_en)
            if len(ko) != len(en):
                errors.append(f"KO/EN 줄수 불일치: KO {len(ko)} vs EN {len(en)} (1:1 상속 위반)")

    # 폰트
    font = ctx.cfg.get("subtitle", {}).get("font", "Noto Sans CJK KR")
    if need_video and not _font_available(font):
        warns.append(f"폰트 미확인: '{font}' — fc-list에 없음. 설치 권장 (fonts-noto-cjk).")

    for w in warns:
        log.warning(w)
    if errors:
        msg = "프리플라이트 실패:\n  - " + "\n  - ".join(errors)
        raise PreflightError(msg)
    log.info("프리플라이트 통과 (video=%s, align=%s)", need_video, need_align)
