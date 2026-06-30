#!/usr/bin/env python3
"""hades/fal_bg.py — fal.ai 커버 배경 생성 (최소 호출 모듈).

- FAL_KEY 는 os.environ 에서만 읽는다. 없으면 즉시 RuntimeError (레포 기록·하드코딩 절대 금지).
- generate_bg(prompt, out_path, image_size) → fal-ai/flux-2-pro 호출 → httpx 다운로드·저장
  → {path, bytes, width, height} 반환.
- 단독 실행: python hades/fal_bg.py "<prompt>" <out_path> [image_size]
"""
from __future__ import annotations

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


def generate_bg(prompt: str, out_path: str | Path,
                image_size: str = "landscape_16_9") -> dict:
    """flux-2-pro 로 배경 1장 생성 → out_path(PNG) 저장. {path,bytes,width,height} 반환."""
    _require_key()
    import fal_client  # 키 검증 후 지연 임포트

    result = fal_client.subscribe(
        MODEL,
        arguments={
            "prompt": prompt,
            "image_size": image_size,
            "output_format": "png",
        },
        with_logs=True,
    )
    images = (result or {}).get("images") or []
    url = images[0].get("url") if images else None
    if not url:
        raise RuntimeError(f"이미지 URL 없음 — 응답 키: {list((result or {}).keys())}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        out.write_bytes(r.content)

    # 해상도: 응답 메타 우선, 없으면 저장 PNG 헤더 실측
    w = images[0].get("width")
    h = images[0].get("height")
    if not (w and h):
        try:
            from PIL import Image
            with Image.open(out) as im:
                w, h = im.size
        except Exception:
            w, h = None, None
    return {"path": out, "bytes": out.stat().st_size, "width": w, "height": h}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print('usage: python hades/fal_bg.py "<prompt>" <out_path> [image_size]',
              file=sys.stderr)
        return 2
    prompt, out_path = argv[0], argv[1]
    image_size = argv[2] if len(argv) > 2 else "landscape_16_9"
    t0 = time.monotonic()
    info = generate_bg(prompt, out_path, image_size)
    dt = time.monotonic() - t0
    print(f"[fal_bg] OK: {info['path']} "
          f"({info['bytes']} bytes, {info['width']}x{info['height']}) in {dt:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
