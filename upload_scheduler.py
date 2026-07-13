#!/usr/bin/env python3
"""
upload_scheduler.py — 최소 기능 YouTube 수동 업로드 스케줄러 (곡 단위)

기능(최소):
 1) YouTube Data API v3 OAuth — 계정 reina2hj@gmail.com.
    · OAuth 클라이언트 시크릿 경로는 config.yaml 의 youtube.client_secret 에서 읽는다.
    · 없으면 Google Cloud Console 에서 만들어야 함을 안내하고 중단.
 2) tracks/<slug>/out/upload_manifest.json 에 업로드 이력(track_id, video_id, uploaded_at) 기록.
 3) 일일 캡: 오늘(로컬 날짜) 업로드가 전체 트랙 통틀어 1건 이상이면 중단하고 이유 출력.
 4) tracks/<slug>/out/youtube_description.txt 파싱 → 제목(1행)·설명(태그 섹션 전까지)·태그(쉼표 목록).
 5) videos.insert 호출 → (video_id, url) 콘솔 출력 + manifest 기록.

실행:
    python upload_scheduler.py --track geureoke              # 실제 업로드(대화형 OAuth)
    python upload_scheduler.py --track geureoke --dry-run    # 네트워크 없이 파싱·캡·대상만 확인
    python upload_scheduler.py --track geureoke --privacy private
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from hades_util import get_logger, load_config

log = get_logger("scheduler")

ACCOUNT_HINT = "reina2hj@gmail.com"
DAILY_CAP = 1
ROOT = Path(__file__).resolve().parent


def _is_sep(s: str) -> bool:
    """구분선(═ 로만 이루어진 줄) 여부."""
    return s != "" and set(s) <= set("═")


def parse_description(path: Path):
    """youtube_description.txt → (title, description, tags[]).
    1행=제목, 3행부터=설명 본문(해시태그 포함), '태그 필드용' 마커 뒤 쉼표목록=태그."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    title = lines[0].strip()
    mi = next((i for i, l in enumerate(lines) if "태그 필드용" in l), None)
    if mi is None:
        body, tags = lines[1:], []
    else:
        end = mi
        while end > 0 and (lines[end - 1].strip() == "" or _is_sep(lines[end - 1].strip())):
            end -= 1                                   # 태그 블록의 구분선·빈줄을 설명에서 제외
        body = lines[1:end]
        tags = []
        for l in lines[mi + 1:]:
            s = l.strip()
            if s == "" or _is_sep(s):
                continue
            tags = [t.strip() for t in s.split(",") if t.strip()]
            break
    description = "\n".join(body).strip("\n")
    return title, description, tags


def today_upload_count():
    """전체 트랙의 upload_manifest.json 스캔 → 오늘(로컬) 업로드 건수·레코드."""
    today = datetime.now().date().isoformat()
    hits = []
    for mani in ROOT.glob("tracks/*/out/upload_manifest.json"):
        try:
            data = json.loads(mani.read_text(encoding="utf-8"))
        except Exception:                              # noqa: BLE001 — 깨진 매니페스트는 건너뜀
            continue
        for rec in data.get("uploads", []):
            if str(rec.get("uploaded_at", "")).startswith(today):
                hits.append(rec)
    return len(hits), hits


def record_manifest(mani_path: Path, rec: dict) -> None:
    """upload_manifest.json 에 업로드 레코드 원자적 추가."""
    data = {"uploads": []}
    if mani_path.exists():
        try:
            data = json.loads(mani_path.read_text(encoding="utf-8"))
        except Exception:                              # noqa: BLE001
            data = {"uploads": []}
    data.setdefault("uploads", []).append(rec)
    mani_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = mani_path.parent / (mani_path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, mani_path)


