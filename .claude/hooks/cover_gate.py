#!/usr/bin/env python3
"""cover_gate.py — PreToolUse(Bash) 훅.

ffmpeg 로 .mp4 를 만드는 Bash 명령을 가로채, 대상 곡(slug)의 cover.jpg sha256 이
tracks/<slug>/out/.cover_ok 에 기록된 '승인 해시'와 일치하는지 확인한다.
- 불일치           → exit 2 (차단)
- cover 있는데 .cover_ok 없음(미승인) → exit 2 (차단; 승인되지 않은 커버)
- cover.jpg 자체 없음 / 비대상 명령   → exit 0 (통과)

오직 exit 2 만 차단 신호다. 파싱 오류 등 예외는 fail-open(0)으로 세션 브릭을 막는다.
"""
import sys
import json
import re
import hashlib
from pathlib import Path

# Windows cp949 파이프에서도 UTF-8 입출력 보장(한글·기호 안전)
try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    low = cmd.lower()
    # ffmpeg 로 mp4 를 만드는 명령만 대상
    if "ffmpeg" not in low or ".mp4" not in low:
        return 0
    # slug 추출: tracks/<slug>/ ...
    m = re.search(r"tracks[\\/]+([^\\/]+)[\\/]", cmd)
    if not m:
        return 0
    slug = m.group(1)
    root = Path.cwd()
    cover = root / "tracks" / slug / "cover.jpg"
    okfile = root / "tracks" / slug / "out" / ".cover_ok"
    if not cover.exists():
        return 0  # 해당 곡 커버 자체가 없음 → 대상 아님(통과)
    cur = _sha256(cover)
    if not okfile.exists():
        sys.stderr.write(
            f"[cover_gate] 차단: '{slug}' 승인 기록(.cover_ok) 없음 — 미승인 커버는 인코딩 불가.\n"
            f"  현재 sha256={cur}\n"
            f"  → 커버 확인 후 .cover_ok 기록(승인) 필요.\n")
        return 2
    toks = okfile.read_text(encoding="utf-8").split()
    rec = toks[0].strip() if toks else ""
    if cur != rec:
        sys.stderr.write(
            f"[cover_gate] 차단: '{slug}' cover.jpg 가 승인본과 다릅니다.\n"
            f"  현재   sha256={cur}\n"
            f"  승인본 sha256={rec}\n"
            f"  → 커버 재확인 후 .cover_ok 갱신(승인) 전에는 인코딩할 수 없습니다.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
