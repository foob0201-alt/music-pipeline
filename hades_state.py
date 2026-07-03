#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hades_state.py — 트랙별 상태 머신 (HADES 무인 루프 v1, 파트 1).

상태(트랙별, tracks/<slug>/state.json 에 기록):
  NEW → FINGERPRINTED → COVER_CANDIDATES → COVER_OK(게이트1)
      → ALIGNED → SUBTITLED → ENCODED → VERIFIED(게이트2 자동) → QUEUED
  (UPLOADED/POSTED 로의 자동 전이는 없음 — 발행은 upload_scheduler 사용자 트리거.
   HADES §3·§4.4·발행수동 정책. QUEUED 가 --auto 의 종착.)

원칙:
- 각 스테이지는 기존 모듈 호출. 산출물이 이미 있으면 건너뛴다(멱등·resume).
- COVER_OK 게이트에서 정지, .cover_ok 감지 시 자동 재개.
- 실패는 state.error 에 기록하고 그 트랙만 멈춤(배치 상위에서 다음 트랙으로).
- 판단 없음. 정해진 전이의 수행. (HADES §2.1)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from hades_util import (Context, load_config, get_logger, cover_gate_ok,
                        approve_cover, _sha256_file)

log = get_logger("state")

# 상태 순서(선형). 인덱스로 진행도 비교.
STATES = ["NEW", "FINGERPRINTED", "COVER_CANDIDATES", "COVER_OK",
          "ALIGNED", "SUBTITLED", "ENCODED", "VERIFIED", "QUEUED",
          "UPLOADED", "POSTED"]
# 특수(정지) 상태
AWAITING_LYRICS = "AWAITING_LYRICS"
NEEDS_REVIEW = "NEEDS_REVIEW"
HOLD_COVER = "HOLD_COVER"         # 무인 게이트1: scene_check 2연속 FAIL → 사람 개입 대기
AUTO_TERMINAL = "QUEUED"          # --auto 는 여기서 멈춘다(업로드는 수동)


# ─────────────────────────────────────────────────────────── state.json I/O
def state_path(slug: str) -> Path:
    return Path("tracks") / slug / "state.json"


def load_state(slug: str) -> dict:
    p = state_path(slug)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"slug": slug, "state": "NEW", "error": None, "history": []}


def save_state(slug: str, st: dict) -> None:
    p = state_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def set_state(st: dict, new: str, *, error: Optional[str] = None) -> None:
    st["state"] = new
    st["error"] = error
    st["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    st.setdefault("history", []).append({"state": new, "ts": st["updated"]})
    save_state(st["slug"], st)
    log.info("[%s] → %s%s", st["slug"], new, f" (error: {error})" if error else "")


def _probe_dur(path: Path) -> Optional[float]:
    try:
        o = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True).stdout.strip()
        return float(o)
    except Exception:  # noqa: BLE001
        return None


