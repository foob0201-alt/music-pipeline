#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hades/scene_check.py — GATE1 무인화용 헤드리스 비전 검사 (fal_bg v3 한 세트).

`claude -p --allowedTools Read` 로 후보 커버 배경을 비전 검사해 JSON 판정을 받는다.
판정 3항목 전부 true → PASS:
  - anchor_present         : SCENE 앵커(가사 유래 장면)가 이미지에 실제로 담겼는가
  - no_lyric_contradiction : 이미지가 가사와 모순되지 않는가 (가사 없으면 자동 true)
  - no_face_no_text        : 사람 얼굴·글자/워터마크가 없는가 (제목·Reina는 코드가 나중에 합성)

입력: 후보 이미지 + SCENE 앵커(가사 줄번호 근거) + lyrics_ko.txt(있으면).
앵커·scene 은 인자로 받거나 이미지의 <img>.genlog.json 에서 자동 해석.

판단(합격 기준)은 PM/코드가 소유. 이 모듈은 '검증 신호'만 만든다. (HADES §2.1)
보안: FAL 키 등 시크릿을 다루지 않는다. claude CLI 만 호출.

CLI:
  python hades/scene_check.py <image.png> [--slug <slug>] [--anchor L12,L14]
      [--model claude-sonnet-5] [--timeout 180]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
# 게이트 검사 기본 모델 — 비전/JSON 신뢰 대비 비용 균형(세션 opus 상속 금지, 건당 과금 방어).
DEFAULT_MODEL = os.environ.get("SCENE_CHECK_MODEL", "claude-sonnet-5")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


# ─────────────────────────────────────────────────────────── 입력 해석
def _claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"


