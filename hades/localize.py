# -*- coding: utf-8 -*-
"""localize.py — YouTube 글로벌 메타 표준 (ko default + en localization).

- defaultLanguage="ko", defaultAudioLanguage="ko"
- localizations["en"] = {title: EN 제목, description: EN 소개 + EN 가사}
EN 제목 = 표준 제목의 " / " 뒤 부분. EN 소개 = youtube_description.txt 의 영어 인트로.
EN 가사 = lyrics_en.txt (인스트루멘털은 (Instrumental) 표기).

재사용: upload_scheduler(신규 업로드), 소급 스크립트(기존분 videos.update) 공용.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 곡명 EN 폴백(표준 제목에 " / " 없는 경우)
EN_NAME_FALLBACK = {
    "songdo": "Songdo Amusement Park - Reina",
}


def _ascii_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if ord(c) < 128) / len(letters)


def en_intro(track: str) -> str:
    """youtube_description.txt 상단의 영어 인트로 문단 추출. 없으면 폴백."""
    p = ROOT / "tracks" / track / "out" / "youtube_description.txt"
    if p.exists():
        lines = p.read_text(encoding="utf-8").splitlines()
        block = []
        for ln in lines[1:]:
            s = ln.strip()
            if s.startswith("━") or s.startswith("═") or s.startswith("["):
                if block:
                    break
                continue
            if s.startswith("Reina ") or s.startswith("(YouTube") or s.startswith("#"):
                if block:
                    break
                continue
            if not s:
                if block:
                    break
                continue
            if _ascii_ratio(s) > 0.6 and len(s) > 12:   # 영어 문장
                block.append(s)
            elif block:
                break
        if block:
            return " ".join(block)
    return f"A song by Reina — Korean R&B / indie."


def en_lyrics(track: str) -> str | None:
    p = ROOT / "tracks" / track / "lyrics_en.txt"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip()


def en_title_from(current_title: str, track: str) -> str:
    """표준 제목의 ' / ' 뒤 = EN 제목. 없으면 폴백맵."""
    if " / " in current_title:
        return current_title.split(" / ", 1)[1].strip()
    return EN_NAME_FALLBACK.get(track, f"{track} - Reina")


def en_description(track: str, *, is_short: bool) -> str:
    intro = en_intro(track)
    if is_short:
        first = re.split(r"(?<=[.!?])\s", intro)[0]
        return f"{first}\n\nFull version on the channel.\n#Shorts"
    lyr = en_lyrics(track)
    body = f"{intro}\n\nReina — original song, lyrics & production."
    if lyr:
        body += "\n\n[Lyrics]\n" + lyr
    else:
        body += "\n\n(Instrumental)"
    return body


def build_localization(track: str, current_title: str, *, is_short: bool) -> dict:
    """videos.update / insert 용 메타 조각 반환."""
    return {
        "defaultLanguage": "ko",
        "defaultAudioLanguage": "ko",
        "localizations": {
            "en": {
                "title": en_title_from(current_title, track)[:100],
                "description": en_description(track, is_short=is_short)[:5000],
            }
        },
    }
