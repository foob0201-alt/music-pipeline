#!/usr/bin/env python3
"""danger_guard.py — PreToolUse(Bash) 훅.

파괴적/위험 Bash 명령을 차단한다:
  - rm -rf ~  /  $HOME  /  /  (대량 삭제, --no-preserve-root 포함)
  - main/master 강제 푸시 (git push --force/-f/+refspec)
  - ANTHROPIC_BASE_URL 설정 (API 트래픽 우회)
  - 원격 스크립트 파이프 실행 (curl|wget … | sh)
- 해당  → exit 2 (차단)
- 그 외 → exit 0 (통과). 파싱 오류는 fail-open(0).

오직 exit 2 만 차단 신호다.
"""
import sys
import json
import re

# Windows cp949 파이프에서도 UTF-8 입출력 보장(한글·기호 안전)
try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    low = cmd.lower()
    reasons = []

    # rm -rf 홈/루트
    has_rm = re.search(r"\brm\b", low)
    rf = re.search(r"-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r|-rf|-fr", low)
    target = re.search(r"(\s~(\s|/|$)|\$home|\s/(\s|$|\*)|--no-preserve-root)", low)
    if has_rm and rf and target:
        reasons.append("rm -rf ~ / $HOME / / 류 대량 삭제")

    # git 강제 푸시 main/master
    if (re.search(r"git\s+push", low)
            and re.search(r"(--force\b|--force-with-lease\b|\s-f\b|\s\+)", low)
            and re.search(r"\b(main|master)\b", low)):
        reasons.append("main/master 강제 푸시")

    # ANTHROPIC_BASE_URL 변경(트래픽 우회)
    if "anthropic_base_url" in low:
        reasons.append("ANTHROPIC_BASE_URL 설정(API 트래픽 우회)")

    # 원격 스크립트 파이프 실행
    if re.search(r"(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba)?sh\b", low):
        reasons.append("원격 스크립트 파이프 실행(curl|sh)")

    if reasons:
        sys.stderr.write("[danger_guard] 차단: " + " · ".join(reasons) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
