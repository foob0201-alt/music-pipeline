#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hades/fal_bg.py — fal.ai 커버 배경 생성 (v2: 하우스 스타일 자동화).

핵심(v2):
- 하우스 스타일 템플릿(확정 '대낮 블루' 골격) + 곡별 --scene "<한 줄>" 삽입. 네거티브 고정.
- style_ref/ 의 확정 배경을 fal FLUX.2 [pro] edit 엔드포인트(image_urls, 최대 9장)에
  멀티레퍼런스로 자동 첨부(색감/광량/필름그레인 일관성). --no-ref 로 해제.
- tone_check(): 평균 밝기·채도·황색끼(R-B)·회색끼 임계 검사. 불합격 시 seed 변경 재생성.
- generate_candidates(): 합격 N장 확보(최대 재시도 제한). 후보 배경 반환.

보안:
- FAL_KEY 는 os.environ 에서만 읽는다. 없으면 즉시 RuntimeError (레포 기록·하드코딩 절대 금지).

CLI:
  # 템플릿 모드(권장): 곡별 장면 한 줄만
  python hades/fal_bg.py <slug> --scene "<한 줄 장면>" [--candidates 3] [--seed N] [--no-ref]
  # 단일 생성(레거시): 전체 프롬프트 직접
  python hades/fal_bg.py --prompt "<full prompt>" --out <path> [--seed N] [--size 2560x1440]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

MODEL_TXT2IMG = "fal-ai/flux-2-pro"        # 텍스트→이미지 (레퍼런스 없음)
MODEL_EDIT = "fal-ai/flux-2-pro/edit"      # 멀티레퍼런스 (image_urls, 최대 9장)
REPO = Path(__file__).resolve().parent.parent
STYLE_REF_DIR = REPO / "style_ref"

# ─────────────────────────────────────────────────────────────────────────
# 하우스 스타일 템플릿 — 오늘 songdo 최종(대낮 블루) 확정 골격. {scene} 만 곡별로 교체.
# ─────────────────────────────────────────────────────────────────────────
HOUSE_STYLE = (
    "Bright clear high-key daytime photograph, {scene}, under a clean vivid blue sky. "
    "Brilliant azure and turquoise tones, crisp sharp daylight, sparkling clear water, "
    "crisp white clouds, wide open airy composition, vivid saturated fresh colors, "
    "sharp clean focus, generous bright empty blue sky across the top for title text, "
    "cinematic 16:9."
)
# 고정 네거티브(하우스 규약, CONTEXT §1 확정) — flux-2-pro 별도 negative 필드 없어 프롬프트에 명시
HOUSE_NEGATIVE = (
    " Avoid: yellow tint, sepia, golden hour, sunset, orange or amber cast, warm color wash, "
    "film wash, film grain, haze, soft blur, muted or grey tones, gloom, dark or moody tones, "
    "night, low light, washed-out desaturation, people, text, lettering, watermark, logo."
)
# 레퍼런스 사용 시 스타일-온리 지시(레퍼런스의 구도/건물 복제 금지)
REF_PREFIX = (
    "Use {refs} ONLY as strict style references for color grade, brightness, "
    "saturation and 35mm film-grain look — do NOT copy their buildings, layout or "
    "composition. Generate a completely new scene. "
)


def build_house_prompt(scene: str) -> str:
    """곡별 한 줄 장면 → 하우스 스타일 완성 프롬프트(+고정 네거티브)."""
    return HOUSE_STYLE.format(scene=scene.strip()) + HOUSE_NEGATIVE