def insert_video(svc, title, description, tags, category_id, privacy, video: Path,
                 *, localizations: dict | None = None) -> dict:
    """videos.insert(resumable) → 응답 dict(id 포함) 반환.
    글로벌 메타 표준: defaultLanguage/defaultAudioLanguage="ko" 항상 설정.
    localizations={"en":{"title","description"}} 지정 시 함께 등록(part 확장)."""
    from googleapiclient.http import MediaFileUpload
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": str(category_id),
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    part = "snippet,status"
    if localizations:
        body["localizations"] = localizations
        part = "snippet,status,localizations"
    media = MediaFileUpload(str(video), chunksize=-1, resumable=True, mimetype="video/mp4")
    req = svc.videos().insert(part=part, body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            log.info("업로드 %d%%", int(status.progress() * 100))
    return resp


def _oauth_missing_guide(cs) -> None:
    log.error("OAuth 클라이언트 시크릿이 없습니다: %s", cs or "(config youtube.client_secret 미설정)")
    log.error("→ Google Cloud Console 에서 먼저 만들어야 합니다:")
    log.error("   1) https://console.cloud.google.com → 프로젝트 생성/선택")
    log.error("   2) 'YouTube Data API v3' 사용 설정")
    log.error("   3) OAuth 동의 화면 구성 → 테스트 사용자에 %s 추가", ACCOUNT_HINT)
    log.error("   4) 사용자 인증 정보 → OAuth 클라이언트 ID → '데스크톱 앱' → JSON 다운로드")
    log.error("   5) 그 JSON 을 config 의 youtube.client_secret 경로(%s)에 배치",
              cs or "youtube.client_secret")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="곡 단위 YouTube 수동 업로드 스케줄러")
    ap.add_argument("--track", required=True, help="트랙 slug (예: geureoke)")
    ap.add_argument("--dry-run", action="store_true",
                    help="OAuth·업로드 없이 파싱·캡·대상만 출력")
    ap.add_argument("--privacy", default=None,
                    choices=["private", "unlisted", "public"], help="공개 범위(기본 config)")
    args = ap.parse_args(argv)

    slug = args.track
    tdir = ROOT / "tracks" / slug
    out = tdir / "out"
    desc_file = out / "youtube_description.txt"
    mani_path = out / "upload_manifest.json"

    cfg = load_config("config.yaml", str(tdir / "config.yaml"))
    # instrumental 은 산출물명이 <slug>_bgm.mp4(자막 없음), 그 외 vocal 은 <slug>_dual.mp4
    video = out / (f"{slug}_bgm.mp4" if cfg.get("mode") == "instrumental" else f"{slug}_dual.mp4")

    for p in (video, desc_file):
        if not p.exists():
            log.error("필수 파일 없음: %s", p)
            return 2

    yt = cfg.get("youtube", {})
    privacy = args.privacy or yt.get("privacy", "unlisted")
    category_id = yt.get("category_id", "10")

    # 4) 설명 파싱
    title, description, tags = parse_description(desc_file)
    log.info("제목: %s", title)
    log.info("설명 %d자 · 태그 %d개 · 공개=%s · 영상=%s",
             len(description), len(tags), privacy, video.name)

    # 3) 일일 캡 체크
    n, hits = today_upload_count()
    if n >= DAILY_CAP:
        log.error("일일 캡(%d) 초과 — 오늘 이미 %d건 업로드됨. 중단.", DAILY_CAP, n)
        for h in hits:
            log.error("  · %s → %s (%s)", h.get("track_id"), h.get("video_id"),
                      h.get("uploaded_at"))
        return 3

    if args.dry_run:
        log.info("[DRY-RUN] 실제 업로드 없이 종료 — 아래가 업로드될 내용입니다.")
        print(json.dumps({"track_id": slug, "title": title, "tags": tags,
                          "privacy": privacy, "category_id": str(category_id),
                          "description_chars": len(description), "video": str(video)},
                         ensure_ascii=False, indent=2))
        return 0

    # 멱등 차단: upload_ledger.json 에 이미 기록된 트랙은 재업로드하지 않는다(중복 방지).
    # 수동 발행(uploaded_via=manual) 트랙 포함 — Commander 직접 발행분을 스케줄러가 덮지 않도록.
    ledger_p = ROOT / "upload_ledger.json"
    if ledger_p.exists():
        try:
            _led = json.loads(ledger_p.read_text(encoding="utf-8"))
            _hit = next((e for e in _led.get("entries", []) if e.get("track") == slug), None)
        except Exception:                              # noqa: BLE001 — 깨진 원장은 차단하지 않음
            _hit = None
        if _hit is not None:
            log.error("멱등 차단: '%s' 는 upload_ledger 에 이미 기록됨(via=%s, video_id=%s) — 재업로드 스킵.",
                      slug, _hit.get("uploaded_via"), _hit.get("video_id"))
            return 5

    # 1) OAuth
    cs = yt.get("client_secret")
    tok = yt.get("token")
    if not cs or not Path(cs).exists():
        _oauth_missing_guide(cs)
        return 4

    from upload_youtube import _service                # OAuth 로직 재사용(DRY)
    log.info("OAuth 진행 — 브라우저에서 %s 계정으로 로그인하세요.", ACCOUNT_HINT)
    svc = _service(cs, tok)

    # 5) 업로드 + 기록
    resp = insert_video(svc, title, description, tags, category_id, privacy, video)
    vid = resp["id"]
    url = f"https://youtu.be/{vid}"
    rec = {
        "track_id": slug,
        "video_id": vid,
        "url": url,
        "title": title,
        "privacy": privacy,
        "uploaded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    record_manifest(mani_path, rec)
    log.info("업로드 완료 → %s (manifest 기록: %s)", url, mani_path)
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
