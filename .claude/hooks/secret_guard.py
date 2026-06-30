#!/usr/bin/env python3
"""secret_guard.py — PreToolUse(Read|Edit|Write|Bash) 훅.

크레덴셜/시크릿 파일 접근을 차단한다:
  client_secret*.json · token.json · threads_token.json · .env(.*)
Read/Edit/Write 의 file_path 와 Bash 의 command 양쪽을 검사한다.
- 해당  → exit 2 (차단)
- 그 외 → exit 0 (통과). 파싱 오류는 fail-open(0).

오직 exit 2 만 차단 신호다. (HADES 보안 규약: 시크릿은 읽기·출력·편집 금지)
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

SECRET_RE = re.compile(
    r"(client_secret[\w.\-]*\.json"
    r"|token\.json"
    r"|threads_token\.json"
    r"|\.env(?![\w]))",
    re.IGNORECASE,
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input") or {}
    hay = " ".join(str(ti.get(k, "")) for k in ("file_path", "path", "command"))
    if not hay.strip():
        return 0
    m = SECRET_RE.search(hay)
    if m:
        sys.stderr.write(
            f"[secret_guard] 차단: 크레덴셜/시크릿 접근 금지 — '{m.group(0)}'.\n"
            f"  (client_secret*.json · token.json · threads_token.json · .env)\n"
            f"  HADES 보안 규약상 읽기·출력·편집 불가.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
