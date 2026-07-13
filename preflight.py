"""
preflight.py — 단계 실행 전 선행조건 검증 (P0)

추측으로 진행하다 중간에 깨지지 않도록, 실행 전에 멈춰서 확인한다. (HADES §2.2)
- 입력 파일 존재
- ffmpeg / 폰트 가용
- KO / EN 줄수 1:1 (정의 §2)
- 음원 정체성: md5 + duration 이 FINGERPRINTS.md 등재값과 일치 (donghae 오음원 재발 방지)

두 가지 진입점:
  · check(ctx, ...)  — 파이프라인 내부(Context 기반) 선행검증.
  · CLI (--track/--all [--register])  — 착수 전 배치 무결성 게이트 + 지문 등록.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from hades_util import Context, read_lyric_lines, get_logger

log = get_logger("preflight")

ROOT = Path(__file__).resolve().parent
FP_FILE = ROOT / "FINGERPRINTS.md"
DUR_TOL = 0.5
SECTION_PREFIXES = ("[", "(")


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


# ================================================================== 지문(정체성) 게이트 + CLI
def _md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _probe_dur(p: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def _sung_lines(p: Path) -> list[str]:
    out = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith(SECTION_PREFIXES) and s.endswith(("]", ")")):
            continue
        out.append(s)
    return out


def parse_fingerprints() -> dict[str, dict]:
    """FINGERPRINTS.md 의 모든 표에서 slug -> {md5, dur} 추출."""
    reg: dict[str, dict] = {}
    if not FP_FILE.exists():
        return reg
    for line in FP_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        slug = cells[0]
        if slug in ("slug", "") or set(slug) <= set("-: "):
            continue
        m = re.search(r"`([0-9a-fA-F]{32})`", line)
        d = re.search(r"\b(\d{2,4}\.\d{1,2})\b", line)
        if m:
            reg[slug] = {"md5": m.group(1).lower(),
                         "dur": float(d.group(1)) if d else None}
    return reg


def register_fp(slug: str, md5: str, dur: float) -> None:
    """FINGERPRINTS.md 끝에 표 행으로 추가(멱등: 이미 있으면 스킵)."""
    txt = FP_FILE.read_text(encoding="utf-8")
    if re.search(rf"^\|\s*{re.escape(slug)}\s*\|", txt, re.M):
        return
    row = f"| {slug} | `{md5}` | {dur:.2f} | preflight 자동등록 |\n"
    FP_FILE.write_text(txt.rstrip() + "\n" + row, encoding="utf-8")


def check_track(slug: str, reg: dict, *, register: bool) -> dict:
    """단독(배치) 무결성 검사 — Context 없이 파일만으로."""
    td = ROOT / "tracks" / slug
    res = {"slug": slug, "checks": [], "ok": True}

    def chk(name, ok, detail=""):
        res["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            res["ok"] = False

    cfg_txt = (td / "config.yaml").read_text(encoding="utf-8") if (td / "config.yaml").exists() else ""
    instrumental = bool(re.search(r"mode:\s*instrumental", cfg_txt))
    fontm = re.search(r"font:\s*['\"]?([^'\"\n]+)", cfg_txt)
    font = fontm.group(1).strip() if fontm else "Malgun Gothic"

    # 1) 오디오 정체성 (md5 + duration ↔ FINGERPRINTS)
    auds = sorted(td.glob("*.mp3"))
    if not auds:
        chk("audio_exists", False, "mp3 없음")
        return res
    aud = auds[0]
    md5 = _md5_file(aud)
    dur = _probe_dur(aud)
    fp = reg.get(slug)
    if fp is None:
        if register:
            register_fp(slug, md5, dur)
            chk("fingerprint", True, f"신규 등록 md5={md5[:12]} dur={dur:.2f}")
        else:
            chk("fingerprint", False,
                f"FINGERPRINTS 미등재 (md5={md5[:12]} dur={dur:.2f}) — --register 필요")
    else:
        md5_ok = fp["md5"] == md5
        dur_ok = fp["dur"] is None or abs(fp["dur"] - dur) <= DUR_TOL
        chk("fingerprint", md5_ok and dur_ok,
            f"md5 {'=' if md5_ok else '≠'} 대장 / dur {dur:.2f} vs {fp['dur']}")

    # 2) 가사 1:1 (instrumental 스킵)
    nk = 0
    if not instrumental:
        lk, le = td / "lyrics_ko.txt", td / "lyrics_en.txt"
        if not lk.exists() or not le.exists():
            chk("lyrics_1to1", False, f"가사 결손 ko={lk.exists()} en={le.exists()}")
            nk = len(_sung_lines(lk)) if lk.exists() else 0
        else:
            nk, ne = len(_sung_lines(lk)), len(_sung_lines(le))
            chk("lyrics_1to1", nk == ne, f"KO {nk} / EN {ne}")
        # 3) align.json 정합
        aj = td / "out" / "align.json"
        if aj.exists():
            try:
                ajn = len(json.loads(aj.read_text(encoding="utf-8")).get("lines", []))
            except Exception:  # noqa: BLE001
                ajn = -1
            chk("align_match", ajn == nk, f"align {ajn} vs KO {nk}")

    # 4) 폰트(soft, Windows)
    if sys.platform == "win32":
        known = {"malgun gothic": "malgun.ttf", "malgun": "malgun.ttf"}
        fname = known.get(font.lower())
        if fname:
            chk("font", (Path("C:/Windows/Fonts") / fname).exists(), f"{font} → {fname}")
        else:
            res["checks"].append({"name": "font", "ok": True,
                                  "detail": f"{font} (미검증 폰트, soft-pass)"})
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="파이프라인 착수 전 무결성 게이트")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--track", help="트랙 slug")
    g.add_argument("--all", action="store_true", help="tracks/* 전체")
    ap.add_argument("--register", action="store_true", help="미등재 지문 FINGERPRINTS에 추가")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    a = ap.parse_args(argv)

    reg = parse_fingerprints()
    slugs = ([a.track] if a.track else
             sorted(p.name for p in (ROOT / "tracks").glob("*")
                    if p.is_dir() and not p.name.startswith("_")))
    results = [check_track(s, reg, register=a.register) for s in slugs]

    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{'PASS' if r['ok'] else 'FAIL'}] {r['slug']}")
            for c in r["checks"]:
                print(f"    {'OK' if c['ok'] else 'X!'}  {c['name']:14s} {c['detail']}")
    n_fail = sum(1 for r in results if not r["ok"])
    print(f"\n총 {len(results)}곡 · PASS {len(results) - n_fail} · FAIL {n_fail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
