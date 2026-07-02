"""
post_threads.py — Threads(Meta) 게시

- 공식 Graph API. 본인 계정 텍스트+링크 게시(검수 불요 범위).
- 장기 액세스 토큰 캐시 + 만료 임박 시 자동 갱신.
- 재시도/백오프 + 멱등(이미 게시한 곡은 건너뜀). (P0)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from hades_util import Context, Manifest, get_logger, harden_secret, retry

log = get_logger("threads")

GRAPH = "https://graph.threads.net/v1.0"


def _load_token(token_file: str) -> dict:
    p = Path(token_file)
    if not p.exists():
        raise RuntimeError(f"Threads 토큰 파일 없음: {token_file}")
    return json.loads(p.read_text(encoding="utf-8"))


def _maybe_refresh(tok: dict, token_file: str) -> dict:
    """만료 7일 이내면 장기토큰 갱신."""
    import requests
    exp = tok.get("expires_at", 0)
    if exp and exp - time.time() > 7 * 86400:
        return tok
    r = requests.get(f"{GRAPH}/refresh_access_token",
                     params={"grant_type": "th_refresh_token",
                             "access_token": tok["access_token"]}, timeout=30)
    if r.ok:
        d = r.json()
        tok["access_token"] = d.get("access_token", tok["access_token"])
        tok["expires_at"] = time.time() + d.get("expires_in", 5184000)
        Path(token_file).write_text(json.dumps(tok, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
        harden_secret(token_file)
        log.info("Threads 토큰 갱신됨")
    return tok


def _post(user_id: str, token: str, text: str) -> str:
    import requests
    # 1) 컨테이너 생성
    c = requests.post(f"{GRAPH}/{user_id}/threads",
                      params={"media_type": "TEXT", "text": text,
                              "access_token": token}, timeout=30)
    c.raise_for_status()
    cid = c.json()["id"]
    # 2) 게시
    p = requests.post(f"{GRAPH}/{user_id}/threads_publish",
                      params={"creation_id": cid, "access_token": token}, timeout=30)
    p.raise_for_status()
    return p.json()["id"]


def run(ctx: Context) -> Context:
    th = ctx.cfg.get("threads", {})
    if not th.get("enabled", False):
        log.info("threads.enabled=false — 건너뜀")
        return ctx
    if not ctx.youtube_urls:
        log.warning("youtube_urls 없음 — 링크 없이 게시 진행")

    token_file = th.get("token_file", "threads_token.json")
    harden_secret(token_file)
    tok = _maybe_refresh(_load_token(token_file), token_file)

    # 게시 텍스트: dual 우선, 없으면 첫 버전 링크
    url = ctx.youtube_urls.get("dual") or next(iter(ctx.youtube_urls.values()), "")
    text = th.get("text_template", "{title}\n\n{url}").format(title=ctx.title, url=url)

    mani = Manifest(ctx.out_dir / "manifest.json")
    key = f"threads:{ctx.track_dir.name}"
    if mani.done(key):
        log.info("이미 게시됨(매니페스트): %s", mani.get(key))
        return ctx

    pid = retry(lambda: _post(th["user_id"], tok["access_token"], text),
                what="threads-post")
    mani.mark(key, pid)
    log.info("Threads 게시 완료: id=%s", pid)
    return ctx