def _genlog(image_path: Path) -> dict:
    p = image_path.with_name(image_path.name + ".genlog.json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def _parse_anchor(anchor: str) -> list[int]:
    """'L12,L14' 또는 'L12-L14' 또는 '12,14' → [12,14] (1-indexed 줄번호)."""
    if not anchor:
        return []
    nums: list[int] = []
    for tok in re.split(r"[,\s]+", anchor.strip()):
        tok = tok.strip().lstrip("Ll")
        if not tok:
            continue
        m = re.match(r"^(\d+)\s*[-~]\s*(\d+)$", tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            nums.extend(range(min(a, b), max(a, b) + 1))
        elif tok.isdigit():
            nums.append(int(tok))
    # 중복 제거·정렬
    return sorted(dict.fromkeys(nums))


def _anchored_lines(lyrics_text: str, anchor_nums: list[int]) -> str:
    if not lyrics_text or not anchor_nums:
        return ""
    lines = lyrics_text.splitlines()
    out = []
    for n in anchor_nums:
        if 1 <= n <= len(lines):
            out.append(f"L{n}: {lines[n - 1].strip()}")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────── 프롬프트
def build_prompt(image_path: Path, *, lyrics_text: str, anchored: str,
                 scene: Optional[str]) -> str:
    rel = image_path.as_posix()
    parts = [
        "You are a strict cover-art GATE verifier for a music channel. "
        f"Read the image file at: {rel}",
        "Judge ONLY from what is visually in the image. Do not assume.",
    ]
    if anchored:
        parts.append("The intended scene is anchored to these lyric lines "
                     "(the image should visually depict this):\n" + anchored)
    elif scene:
        parts.append("The intended scene (no lyrics — instrumental) is:\n" + scene)
    if lyrics_text:
        parts.append("Full lyrics (for contradiction check — season, time of day, place):\n"
                     + lyrics_text.strip())
    else:
        parts.append("No lyrics provided → set no_lyric_contradiction to true by default.")
    parts.append(
        "Return ONLY a compact JSON object, no prose, with EXACTLY these keys:\n"
        '{"anchor_present": bool, "no_lyric_contradiction": bool, '
        '"no_face_no_text": bool, "notes": "<=15 words"}\n'
        "- anchor_present: the image visually depicts the anchored/intended scene "
        "(place, key objects, time-of-day). If no anchor/scene given, judge general scene sanity → true.\n"
        "- no_lyric_contradiction: nothing in the image contradicts the lyrics' setting/season/time. "
        "No lyrics → true.\n"
        "- no_face_no_text: there are NO human faces AND NO letters/words/numbers/watermark/logo anywhere. "
        "(Title and signature are added later by code — they must NOT already be present.)"
    )
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────── 파싱
def _extract_json(text: str) -> dict:
    """모델 응답(펜스 가능)에서 첫 JSON 오브젝트 추출."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        return json.loads(t[i:j + 1])
    raise ValueError(f"JSON 추출 실패: {text[:200]!r}")


# ─────────────────────────────────────────────────────────── 실행
def run_scene_check(image_path: str | Path, *, slug: Optional[str] = None,
                    lyrics_text: Optional[str] = None, anchor: Optional[str] = None,
                    scene: Optional[str] = None, model: str = DEFAULT_MODEL,
                    timeout: int = 180) -> dict:
    """헤드리스 비전 검사 1회. {ok, verdict, cost_usd, raw, error} 반환.
    ok = 3항목(anchor_present·no_lyric_contradiction·no_face_no_text) 전부 true."""
    image_path = Path(image_path)
    if not image_path.exists():
        return {"ok": False, "verdict": {}, "error": f"이미지 없음: {image_path}"}

    gl = _genlog(image_path)
    if anchor is None:
        anchor = gl.get("scene_anchor")
    if scene is None:
        scene = gl.get("scene")            # genlog 에 scene 키가 있으면 사용
    if lyrics_text is None and slug:
        lp = REPO / "tracks" / slug / "lyrics_ko.txt"
        if lp.exists():
            lyrics_text = lp.read_text(encoding="utf-8")
    lyrics_text = lyrics_text or ""
    anchored = _anchored_lines(lyrics_text, _parse_anchor(anchor or ""))

    prompt = build_prompt(image_path, lyrics_text=lyrics_text, anchored=anchored, scene=scene)

    cmd = [_claude_bin(), "-p", prompt, "--allowedTools", "Read",
           "--output-format", "json", "--model", model]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=str(REPO))
    except subprocess.TimeoutExpired:
        return {"ok": False, "verdict": {}, "error": f"claude -p 타임아웃({timeout}s)"}
    if proc.returncode != 0:
        return {"ok": False, "verdict": {},
                "error": f"claude -p 실패(rc={proc.returncode}): {proc.stderr[:300]}"}

    try:
        env = json.loads(proc.stdout)
        result_text = env.get("result", "") if isinstance(env, dict) else str(env)
        cost = env.get("total_cost_usd") if isinstance(env, dict) else None
        verdict = _extract_json(result_text)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "verdict": {}, "error": f"응답 파싱 실패: {e!r}",
                "raw": proc.stdout[:500]}

    keys = ("anchor_present", "no_lyric_contradiction", "no_face_no_text")
    ok = all(bool(verdict.get(k)) for k in keys)
    return {"ok": ok, "verdict": verdict, "cost_usd": cost, "raw": result_text}


# ─────────────────────────────────────────────────────────── CLI
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="GATE1 무인 비전 검사(scene_check)")
    ap.add_argument("image", help="후보 이미지 경로(png/jpg)")
    ap.add_argument("--slug", help="lyrics_ko.txt 해석용 곡 slug")
    ap.add_argument("--anchor", help="SCENE 앵커 가사 줄번호(예: L12,L14). 미지정 시 genlog")
    ap.add_argument("--scene", help="장면 텍스트(가사 없는 인스트루멘털용)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"검사 모델(기본 {DEFAULT_MODEL})")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args(argv)

    res = run_scene_check(args.image, slug=args.slug, anchor=args.anchor, scene=args.scene,
                          model=args.model, timeout=args.timeout)
    v = res.get("verdict", {})
    status = "PASS" if res["ok"] else "FAIL"
    print(f"[scene_check] {status}  {args.image}")
    print(f"  verdict: {json.dumps(v, ensure_ascii=False)}")
    if res.get("cost_usd") is not None:
        print(f"  cost: ${res['cost_usd']:.4f}")
    if res.get("error"):
        print(f"  error: {res['error']}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
