#!/usr/bin/env python3
"""hades/fal_bg.py — fal.ai 커버 배경 생성 (최소 호출 모듈).

- FAL_KEY 는 os.environ 에서만 읽는다. 없으면 즉시 RuntimeError (레포 기록·하드코딩 절대 금지).
- generate_bg(prompt, out_path, width, height, seed) → fal-ai/flux-2-pro 호출 → httpx 다운로드·저장
  → {path, bytes, width, height, seed, requested} 반환.
- 해상도는 2560x1440 픽셀 명시(HADES §4.1 표준). seed 미지정 시 응답 seed 를 로그에 기록.
- 곡별 생성로그: <out_path>.genlog.json (프롬프트·seed·요청/실제 해상도·모델·시각) 기록.
- 단독 실행: python hades/fal_bg.py "<prompt>" <out_path> [seed]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

MODEL = "fal-ai/flux-2-pro"


def _require_key() -> None:
    """FAL_KEY 는 환경변수로만. 없으면 즉시 중단(값은 출력하지 않음)."""
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError(
            "FAL_KEY 환경변수가 없습니다 — fal.ai 키는 환경변수로만 주입하세요 "
            "(레포 파일 기록·하드코딩 금지)."
        )


def _download(url: str, attempts: int = 4) -> bytes:
    """이미지 다운로드 — httpx 우선(재시도), 전송오류 지속 시 urllib 폴백.
    불안정 TLS(예: SSL bad record mac)에서도 한 번의 생성으로 저장이 끝나도록 견고화."""
    last = None
    for i in range(attempts):
        try:
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                return r.content
        except Exception as e:        # noqa: BLE001 — 전송계열 광범위(SSL/Read/Timeout)
            last = e
            time.sleep(1.5 * (i + 1))
    import urllib.request             # httpx 연속 실패 → urllib 폴백(다른 TLS 경로)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            return resp.read()
    except Exception as e2:           # noqa: BLE001
        raise RuntimeError(
            f"다운로드 실패(httpx {attempts}회 + urllib 폴백): httpx={last!r} urllib={e2!r}")


def _write_genlog(out: Path, entry: dict) -> Path:
    """곡별 생성로그 기록 — <out>.genlog.json (프롬프트·seed·해상도·모델·시각)."""
    log_path = out.with_name(out.name + ".genlog.json")
    log_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return log_path


def generate_bg(prompt: str, out_path: str | Path,
                width: int = 2560, height: int = 1440,
                seed: int | None = None) -> dict:
    """flux-2-pro 로 배경 1장 생성 → out_path(PNG) 저장.
    해상도는 width×height 픽셀 명시(기본 2560×1440). seed 미지정 시 응답 seed 를 기록.
    {path,bytes,width,height,seed,requested,genlog} 반환."""
    _require_key()
    import fal_client  # 키 검증 후 지연 임포트

    arguments = {
        "prompt": prompt,
        "image_size": {"width": int(width), "height": int(height)},  # 픽셀 명시
        "output_format": "png",
    }
    if seed is not None:
        arguments["seed"] = int(seed)

    result = fal_client.subscribe(MODEL, arguments=arguments, with_logs=True)
    result = result or {}
    images = result.get("images") or []
    url = images[0].get("url") if images else None
    if not url:
        raise RuntimeError(f"이미지 URL 없음 — 응답 키: {list(result.keys())}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_download(url))

    # 실제 해상도: 응답 메타 우선, 없으면 저장 PNG 헤더 실측
    aw = images[0].get("width")
    ah = images[0].get("height")
    if not (aw and ah):
        try:
            from PIL import Image
            with Image.open(out) as im:
                aw, ah = im.size
        except Exception:
            aw, ah = None, None

    # 재현용 seed: 요청 seed 우선, 없으면 응답에 담긴 실제 seed
    used_seed = seed if seed is not None else result.get("seed")

    entry = {
        "model": MODEL,
        "prompt": prompt,
        "seed": used_seed,
        "seed_requested": seed,
        "requested": {"width": int(width), "height": int(height)},
        "actual": {"width": aw, "height": ah},
        "output": out.name,
        "bytes": out.stat().st_size,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    genlog = _write_genlog(out, entry)

    return {"path": out, "bytes": out.stat().st_size, "width": aw, "height": ah,
            "seed": used_seed, "requested": {"width": int(width), "height": int(height)},
            "genlog": genlog}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print('usage: python hades/fal_bg.py "<prompt>" <out_path> [seed] '
              '[width height]',
              file=sys.stderr)
        return 2
    prompt, out_path = argv[0], argv[1]
    seed = int(argv[2]) if len(argv) > 2 and argv[2].lower() not in ("", "none") else None
    width = int(argv[3]) if len(argv) > 3 else 2560
    height = int(argv[4]) if len(argv) > 4 else 1440
    t0 = time.monotonic()
    info = generate_bg(prompt, out_path, width, height, seed)
    dt = time.monotonic() - t0
    print(f"[fal_bg] OK: {info['path']} "
          f"({info['bytes']} bytes, {info['width']}x{info['height']}, "
          f"seed={info['seed']}) in {dt:.1f}s")
    print(f"[fal_bg] genlog: {info['genlog']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
