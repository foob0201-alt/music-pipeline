#!/usr/bin/env python3
"""set_privacy.py — 업로드된 YouTube 영상 공개범위 변경 (videos.update).

- videos.update 는 youtube.force-ssl 스코프가 필요(업로드 전용 스코프로는 불가).
  기존 토큰의 스코프가 부족하면 재동의(OAuth 팝업 1회)한다.
- 크레덴셜 경로는 config youtube 설정에서 읽는다(소스에 파일명 하드코딩 안 함).
- 변경 후 tracks/<slug>/out/upload_manifest.json 의 해당 레코드 privacy 필드도 갱신.

사용: python scripts/set_privacy.py <video_id> <private|unlisted|public> [--track <slug>]
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))          # scripts/ 에서 실행해도 repo 루트 모듈 임포트 가능

from hades_util import get_logger, load_config, harden_secret

log = get_logger("set_privacy")
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
ACCOUNT_HINT = "reina2hj@gmail.com"


def _service(client_secret, token):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    tp = Path(token)
    granted = []                                 # 토큰 파일에 실제로 부여된 스코프
    if tp.exists():
        try:
            granted = json.loads(tp.read_text(encoding="utf-8")).get("scopes", [])
        except Exception:                        # noqa: BLE001
            granted = []
    has_scope = all(s in granted for s in SCOPES)

    creds = None
    if tp.exists() and has_scope:
        try:
            creds = Credentials.from_authorized_user_file(token, SCOPES)
        except Exception:                        # noqa: BLE001
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token and has_scope:
            creds.refresh(Request())
        else:
            log.info("videos.update 권한(youtube.force-ssl) 재동의 필요 — 브라우저에서 %s 로 허용하세요.",
                     ACCOUNT_HINT)
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        tp.write_text(creds.to_json(), encoding="utf-8")
        harden_secret(token)
    return build("youtube", "v3", credentials=creds)


def _update_manifest(slug, video_id, privacy):
    if not slug:
        log.warning("--track 미지정 — 매니페스트 갱신 생략")
        return
    mp = ROOT / "tracks" / slug / "out" / "upload_manifest.json"
    if not mp.exists():
        log.warning("매니페스트 없음: %s", mp)
        return
    data = json.loads(mp.read_text(encoding="utf-8"))
    changed = False
    for rec in data.get("uploads", []):
        if rec.get("video_id") == video_id:
            rec["privacy"] = privacy
            changed = True
    if changed:
        tmp = mp.parent / (mp.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        import os
        os.replace(tmp, mp)
        log.info("매니페스트 갱신: %s → privacy=%s", mp, privacy)
    else:
        log.warning("매니페스트에 video_id=%s 레코드 없음", video_id)


def main(argv):
    if len(argv) < 2:
        print("usage: python scripts/set_privacy.py <video_id> <private|unlisted|public> [--track <slug>]")
        return 1
    video_id, privacy = argv[0], argv[1]
    if privacy not in ("private", "unlisted", "public"):
        log.error("privacy 값 오류: %s", privacy)
        return 2
    slug = argv[argv.index("--track") + 1] if "--track" in argv else None

    track_cfg = str(ROOT / "tracks" / slug / "config.yaml") if slug else None
    cfg = load_config(str(ROOT / "config.yaml"), track_cfg)
    yt = cfg.get("youtube", {})

    svc = _service(yt.get("client_secret"), yt.get("token"))
    resp = svc.videos().update(part="status", body={
        "id": video_id,
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }).execute()
    new_priv = resp.get("status", {}).get("privacyStatus") or privacy
    log.info("공개범위 변경 완료: %s → %s", video_id, new_priv)
    _update_manifest(slug, video_id, new_priv)
    print(f"{video_id} -> {new_priv}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