def _md5(path: Path) -> Optional[str]:
    try:
        import hashlib
        h = hashlib.md5()
        with path.open("rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()
    except Exception:  # noqa: BLE001
        return None


# ─────────────────────────────────────────────────────────── 검수(게이트2, 파트1 판정)
def verify_encode(ctx: Context, slug: str) -> dict:
    """ffprobe 9항목 + 지문 일치 검사. (신뢰도 임계는 파트4 sync_check 에서 추가.)
    {ok, items:[{name,value,pass}], reasons:[...]} 반환."""
    # 인스트루멘털은 자막 없는 단일본(_bgm), 보컬은 dual 을 검수 대상으로 삼는다.
    vidname = (f"{ctx.track_dir.name}_bgm.mp4"
               if ctx.cfg.get("mode") == "instrumental"
               else f"{ctx.track_dir.name}_dual.mp4")
    mp4 = ctx.out_dir / vidname
    items, reasons = [], []
    if not mp4.exists():
        return {"ok": False, "items": [], "reasons": ["mp4 없음"]}

    def probe(stream, keys):
        sel = ["-select_streams", stream] if stream else []
        out = subprocess.run(
            ["ffprobe", "-v", "error", *sel, "-show_entries", keys,
             "-of", "default=nw=1", str(mp4)], capture_output=True, text=True)
        return dict(l.split("=", 1) for l in out.stdout.strip().splitlines() if "=" in l)

    v = probe("v:0", "stream=codec_name,profile,width,height,pix_fmt,color_space,"
                     "color_transfer,color_primaries,color_range,r_frame_rate")
    a = probe("a:0", "stream=codec_name,sample_rate,channels,bit_rate")
    fmt = probe(None, "format=duration,size,bit_rate")

    def chk(name, cond, val):
        items.append({"name": name, "value": str(val), "pass": bool(cond)})
        if not cond:
            reasons.append(f"{name}={val}")

    encfps = str(ctx.cfg.get("video", {}).get("fps", 30))
    chk("codec", v.get("codec_name") == "h264", v.get("codec_name"))
    chk("profile", v.get("profile") == "High", v.get("profile"))
    chk("resolution", (v.get("width"), v.get("height")) == ("2560", "1440"),
        f"{v.get('width')}x{v.get('height')}")
    chk("pix_fmt", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"))
    chk("color_bt709",
        v.get("color_primaries") == "bt709" and v.get("color_space") == "bt709"
        and v.get("color_transfer") == "bt709" and v.get("color_range") == "tv",
        f"{v.get('color_primaries')}/{v.get('color_range')}")
    chk("fps", v.get("r_frame_rate") == f"{encfps}/1", v.get("r_frame_rate"))
    dur = float(fmt.get("duration", 0) or 0)
    adur = _probe_dur(ctx.audio) or 0
    chk("duration", abs(dur - adur) < 0.5, f"{dur:.2f}~{adur:.2f}")
    chk("audio_aac", a.get("codec_name") == "aac" and a.get("sample_rate") == "48000",
        f"{a.get('codec_name')}/{a.get('sample_rate')}")
    # faststart: moov 가 mdat 앞
    head = mp4.open("rb").read(400000)
    moov, mdat = head.find(b"moov"), head.find(b"mdat")
    chk("faststart", 0 < moov < mdat if mdat > 0 else moov > 0, f"moov@{moov}/mdat@{mdat}")

    return {"ok": not reasons, "items": items, "reasons": reasons}


# ─────────────────────────────────────────────────────────── 무인 게이트1 (scene_check 한 세트)
def _composite_integrity(cover: Path) -> tuple[bool, str]:
    """합성 무결성 — cover.jpg 존재·해상도·포맷 검사."""
    if not cover.exists():
        return False, "cover.jpg 없음"
    try:
        from PIL import Image
        with Image.open(cover) as im:
            if im.size != (2560, 1440):
                return False, f"해상도 {im.size} != 2560x1440"
            if (im.format or "").upper() not in ("JPEG", "JPG"):
                return False, f"포맷 {im.format} != JPEG"
    except Exception as e:  # noqa: BLE001
        return False, f"이미지 열기 실패: {e!r}"
    return True, "ok"


def _notify_hold(slug: str, msg: str) -> None:
    """HOLD 알림 — 실제 폰 푸시는 하네스/원격 트리거(별도). 여기선 로그 + 파일 기록으로 남긴다."""
    log.warning("[%s] [HOLD 알림] %s", slug, msg)
    try:
        nf = Path("tracks") / slug / "out" / "HOLD_NOTIFY.txt"
        nf.parent.mkdir(parents=True, exist_ok=True)
        with nf.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}  {msg}\n")
    except Exception:  # noqa: BLE001
        pass


def auto_gate1(ctx: Context, slug: str, cfg: dict) -> tuple[str, str]:
    """무인 게이트1: 후보(bg_*.png)에 tone_check + scene_check + 합성 무결성 →
    합격 첫 후보를 cover_render 로 합성하고 .cover_ok 자동 서명.
    반환 (결과, 상세): 결과 ∈ {'approved','hold','wait'}.  (판단 기준은 코드 소유 — HADES §2.1)"""
    if not cfg.get("cover_gate_auto", True):
        return "wait", "cover_gate_auto=false (수동 게이트 유지)"

    hades_dir = str((Path(__file__).resolve().parent / "hades"))
    if hades_dir not in sys.path:
        sys.path.insert(0, hades_dir)
    import fal_bg
    import scene_check

    cover_cfg = cfg.get("cover", {}) or {}
    anchor = cover_cfg.get("anchor")
    scene = cover_cfg.get("scene")

    cands = sorted(ctx.track_dir.glob("bg_*.png"))
    if not cands:
        return "wait", "후보(bg_*.png) 없음 — 생성 대기"

    consec_fail, scene_ran, reasons = 0, 0, []
    for cand in cands:
        tc = fal_bg.tone_check(cand)
        if not tc["ok"]:
            reasons.append(f"{cand.name} tone FAIL({','.join(tc['reasons'])})")
            continue
        sc = scene_check.run_scene_check(cand, slug=slug, anchor=anchor, scene=scene)
        if sc.get("error"):
            # 검사기 인프라 오류(타임아웃/CLI 등)는 FAIL 로 세지 않고 대기(재시도).
            return "wait", f"scene_check 오류: {sc['error']}"
        scene_ran += 1
        if not sc["ok"]:
            consec_fail += 1
            reasons.append(f"{cand.name} scene FAIL {sc.get('verdict')}")
            if consec_fail >= 2:
                _notify_hold(slug, f"scene_check 2연속 FAIL: {reasons[-2:]}")
                return "hold", "; ".join(reasons)
            continue
        # PASS → 합성 + 무결성 + 자동 서명
        consec_fail = 0
        rc = subprocess.run([sys.executable, "cover_render.py", slug, "--bg", str(cand)],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            return "wait", f"cover_render 실패({cand.name}): {rc.stderr[:200]}"
        ok, why = _composite_integrity(ctx.cover)
        if not ok:
            return "wait", f"합성 무결성 실패: {why}"
        approve_cover(slug)
        return "approved", f"{cand.name} PASS → cover.jpg 합성·자동 서명"

    # 후보를 다 돌았는데 합격 없음: scene 검사가 있었으면 사람 개입(재생성) 필요 → HOLD
    if scene_ran:
        _notify_hold(slug, f"후보 전원 scene_check 미합격 — 재생성 필요: {reasons}")
        return "hold", "; ".join(reasons)
    return "wait", "; ".join(reasons) or "합격 후보 없음"


# ─────────────────────────────────────────────────────────── 스테이지 핸들러
def _run_align_mms(slug: str) -> None:
    subprocess.run([sys.executable, "scripts/align_mms.py", slug], check=True)


def advance(slug: str, *, cfg: dict) -> dict:
    """현재 state 에서 가능한 만큼 전진(멱등). 게이트/종착/실패에서 멈춘다.
    반환: 갱신된 state dict."""
    st = load_state(slug)
    ctx = Context.from_cfg(cfg)
    name = ctx.track_dir.name

    # NEEDS_REVIEW/AWAITING_LYRICS 는 조건 해소 시에만 진행
    guard = st.get("state")

    def idx(s): return STATES.index(s) if s in STATES else -1

    for _ in range(len(STATES) + 2):        # 최대 전이 횟수 상한(무한루프 방지)
        cur = st["state"]
        try:
            if cur in ("QUEUED", "UPLOADED", "POSTED"):
                return st                                   # --auto 종착(수동 업로드 대기)

            if cur == "NEW":
                if not ctx.audio.exists():
                    set_state(st, "NEW", error="audio.mp3 없음"); return st
                st["fingerprint"] = {"md5": _md5(ctx.audio), "duration": _probe_dur(ctx.audio)}
                set_state(st, "FINGERPRINTED")

            elif cur == "FINGERPRINTED":
                set_state(st, "COVER_CANDIDATES")           # 커버 생성은 파트3/5 에서 채움

            elif cur == "COVER_CANDIDATES":
                if cover_gate_ok(slug):
                    set_state(st, "COVER_OK")               # 이미 승인(수동/이전 자동) — 하위호환
                    continue
                # 무인 게이트1: tone_check + scene_check + 합성 무결성 → 자동 .cover_ok
                res, detail = auto_gate1(ctx, slug, cfg)
                st["gate1"] = {"result": res, "detail": detail, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
                if res == "approved":
                    ctx = Context.from_cfg(cfg)             # cover.jpg 갱신 반영
                    set_state(st, "COVER_OK", error=None)
                    continue
                elif res == "hold":
                    set_state(st, HOLD_COVER, error="게이트1 무인검증 실패: " + detail)
                    return st                               # 사람 개입 대기
                else:                                       # wait
                    log.info("[%s] 게이트1 대기 — %s. 정지.", slug, detail)
                    return st

            elif cur == "COVER_OK":
                # 인스트루멘털: 가사·정렬·자막 전부 건너뛰고 커버+오디오만 인코딩 → ENCODED 직행
                if ctx.cfg.get("mode") == "instrumental":
                    import make_video
                    if not (ctx.out_dir / f"{name}_bgm.mp4").exists():
                        make_video.run(ctx)
                    set_state(st, "ENCODED")
                    continue
                if not (ctx.lyrics_ko.exists() and (not ctx.lyrics_en or ctx.lyrics_en.exists())):
                    set_state(st, AWAITING_LYRICS, error="lyrics 없음"); return st
                if not (ctx.out_dir / "align.json").exists():
                    _run_align_mms(slug)
                if not (ctx.out_dir / "align.json").exists():
                    set_state(st, "COVER_OK", error="align.json 생성 실패"); return st
                set_state(st, "ALIGNED")

            elif cur == "ALIGNED":
                import align
                if not any((ctx.out_dir / f"{name}_{m}.ass").exists()
                           for m in cfg.get("subtitle", {}).get("modes", ["dual"])):
                    align.run(ctx)
                set_state(st, "SUBTITLED")

            elif cur == "SUBTITLED":
                import align, make_video
                mp4 = ctx.out_dir / f"{name}_dual.mp4"
                if not mp4.exists():
                    align.run(ctx)                          # ass_map 채우기(ctx 재생성됨)
                    make_video.run(ctx)
                set_state(st, "ENCODED")

            elif cur == "ENCODED":
                res = verify_encode(ctx, slug)
                st["verify"] = res
                if res["ok"]:
                    set_state(st, "VERIFIED")
                else:
                    set_state(st, NEEDS_REVIEW, error="검수 미달: " + ", ".join(res["reasons"]))
                    return st                               # 게이트2 미달 정지

            elif cur == "VERIFIED":
                # 발행 보류(publish_hold): QUEUED 미투입, VERIFIED 에서 정지하고 사유 기록.
                # (예: BGM 모션 레이어 표준 확정 후 재렌더 발행 예정)
                if cfg.get("publish_hold"):
                    st["hold_reason"] = cfg.get("hold_reason", "publish hold")
                    save_state(st["slug"], st)
                    log.info("[%s] VERIFIED — 발행 보류(hold): %s. QUEUED 미투입.",
                             slug, st["hold_reason"])
                    return st
                set_state(st, "QUEUED")                     # 업로드 대기(수동 트리거)
                return st

            elif cur == HOLD_COVER:
                # 사람이 개입해 커버를 승인(.cover_ok)했으면 복귀, 아니면 정지.
                if cover_gate_ok(slug):
                    set_state(st, "COVER_OK"); continue
                log.info("[%s] HOLD_COVER — 사람 개입 대기(게이트1 무인검증 실패). 정지.", slug)
                return st

            elif cur in (AWAITING_LYRICS, NEEDS_REVIEW):
                # 조건 재확인 후 이전 진행 상태로 복귀 시도
                if cur == AWAITING_LYRICS and ctx.lyrics_ko.exists():
                    set_state(st, "COVER_OK")
                elif cur == NEEDS_REVIEW:
                    log.info("[%s] NEEDS_REVIEW — 수동 검수 필요. 정지.", slug); return st
                else:
                    return st
            else:
                log.warning("[%s] 알 수 없는 상태: %s", slug, cur); return st
        except Exception as e:  # noqa: BLE001
            set_state(st, cur, error=repr(e))
            log.error("[%s] 스테이지 실패(%s): %r", slug, cur, e)
            return st
    return st


def run_auto(slug: str, cfg: dict) -> dict:
    """단일 트랙 --auto: 현재 상태에서 종착/게이트/실패까지 전진."""
    log.info("[%s] --auto 시작 (현재: %s)", slug, load_state(slug).get("state"))
    st = advance(slug, cfg=cfg)
    log.info("[%s] --auto 종료: %s%s", slug, st["state"],
             f" (error: {st['error']})" if st.get("error") else "")
    return st


# ─────────────────────────────────────────────────────────── 상태 테이블
def status_table() -> str:
    rows = []
    for sp in sorted(Path("tracks").glob("*/state.json")):
        slug = sp.parent.name
        st = load_state(slug)
        rows.append((slug, st.get("state", "?"), st.get("updated", "-"),
                     (st.get("error") or "")[:40]))
    if not rows:
        return "(state.json 있는 트랙 없음 — 아직 --auto 미실행)"
    w = max((len(r[0]) for r in rows), default=4)
    out = [f"{'slug':<{w}}  {'state':<16}  {'updated':<19}  error",
           "-" * (w + 60)]
    for slug, state, upd, err in rows:
        out.append(f"{slug:<{w}}  {state:<16}  {upd:<19}  {err}")
    return "\n".join(out)