# ─────────────────────────────────────────────────────────────────────────
# 톤 검사 — 하우스 '대낮 블루' 임계
# ─────────────────────────────────────────────────────────────────────────
# 임계값(0~255 스케일). 실측 튜닝값: blue 후보 통과 / golden 후보 탈락.
TONE_THRESH = {
    "bright_min": 110.0,   # 평균 밝기(luma) 최소 — 어두우면 탈락
    "sat_min": 40.0,       # 평균 채도(HSV S) 최소 — 회색끼면 탈락
    "warm_max": 10.0,      # 황색끼(meanR-meanB) 최대 — 넘으면 노랑/황혼으로 탈락
    "gray_frac_max": 0.62, # 저채도(S<28) 픽셀 비율 최대 — 넘으면 회색끼 탈락
    "gray_s": 28.0,        # '회색' 판정 채도 임계
}


def tone_metrics(path: str | Path) -> dict:
    """이미지의 밝기·채도·황색끼·회색끼 지표 산출(빠른 다운샘플)."""
    from PIL import Image
    import numpy as np
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((512, 512))
        arr = np.asarray(im, dtype=np.float32)
        hsv = np.asarray(im.convert("HSV"), dtype=np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sat = hsv[..., 1]
    return {
        "brightness": float(luma.mean()),
        "saturation": float(sat.mean()),
        "warm_index": float(r.mean() - b.mean()),   # +=warm/yellow, -=cool/blue
        "gray_frac": float((sat < TONE_THRESH["gray_s"]).mean()),
    }


def tone_check(path: str | Path, thresh: dict | None = None) -> dict:
    """하우스 대낮 블루 톤 합격 여부. {ok, metrics, reasons} 반환."""
    t = thresh or TONE_THRESH
    m = tone_metrics(path)
    reasons = []
    if m["brightness"] < t["bright_min"]:
        reasons.append(f"어두움(밝기 {m['brightness']:.0f}<{t['bright_min']:.0f})")
    if m["saturation"] < t["sat_min"]:
        reasons.append(f"저채도(채도 {m['saturation']:.0f}<{t['sat_min']:.0f})")
    if m["warm_index"] > t["warm_max"]:
        reasons.append(f"황색끼(R-B {m['warm_index']:.0f}>{t['warm_max']:.0f})")
    if m["gray_frac"] > t["gray_frac_max"]:
        reasons.append(f"회색끼(저채도비 {m['gray_frac']:.2f}>{t['gray_frac_max']:.2f})")
    return {"ok": not reasons, "metrics": m, "reasons": reasons}


# ─────────────────────────────────────────────────────────────────────────
# fal 호출
# ─────────────────────────────────────────────────────────────────────────
def _require_key() -> None:
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError(
            "FAL_KEY 환경변수가 없습니다 — fal.ai 키는 환경변수로만 주입하세요 "
            "(레포 파일 기록·하드코딩 금지).")


def _download(url: str, attempts: int = 4) -> bytes:
    """이미지 다운로드 — httpx 우선(재시도), 전송오류 지속 시 urllib 폴백."""
    last = None
    for i in range(attempts):
        try:
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                return r.content
        except Exception as e:        # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            return resp.read()
    except Exception as e2:           # noqa: BLE001
        raise RuntimeError(
            f"다운로드 실패(httpx {attempts}회 + urllib 폴백): httpx={last!r} urllib={e2!r}")


def _collect_style_refs(ref_dir: Path, limit: int = 9) -> list[Path]:
    """style_ref/ 의 참조 이미지(png/jpg) 수집(최대 limit장)."""
    if not ref_dir.is_dir():
        return []
    refs = sorted(p for p in ref_dir.iterdir()
                  if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    return refs[:limit]


def _write_genlog(out: Path, entry: dict) -> Path:
    log_path = out.with_name(out.name + ".genlog.json")
    log_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def generate_bg(prompt: str, out_path: str | Path,
                width: int = 2560, height: int = 1440,
                seed: int | None = None,
                reference_images: list[str | Path] | None = None) -> dict:
    """flux-2-pro 로 배경 1장 생성 → out_path(PNG) 저장.
    reference_images 가 있으면 edit 엔드포인트(image_urls)로 멀티레퍼런스 첨부.
    {path,bytes,width,height,seed,requested,genlog,model,refs} 반환."""
    _require_key()
    import fal_client  # 키 검증 후 지연 임포트

    arguments = {
        "prompt": prompt,
        "image_size": {"width": int(width), "height": int(height)},
        "output_format": "png",
    }
    if seed is not None:
        arguments["seed"] = int(seed)

    ref_urls = []
    model = MODEL_TXT2IMG
    if reference_images:
        # 로컬 파일 → fal 업로드 → image_urls. edit 엔드포인트 사용.
        for rp in reference_images:
            ref_urls.append(fal_client.upload_file(str(rp)))
        refs_tok = " and ".join(f"@image{i+1}" for i in range(len(ref_urls)))
        arguments["prompt"] = REF_PREFIX.format(refs=refs_tok) + prompt
        arguments["image_urls"] = ref_urls
        model = MODEL_EDIT

    result = fal_client.subscribe(model, arguments=arguments, with_logs=True) or {}
    images = result.get("images") or []
    url = images[0].get("url") if images else None
    if not url:
        raise RuntimeError(f"이미지 URL 없음 — 응답 키: {list(result.keys())}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_download(url))

    aw = images[0].get("width")
    ah = images[0].get("height")
    if not (aw and ah):
        try:
            from PIL import Image
            with Image.open(out) as im:
                aw, ah = im.size
        except Exception:
            aw, ah = None, None

    used_seed = seed if seed is not None else result.get("seed")
    entry = {
        "model": model,
        "prompt": arguments["prompt"],
        "seed": used_seed,
        "seed_requested": seed,
        "requested": {"width": int(width), "height": int(height)},
        "actual": {"width": aw, "height": ah},
        "reference_images": [str(r) for r in (reference_images or [])],
        "output": out.name,
        "bytes": out.stat().st_size,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    genlog = _write_genlog(out, entry)
    return {"path": out, "bytes": out.stat().st_size, "width": aw, "height": ah,
            "seed": used_seed, "requested": {"width": int(width), "height": int(height)},
            "genlog": genlog, "model": model, "refs": ref_urls}


def generate_candidates(prompt: str, slug: str, *, width: int = 2560, height: int = 1440,
                        base_seed: int | None = None, target: int = 3, max_retries: int = 5,
                        reference_images: list | None = None,
                        out_dir: Path | None = None) -> dict:
    """톤 합격 후보 target 장 확보. 불합격 시 seed 변경 재생성(최대 max_retries 추가 시도).
    {passed:[{path,seed,metrics}], attempts:[...], target, secured} 반환."""
    out_dir = out_dir or (REPO / "tracks" / slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    if base_seed is None:
        base_seed = int(time.time()) % 1_000_000
    passed, attempts = [], []
    max_attempts = target + max_retries       # 이상적 target + 최대 max_retries 재시도
    i = 0
    while len(passed) < target and i < max_attempts:
        seed = int(base_seed) + i
        i += 1
        out = out_dir / f"bg_{slug}_{seed}.png"
        try:
            info = generate_bg(prompt, out, width, height, seed, reference_images)
        except Exception as e:                # noqa: BLE001
            attempts.append({"seed": seed, "ok": False, "error": repr(e)})
            print(f"  [attempt {i}] seed {seed}: 생성실패 {e!r}")
            continue
        tc = tone_check(out)
        rec = {"seed": seed, "path": str(out), "ok": tc["ok"],
               "metrics": tc["metrics"], "reasons": tc["reasons"]}
        attempts.append(rec)
        m = tc["metrics"]
        status = "PASS" if tc["ok"] else "FAIL(" + ", ".join(tc["reasons"]) + ")"
        print(f"  [attempt {i}] seed {seed}: 밝기{m['brightness']:.0f} 채도{m['saturation']:.0f} "
              f"R-B{m['warm_index']:+.0f} 회색{m['gray_frac']:.2f} → {status}")
        if tc["ok"]:
            passed.append(rec)
        else:
            out.unlink(missing_ok=True)       # 불합격 파일 정리
            out.with_name(out.name + ".genlog.json").unlink(missing_ok=True)
    return {"passed": passed, "attempts": attempts, "target": target,
            "secured": len(passed), "reached_cap": i >= max_attempts and len(passed) < target}


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────
def _parse_size(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="fal.ai 커버 배경 생성 (하우스 스타일 v2)")
    ap.add_argument("slug", nargs="?", help="곡 slug (tracks/<slug>/ 출력 경로 근거)")
    ap.add_argument("--scene", help="곡별 장면 한 줄(하우스 템플릿에 삽입)")
    ap.add_argument("--prompt", help="전체 프롬프트 직접 지정(템플릿 우회)")
    ap.add_argument("--seed", type=int, default=None, help="base seed(미지정 시 시각 기반)")
    ap.add_argument("--size", default="2560x1440", help="WxH (기본 2560x1440)")
    ap.add_argument("--out", help="단일 생성 출력 경로(--single 시)")
    ap.add_argument("--candidates", type=int, default=3, help="합격 후보 목표 장수(기본 3)")
    ap.add_argument("--max-retries", type=int, default=5, help="톤 불합격 시 추가 재생성 상한")
    ap.add_argument("--ref-dir", default=str(STYLE_REF_DIR), help="style_ref 폴더")
    ap.add_argument("--no-ref", action="store_true", help="멀티레퍼런스 비활성")
    ap.add_argument("--single", action="store_true", help="후보 루프 없이 1장만")
    args = ap.parse_args(argv)

    width, height = _parse_size(args.size)

    # 프롬프트 결정
    if args.prompt:
        prompt = args.prompt
    elif args.scene:
        prompt = build_house_prompt(args.scene)
    else:
        ap.error("--scene 또는 --prompt 중 하나는 필요합니다")

    # 레퍼런스
    refs = None
    if not args.no_ref:
        refs = _collect_style_refs(Path(args.ref_dir))
        if refs:
            print(f"[refs] {len(refs)}장 첨부: {[p.name for p in refs]}")
        else:
            print(f"[refs] style_ref 비어있음({args.ref_dir}) — 레퍼런스 없이 진행")

    t0 = time.monotonic()

    # 단일 생성
    if args.single or args.candidates <= 1:
        out = args.out or (REPO / "tracks" / (args.slug or "bg") / f"bg_{args.slug or 'out'}.png")
        info = generate_bg(prompt, out, width, height, args.seed, refs)
        dt = time.monotonic() - t0
        tc = tone_check(info["path"])
        print(f"[fal_bg] OK: {info['path']} ({info['bytes']}B, {info['width']}x{info['height']}, "
              f"seed={info['seed']}, model={info['model']}) in {dt:.1f}s")
        print(f"[tone] {'PASS' if tc['ok'] else 'FAIL: '+', '.join(tc['reasons'])} {tc['metrics']}")
        print(f"[fal_bg] genlog: {info['genlog']}")
        return 0

    # 후보 루프(tone_check + 자동 재생성)
    if not args.slug:
        ap.error("후보 모드는 slug 가 필요합니다(출력 경로).")
    res = generate_candidates(prompt, args.slug, width=width, height=height,
                              base_seed=args.seed, target=args.candidates,
                              max_retries=args.max_retries, reference_images=refs)
    dt = time.monotonic() - t0
    print(f"\n[fal_bg] 후보 {res['secured']}/{res['target']}장 확보 "
          f"(시도 {len(res['attempts'])}회) in {dt:.1f}s")
    for p in res["passed"]:
        print(f"  ✅ seed {p['seed']}: {p['path']}")
    if res["reached_cap"]:
        print(f"  ⚠️ 상한 도달 — 목표 미달({res['secured']}/{res['target']}). 임계 완화/scene 조정 검토.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
