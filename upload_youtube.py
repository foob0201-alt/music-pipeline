"""
upload_youtube.py — YouTube Data API v3 버전별 업로드

- OAuth 데스크톱 클라이언트(client_secret.json) → token.json 캐시.
- 버전(ko/en/dual)별 업로드. 제목에 언어 라벨.
- 재시도/백오프 + 멱등 매니페스트(이미 올린 버전은 건너뜀). (P0)
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from hades_util import Context, Manifest, get_logger, harden_secret, retry

log = get_logger("youtube")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _service(client_secret: str, token: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    tp = Path(token)
    if tp.exists():
        creds = Credentials.from_authorized_user_file(token, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        tp.write_text(creds.to_json(), encoding="utf-8")
        harden_secret(token)
    return build("youtube", "v3", credentials=creds)


def _build_body(cfg: dict, title: str, ver: str) -> dict:
    yt = cfg.get("youtube", {})
    label = yt.get("ver_labels", {}).get(ver, ver)
    full_title = yt.get("title_template", "{title} ({ver_label})").format(
        title=title, ver_label=label)
    return {
        "snippet": {
            "title": full_title[:100],
            "description": yt.get("description", ""),
            "tags": yt.get("tags", []),
            "categoryId": str(yt.get("category_id", "10")),
        },
        "status": {
            "privacyStatus": yt.get("privacy", "unlisted"),
            "selfDeclaredMadeForKids": False,
        },
    }


def _upload_one(svc, body: dict, video: Path) -> str:
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(video), chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    req = svc.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            log.info("업로드 %d%%", int(status.progress() * 100))
    return f"https://youtu.be/{resp['id']}"


def run(ctx: Context) -> Context:
    yt = ctx.cfg.get("youtube", {})
    if not yt.get("enabled", False):
        log.info("youtube.enabled=false — 건너뜀")
        return ctx
    if not ctx.video_map:
        raise RuntimeError("video_map 없음 — video 단계 선행 필요")

    harden_secret(yt.get("client_secret", "client_secret.json"))
    mani = Manifest(ctx.out_dir / "manifest.json")
    svc = _service(yt.get("client_secret", "client_secret.json"),
                   yt.get("token", "token.json"))

    urls: Dict[str, str] = {}
    for ver, video in ctx.video_map.items():
        key = f"youtube:{ctx.track_dir.name}:{ver}"
        if mani.done(key):
            urls[ver] = mani.get(key)
            log.info("이미 업로드됨(매니페스트): %s → %s", ver, urls[ver])
            continue
        body = _build_body(ctx.cfg, ctx.title, ver)
        url = retry(lambda: _upload_one(svc, body, video),
                    what=f"youtube-upload[{ver}]")
        urls[ver] = url
        mani.mark(key, url)
        log.info("업로드 완료 %s → %s", ver, url)
    ctx.youtube_urls = urls
    return ctx
