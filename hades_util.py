"""
hades_util.py — 공용 유틸 (네비게이터 결정값을 실행자가 공유)

책임: 설정 로드/병합 · 로깅 · 경로 해석 · 멱등 매니페스트 · 재시도/백오프 · 시크릿 보안.
이 파일에는 '판단'이 없다. 모두 결정된 규칙의 반복 수행이다. (HADES §2.1)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - 안내만
    yaml = None


# ---------------------------------------------------------------- 로깅
def get_logger(name: str = "hades") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                                         datefmt="%H:%M:%S"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger


log = get_logger()


# ---------------------------------------------------------------- 설정
def _deep_merge(base: dict, over: dict) -> dict:
    """over 값이 base를 덮어쓴다. dict는 재귀 병합."""
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(root_cfg: str = "config.yaml", track_cfg: Optional[str] = None) -> dict:
    """루트 기본값 + 곡별 설정 병합 (곡별이 우선)."""
    if yaml is None:
        raise RuntimeError("pyyaml 미설치: pip install pyyaml")
    with open(root_cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if track_cfg and os.path.exists(track_cfg):
        with open(track_cfg, "r", encoding="utf-8") as f:
            cfg = _deep_merge(cfg, yaml.safe_load(f) or {})
    return cfg


# ---------------------------------------------------------------- 컨텍스트 (단계 간 전달)
@dataclass
class Context:
    """단계 사이로 흐르는 산출물 맵. (HADES §3.3)"""
    cfg: dict
    track_dir: Path
    out_dir: Path
    audio: Path
    cover: Path
    lyrics_ko: Path
    lyrics_en: Optional[Path]
    title: str
    ass_map: Dict[str, Path] = field(default_factory=dict)     # {ver: ass}
    lrc: Optional[Path] = None
    video_map: Dict[str, Path] = field(default_factory=dict)   # {ver: mp4}
    youtube_urls: Dict[str, str] = field(default_factory=dict) # {ver: url}

    @classmethod
    def from_cfg(cls, cfg: dict) -> "Context":
        track_dir = Path(cfg["track"]["dir"])
        p = cfg["paths"]
        out_dir = track_dir / p.get("out_dir", "out")
        out_dir.mkdir(parents=True, exist_ok=True)
        ly_en = track_dir / p["lyrics_en"] if p.get("lyrics_en") else None
        return cls(
            cfg=cfg,
            track_dir=track_dir,
            out_dir=out_dir,
            audio=track_dir / p["audio"],
            cover=track_dir / p["cover"],
            lyrics_ko=track_dir / p["lyrics_ko"],
            lyrics_en=ly_en,
            title=cfg.get("meta", {}).get("title", cfg["track"]["name"]),
        )


# ---------------------------------------------------------------- 멱등 매니페스트 (P0)
class Manifest:
    """업로드/게시 중복 방지. 키 단위로 완료 기록."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: Dict[str, Any] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.data = {}

    def done(self, key: str) -> bool:
        return key in self.data

    def get(self, key: str) -> Any:
        return self.data.get(key)

    def mark(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2),
                             encoding="utf-8")


# ---------------------------------------------------------------- 재시도/백오프 (P0)
def retry(fn: Callable, *, tries: int = 4, base: float = 2.0, what: str = "op"):
    """지수 백오프 재시도. 마지막 실패는 예외 전파."""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - 업로드 계열은 광범위 예외
            last = e
            wait = base ** i
            log.warning("%s 실패 (%d/%d): %s — %.1fs 후 재시도", what, i + 1, tries, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"{what} {tries}회 모두 실패") from last


# ---------------------------------------------------------------- 시크릿 보안 (P0)
def harden_secret(path: str | Path) -> None:
    """크레덴셜 파일 권한을 0600으로. 존재할 때만."""
    p = Path(path)
    if p.exists():
        p.chmod(stat.S_IRUSR | stat.S_IWUSR)
        log.info("secret chmod 600: %s", p)


# ---------------------------------------------------------------- 가사 파서
SECTION_PREFIXES = ("[", "(")  # [Verse], (Chorus) 등 섹션 태그 줄은 자막에서 제외


def read_lyric_lines(path: str | Path) -> list[str]:
    """빈 줄·섹션 태그 줄 제외, 자막용 라인 리스트 반환."""
    lines: list[str] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith(SECTION_PREFIXES) and s.endswith(("]", ")")):
            continue
        lines.append(s)
    return lines


# ---------------------------------------------------------------- 커버 승인 게이트 (코드 1차)
# 훅(.claude/hooks/cover_gate.py)이 못 보는 내부 subprocess 인코딩 경로를 코드에서 막는다.
def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _cover_paths(slug: str) -> tuple[Path, Path]:
    """slug → (cover.jpg, out/.cover_ok) 경로(레포 루트 기준)."""
    base = Path("tracks") / slug
    return base / "cover.jpg", base / "out" / ".cover_ok"


def approve_cover(slug: str) -> Path:
    """현재 cover.jpg 의 sha256 을 tracks/<slug>/out/.cover_ok 에 원자적으로 기록(승인)."""
    cover, ok = _cover_paths(slug)
    if not cover.exists():
        raise FileNotFoundError(f"커버 없음: {cover}")
    ok.parent.mkdir(parents=True, exist_ok=True)
    digest = _sha256_file(cover)
    tmp = ok.parent / ".cover_ok.tmp"
    tmp.write_text(digest + "\n", encoding="utf-8")
    os.replace(tmp, ok)                       # 원자적 교체(같은 디렉터리)
    log.info("커버 승인: %s → %s (sha256=%s…)", cover.name, ok, digest[:12])
    return ok


def record_upload_spotcheck(track: str, ver: str, url: str, *,
                            every: int = 5, ledger: str = "upload_ledger.json") -> bool:
    """전역 업로드 원장에 기록하고 every건당 1건 '사후 확인(spot_check)' 플래그를 세운다.
    무인 게이트1 도입에 따른 사후 표본검사(HADES). 반환: 이 업로드가 표본이면 True."""
    p = Path(ledger)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"count": 0, "entries": []}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data["count"] = int(data.get("count", 0)) + 1
    flag = (data["count"] % every == 0)
    data.setdefault("entries", []).append({
        "n": data["count"], "track": track, "ver": ver, "url": url,
        "spot_check": flag, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
    return flag


def cover_gate_ok(slug: str) -> bool:
    """.cover_ok 가 존재하고 현재 cover.jpg 해시와 일치해야 True (둘 다 충족)."""
    cover, ok = _cover_paths(slug)
    if not cover.exists() or not ok.exists():
        return False
    toks = ok.read_text(encoding="utf-8").split()
    rec = toks[0].strip() if toks else ""
    return bool(rec) and _sha256_file(cover) == rec
