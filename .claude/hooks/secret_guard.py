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

# (1) 시크릿 '파일명' — 접근 경로/명령에서 검사 (파일 내용에선 검사 안 함:
#     .gitignore/README 등이 이 이름을 합법적으로 언급해도 오탐 안 나게)
PATH_RE = re.compile(
    r"(client_secret[\w.\-]*\.json"
    r"|token\.json"
    r"|threads_token\.json"
    r"|\.env(?![\w])"
    r"|id_rsa\b|id_ed25519\b)",
    re.IGNORECASE,
)
# (2) 시크릿 '값 자료' — 경로/명령 + 파일 내용까지 검사 (레포 파일 기록 시도 차단).
#     fal 키 형식 = UUID:hex(32+)  ·  PEM 개인키 헤더. 환경변수 '이름'은 차단 안 함
#     (os.environ["FAL_KEY"] 같은 정상 코드/모델 id "fal-ai/..."는 통과).
VALUE_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{32,}"
    r"|-----BEGIN[ A-Z]*PRIVATE KEY-----"
    r"|EAA[0-9A-Za-z]{50,}"                    # Meta/FB Graph API access token 값
    r"|IGQ[\w\-]{20,}"                         # IG Basic Display 단기 토큰 값
    r"|IGAA[\w\-]{20,}"                        # IG API 장기 토큰 값
    r"|IG_APP_SECRET[\s\"':=]+[0-9a-f]{16,}"   # IG 앱 시크릿(변수명+실제값 결합; %참조%는 미차단)
    r")",     # 변수명 자체(IG_ACCESS_TOKEN)는 미차단 — %VAR% 참조 curl 작동 보장.
    re.IGNORECASE,
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input") or {}
    path_hay = " ".join(str(ti.get(k, "")) for k in ("file_path", "path", "command"))
    value_hay = path_hay + " " + " ".join(
        str(ti.get(k, "")) for k in ("content", "new_string", "old_string"))
    mp = PATH_RE.search(path_hay)
    mv = VALUE_RE.search(value_hay)
    if mp or mv:
        what = mp.group(0) if mp else "<credential value>"   # 값은 절대 에코하지 않음
        sys.stderr.write(
            f"[secret_guard] 차단: 크레덴셜/시크릿 - '{what}'.\n"
            f"  파일명(client_secret*.json·token.json·threads_token.json·.env·id_rsa) 또는\n"
            f"  키 값 자료(fal UUID:hex · PEM 개인키)의 접근·기록 금지.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
