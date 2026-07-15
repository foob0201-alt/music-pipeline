r"""
make_shorts.py v2 — 코러스 훅 세로 숏츠 렌더 (포터블 단독 모듈)

목적:
  기존 곡의 align.json(줄/단어 타임코드) + 가사(섹션 태그) + 커버 + 오디오만으로,
  코러스 훅 구간을 자동 감지해 세로 1080x1920 YouTube Shorts 클립을 만든다.

포터블 원칙:
  - HADES 내부 모듈(align.py/hades_util 등)에 의존하지 않는다. stdlib + ffmpeg/ffprobe 만.
  - 시크릿·크레덴셜을 읽거나 출력하지 않는다.
  - 어떤 트랙에도 단독 실행 가능(경로만 인자로 준다).

길이 스펙(Navigator 2026-07-09 확정):
  - 클립 20~40초. 코러스 훅이 온전히 담기는 "최소 길이 우선", 억지 연장 금지.
  - 코러스 자동감지 최소길이 파라미터 = 20초(--min-sec). 상한 --max-sec = 40초.
  - 감지 규칙: 가사의 [Chorus] 섹션 태그를 align.json 줄 순서에 매핑 → 첫 코러스 블록.
      * 블록 길이가 [min,max] 안이면 그대로 사용.
      * min 미만이면 뒤 줄로 최소 확장(≥min, ≤max)에서 멈춤.
      * max 초과면 훅 앞줄들을 담되 줄 경계에서 ≤max로 컷(롱테일 홀드 절단).
      * 그래도 [min,max]에 훅이 안 담기면 감지 실패 반환(호출측이 정지·보고).

영상:
  - 커버(가로 2560x1440) 중앙 9:16 크롭(810x1440) → 1080x1920 스케일 + 완만한 Ken Burns.
  - dual mp4를 크롭하지 않는다(하단 가로자막이 딸려오므로). 커버+오디오 재렌더 경로.

자막:
  - 숏츠 전용 ASS 재생성. PlayRes 1080x1920 기준 폰트·마진 재계산.
  - dual 스타일 유지: KO 노랑 카라오케(\kf, Secondary=흰→Primary=노랑 스윕) 위 / EN 크림 아래.

인코딩(하우스 표준):
  - libx264 High · yuv420p · BT.709(full→tv 태깅) · 1-pass CRF16 · preset slow
  - AAC-LC 48kHz 384k · +faststart · fps 기본 30.

사용:
  python make_shorts.py --align tracks/<slug>/out/align.json \
    --lyrics-ko tracks/<slug>/lyrics_ko.txt --lyrics-en tracks/<slug>/lyrics_en.txt \
    --cover tracks/<slug>/cover.jpg --audio tracks/<slug>/<slug>.mp3 \
    --out tracks/<slug>/out/<slug>_shorts.mp4 --title "제목"
  # 감지만 미리보기:
  python make_shorts.py ... --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------- 데이터 모델
@dataclass
class Line:
    idx: int
    text: str
    start: float
    end: float
    words: List[Tuple[str, float, float]] = field(default_factory=list)
    section: str = ""


# ---------------------------------------------------------------- 로더
def load_align(path: Path) -> List[Line]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: List[Line] = []
    for i, L in enumerate(data.get("lines", [])):
        words = [(w["w"], float(w["start"]), float(w["end"])) for w in L.get("words", [])]
        out.append(Line(i, L["ko"], float(L["start"]), float(L["end"]), words))
    return out


_norm = lambda s: re.sub(r"\s+", "", s)


def parse_sections(lyrics_path: Path) -> List[Tuple[str, str]]:
    """가사 파일 → [(정규화 섹션명, 부른 줄 텍스트)] 순서 유지. 태그/애드립 줄 제외."""
    seq: List[Tuple[str, str]] = []
    sec = ""
    for raw in lyrics_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("[") and s.endswith("]"):
            sec = re.sub(r"\s*\d+\s*$", "", s[1:-1]).strip().lower()
            continue
        if s.startswith("("):          # (adlib) 류는 자막 비대상
            continue
        seq.append((sec, s))
    return seq


def attach_sections(lines: List[Line], seq: List[Tuple[str, str]]) -> bool:
    """align 줄에 섹션명 부착. 순서 1:1 매핑, 텍스트로 검증. 전부 일치 시 True."""
    ok = len(lines) == len(seq)
    for i, ln in enumerate(lines):
        if i < len(seq):
            ln.section = seq[i][0]
            if _norm(ln.text) != _norm(seq[i][1]):
                ok = False
    return ok


def _en_parse(lyrics_en: Path, keep_adlib: bool) -> List[str]:
    out: List[str] = []
    for raw in lyrics_en.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or (s.startswith("[") and s.endswith("]")):
            continue
        if not keep_adlib and s.startswith("("):
            continue
        out.append(s)
    return out


def en_lines(lyrics_en: Optional[Path]) -> Optional[List[str]]:
    if not lyrics_en or not lyrics_en.exists():
        return None
    return _en_parse(lyrics_en, keep_adlib=False)


def en_lines_matched(lyrics_en: Optional[Path], target: int) -> Optional[List[str]]:
    """EN 줄 리스트를 align 줄수(target)에 맞춘다 — 애드립 포함/제외 중 일치하는 파싱 선택.
    (donghae 처럼 align.json이 애드립을 포함하는 트랙에서 EN 인덱스 어긋남 방지.)"""
    if not lyrics_en or not lyrics_en.exists():
        return None
    a = _en_parse(lyrics_en, keep_adlib=False)
    b = _en_parse(lyrics_en, keep_adlib=True)
    for c in (a, b):
        if len(c) == target:
            return c
    return a  # 둘 다 불일치 → 자막 파서 기본값(최선 노력)


# ---------------------------------------------------------------- 코러스 감지
@dataclass
class Window:
    t0: float
    t1: float
    line_idxs: List[int]
    reason: str

    @property
    def dur(self) -> float:
        return self.t1 - self.t0


def _blocks(lines: List[Line], name: str) -> List[Tuple[int, int]]:
    runs, i, n = [], 0, len(lines)
    while i < n:
        if lines[i].section == name:
            j = i
            while j + 1 < n and lines[j + 1].section == name:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def detect_chorus(lines: List[Line], *, min_sec: float, max_sec: float,
                  which: int = 0) -> Tuple[Optional[Window], str]:
    """첫(또는 which번째) [chorus] 블록을 [min,max] 창으로 확정. 실패 시 (None, 사유)."""
    runs = _blocks(lines, "chorus")
    if not runs:
        return None, "가사에 [Chorus] 섹션 태그가 없음(코러스 자동감지 불가)"
    if which >= len(runs):
        return None, f"코러스 블록 {which} 없음(총 {len(runs)}개)"
    s, e = runs[which]
    t0 = lines[s].start
    t1 = lines[e].end
    dur = t1 - t0

    if dur < min_sec:
        # 뒤 줄로 최소 확장
        k = e
        while dur < min_sec and k + 1 < len(lines):
            k += 1
            t1 = lines[k].end
            dur = t1 - t0
        if dur < min_sec:
            return None, (f"코러스+후속 전체가 {dur:.1f}s < {min_sec:.0f}s "
                          f"(억지 연장 금지 → 정지)")
        if dur > max_sec:
            return None, (f"코러스를 {min_sec:.0f}s로 채우려면 {dur:.1f}s가 되어 "
                          f"{max_sec:.0f}s 초과(줄 경계상 [min,max] 불가 → 정지)")
        idxs = [ln.idx for ln in lines if ln.start < t1 - 1e-6 and ln.end > t0 + 1e-6]
        return Window(t0, t1, idxs, f"chorus#{which} +후속확장 {dur:.1f}s"), "ok"

    if dur > max_sec:
        # 줄 경계에서 ≤max 로 컷(마지막 롱테일 홀드 절단). 훅 앞줄부터 누적.
        t1c = None
        for k in range(s, e + 1):
            if lines[k].end - t0 <= max_sec:
                t1c = lines[k].end
            else:
                break
        if t1c is None or (t1c - t0) < min_sec:
            return None, (f"첫 코러스 줄 홀드가 길어 [{min_sec:.0f},{max_sec:.0f}]s "
                          f"창에 훅이 안 담김 → 정지")
        t1 = t1c
        idxs = [ln.idx for ln in lines if ln.start < t1 - 1e-6 and ln.end > t0 + 1e-6]
        return Window(t0, t1, idxs, f"chorus#{which} 롱테일컷 {t1 - t0:.1f}s"), "ok"

    idxs = [ln.idx for ln in lines[s:e + 1]]
    return Window(t0, t1, idxs, f"chorus#{which} 그대로 {dur:.1f}s"), "ok"


def _fit_window(lines, s, e, min_sec, max_sec, label):
    """줄 블록 [s,e] 를 [min,max] 창으로 확정(뒤 확장/롱테일 컷). 실패 시 None."""
    t0, t1 = lines[s].start, lines[e].end
    dur = t1 - t0
    if dur < min_sec:
        k = e
        while dur < min_sec and k + 1 < len(lines):
            k += 1; t1 = lines[k].end; dur = t1 - t0
        if dur < min_sec or dur > max_sec:
            return None
    elif dur > max_sec:
        t1c = None
        for k in range(s, e + 1):
            if lines[k].end - t0 <= max_sec:
                t1c = lines[k].end
            else:
                break
        if t1c is None or (t1c - t0) < min_sec:
            return None
        t1 = t1c
    idxs = [ln.idx for ln in lines if ln.start < t1 - 1e-6 and ln.end > t0 + 1e-6]
    return Window(t0, t1, idxs, f"{label} {t1 - t0:.1f}s")


def detect_by_repetition(lines, *, min_sec, max_sec):
    """[Chorus] 태그가 없을 때 폴백 — 가장 반복되는 연속 줄 블록(=후렴)의 첫 등장을 창으로."""
    from collections import Counter
    nz = lambda s: re.sub(r"[\s,.~]", "", s)
    cnt = Counter(nz(l.text) for l in lines)
    rep = [i for i, l in enumerate(lines) if cnt[nz(l.text)] >= 2]
    if not rep:
        return None, "반복 줄 없음 — 후렴 추정 불가"
    runs, st, pv = [], rep[0], rep[0]
    for i in rep[1:]:
        if i == pv + 1:
            pv = i
        else:
            runs.append((st, pv)); st, pv = i, i
    runs.append((st, pv))
    runs.sort(key=lambda r: (-(r[1] - r[0]), r[0]))   # 긴 블록 우선, 동률이면 이른 것
    for s, e in runs:
        w = _fit_window(lines, s, e, min_sec, max_sec, "repeat-hook")
        if w:
            return w, "ok(repetition)"
    return None, "반복 블록이 [min,max]에 안 맞음"


def detect_peak_window(audio, *, min_sec, max_sec):
    """인스트루멘털 — RMS 에너지 최대 구간(0.5s 해상도)을 훅으로."""
    import wave, struct, tempfile, os
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-y", "-i", str(audio), "-ac", "1", "-ar", "8000",
                    "-f", "wav", tmp], check=True, capture_output=True)
    try:
        w = wave.open(tmp, "rb"); n = w.getnframes(); sr = w.getframerate()
        raw = w.readframes(n); w.close()
    finally:
        os.remove(tmp)
    data = struct.unpack("<%dh" % (len(raw) // 2), raw)
    hop = sr // 2
    energies = [sum(x * x for x in data[i:i + hop]) / max(1, len(data[i:i + hop]))
                for i in range(0, len(data), hop) if data[i:i + hop]]
    if not energies:
        return None, "에너지 계산 실패"
    best = None
    for Lsec in (min_sec, (min_sec + max_sec) / 2.0, max_sec):
        wlen = max(1, int(round(Lsec * 2)))
        for stt in range(0, len(energies) - wlen + 1):
            m = sum(energies[stt:stt + wlen]) / wlen
            if best is None or m > best[0]:
                best = (m, stt * 0.5, (stt + wlen) * 0.5, Lsec)
    if best is None:
        return None, "창 배치 실패"
    _, t0, t1, L = best
    return Window(t0, t1, [], f"RMS-peak {L:.0f}s"), "ok(rms)"


# ---------------------------------------------------------------- ASS (세로 전용)
def _ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _karaoke(words: List[Tuple[str, float, float]], line_start: float, text: str) -> str:
    if not words:
        return text
    parts, cursor = [], line_start
    for w, ws, we in words:
        gap = max(0.0, ws - cursor)
        if gap > 0.02:
            parts.append(f"{{\\k{int(round(gap * 100))}}}")
        dur = max(1, int(round((we - ws) * 100)))
        parts.append(f"{{\\kf{dur}}}{w} ")
        cursor = we
    return "".join(parts).rstrip()


# 세로 숏츠 스타일 상수(1080x1920 기준, dual 팔레트 유지)
S = dict(
    play_w=1080, play_h=1920, font="Malgun Gothic",
    ko_fs=66, en_fs=50, ko_mv=620, en_mv=540, margin_lr=96,  # en_mv: KO(620) 바로 아래 ~20px, 하단 UI존 위
    gold="&H0000D7FF", white="&H00FFFFFF", cream="&H00BED7DC",
    outline_c="&H00202020", back_c="&H64000000", outline=4, shadow=1,
    fade_in=250, fade_out=250, pop=106,
    # 제목 오버레이(상단 세이프존): 흰색 볼드 + 아웃라인, Alignment 8(top-center)
    title_fs=64, title_mv=104, title_color="&H00FFFFFF", title_outline=4,
    # 핸들 시그니처(하단 좌측 구석, 보조 크기): 반투명 흰색, 제목보다 작게
    handle_fs=40, handle_mv=48, handle_color="&H28FFFFFF", handle_outline=3,
)


def build_shorts_ass(win: Window, lines: List[Line], en: Optional[List[str]],
                     title: str, *, title_overlay: bool = True, handle: str = "") -> str:
    fmt = ("Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
           "MarginV, Effect, Text")
    style_fmt = ("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                 "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                 "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                 "Alignment, MarginL, MarginR, MarginV, Encoding")
    ko = (f"Style: KO,{S['font']},{S['ko_fs']},{S['gold']},{S['white']},"
          f"{S['outline_c']},{S['back_c']},1,0,0,0,100,100,0,0,1,"
          f"{S['outline']},{S['shadow']},2,{S['margin_lr']},{S['margin_lr']},{S['ko_mv']},1")
    en_s = (f"Style: EN,{S['font']},{S['en_fs']},{S['cream']},{S['cream']},"
            f"{S['outline_c']},{S['back_c']},0,1,0,0,100,100,0,0,1,"
            f"{max(2, S['outline'] - 1)},{S['shadow']},2,{S['margin_lr']},{S['margin_lr']},{S['en_mv']},1")
    # TITLE: 상단 세이프존 제목 오버레이(Alignment 8 = top-center)
    title_s = (f"Style: TITLE,{S['font']},{S['title_fs']},{S['title_color']},{S['title_color']},"
               f"{S['outline_c']},{S['back_c']},1,0,0,0,100,100,0,0,1,"
               f"{S['title_outline']},{S['shadow']},8,{S['margin_lr']},{S['margin_lr']},{S['title_mv']},1")
    # HANDLE: 하단 좌측 구석 핸들 시그니처(Alignment 1 = bottom-left, 반투명·보조 크기)
    handle_s = (f"Style: HANDLE,{S['font']},{S['handle_fs']},{S['handle_color']},{S['handle_color']},"
                f"{S['outline_c']},{S['back_c']},0,0,0,0,100,100,0,0,1,"
                f"{S['handle_outline']},{S['shadow']},1,40,40,{S['handle_mv']},1")
    hdr = (
        "[Script Info]\n"
        f"Title: {title} [shorts]\n"
        "ScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
        f"PlayResX: {S['play_w']}\nPlayResY: {S['play_h']}\n\n"
        "[V4+ Styles]\n" + style_fmt + "\n" + ko + "\n" + en_s + "\n" + title_s + "\n"
        + handle_s + "\n\n"
        "[Events]\n" + fmt + "\n"
    )
    tag = (f"{{\\fad({S['fade_in']},{S['fade_out']})"
           f"\\t(0,180,\\fscx{S['pop']}\\fscy{S['pop']})\\t(180,360,\\fscx100\\fscy100)}}")
    ev = []
    if title_overlay and title:
        # 클립 전체 구간에 제목 표시(부드러운 페이드 인)
        ev.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(win.dur)},TITLE,,0,0,0,,"
                  f"{{\\fad(400,0)}}{title}")
    if handle:
        # 하단 구석 핸들 시그니처(클립 전체, 페이드 인)
        ev.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(win.dur)},HANDLE,,0,0,0,,"
                  f"{{\\fad(400,0)}}{handle}")
    by_idx = {ln.idx: ln for ln in lines}
    for i in win.line_idxs:
        ln = by_idx[i]
        st = max(win.t0, ln.start) - win.t0
        en_t = min(win.t1, ln.end) - win.t0
        if en_t <= st:
            continue
        # 카라오케는 원 타임코드 기준으로 만들고 줄을 창 시작으로 리베이스
        kt = _karaoke([(w, ws - win.t0, we - win.t0) for w, ws, we in ln.words],
                      ln.start - win.t0, ln.text)
        ev.append(f"Dialogue: 0,{_ass_time(st)},{_ass_time(en_t)},KO,,0,0,0,,{tag}{kt}")
        if en and i < len(en):
            ev.append(f"Dialogue: 0,{_ass_time(st)},{_ass_time(en_t)},EN,,0,0,0,,{tag}{en[i]}")
    return hdr + "\n".join(ev) + "\n"


# ---------------------------------------------------------------- 인코딩
def _esc_sub(path: Path) -> str:
    s = str(path.resolve())
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render(cover: Path, audio: Path, ass: Path, out: Path, win: Window, *,
           fps: int = 30, crf: int = 16, zoom_end: float = 1.08,
           top_frac: float = 0.12) -> Path:
    dur = win.dur
    frames = int(round(dur * fps))
    zstep = max(0.00005, (zoom_end - 1.0) / max(1, frames))
    # 커버(가로 2560x1440) → 세로 9:16. 상단 top_frac 을 버려(제목 밴드 제외) 나머지에서
    # 중앙 9:16 크롭. 하단(피사체) 유지. top_frac=0 이면 전높이 중앙 크롭(스펙 원형).
    CW, CH = 2560, 1440
    drop = int(round(CH * max(0.0, min(0.4, top_frac))))
    hc = CH - drop
    wc = int(round(hc * 9 / 16))
    xc = (CW - wc) // 2
    yc = drop
    vf = (
        f"[0:v]scale={CW}:{CH}:flags=lanczos,"
        f"crop={wc}:{hc}:{xc}:{yc},"
        f"scale=1080:1920:flags=lanczos,"
        f"zoompan=z='min(zoom+{zstep:.6f}\\,{zoom_end})':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},"
        f"scale=1080:1920:in_range=full:out_range=tv,"
        f"format=yuv420p,"
        f"setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
        + (f",subtitles=filename='{_esc_sub(ass)}'[v]" if ass is not None else "[v]")
    )
    afade = f"afade=t=in:st=0:d=0.12,afade=t=out:st={max(0.0, dur - 0.35):.3f}:d=0.35"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(cover),
        "-ss", f"{win.t0:.3f}", "-i", str(audio),
        "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
        "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-profile:v", "high", "-crf", str(crf), "-preset", "slow",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-color_range", "tv",
        "-af", afade, "-c:a", "aac", "-b:a", "384k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="코러스 훅 세로 숏츠 렌더")
    ap.add_argument("--align", default=None, help="align.json (보컬 필수)")
    ap.add_argument("--lyrics-ko", default=None, help="lyrics_ko.txt (보컬 필수)")
    ap.add_argument("--lyrics-en", default=None)
    ap.add_argument("--cover", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="",
                    help="상단 오버레이용 대표 가사구절 1줄(자막과 별개 소스)")
    ap.add_argument("--song", default="",
                    help="곡명 — 상단 오버레이를 표준 포맷 '곡명 - Reina'로 조립(가사훅 미포함)")
    ap.add_argument("--min-sec", type=float, default=20.0)
    ap.add_argument("--max-sec", type=float, default=40.0)
    ap.add_argument("--which", type=int, default=0, help="몇 번째 코러스 블록(0=첫)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--top-frac", type=float, default=0.12,
                    help="상단 크롭 비율(제목 밴드 제외). 0=전높이 중앙크롭")
    ap.add_argument("--instrumental", action="store_true",
                    help="가사 없는 인스트루멘털 — RMS 피크 구간, 가사 자막 없음")
    ap.add_argument("--no-title-overlay", action="store_true",
                    help="상단 제목 오버레이 끄기(기본 켬)")
    ap.add_argument("--handle", default="@reina_music0217",
                    help="하단 구석 핸들 시그니처(빈 문자열이면 끔)")
    ap.add_argument("--dry-run", action="store_true", help="감지만 출력(렌더 안 함)")
    a = ap.parse_args()
    title_overlay = not a.no_title_overlay
    # 상단 오버레이 = 표준 포맷 "곡명 - Reina" (곡명+아티스트만; 가사훅 미포함, 자막과 독립).
    # 가사 키워드는 화면 밖 메타데이터(제목/설명/해시태그)로만 유지(2026-07-15 표준 변경).
    # --song 지정 시 "곡명 - Reina" 조립, 미지정 시 --title 원문(하위호환).
    overlay_text = ('%s - Reina' % a.song) if a.song else a.title

    # ---- 인스트루멘털: RMS 피크, 가사 자막 없음(제목 오버레이는 유지) ----
    if a.instrumental:
        win, reason = detect_peak_window(Path(a.audio), min_sec=a.min_sec, max_sec=a.max_sec)
        if win is None:
            print(f"DETECT_FAIL: {reason}"); return 2
        print(f"DETECT_OK: {reason}\n  window: {win.t0:.2f} -> {win.t1:.2f}  dur={win.dur:.2f}s (RMS)")
        if a.dry_run:
            return 0
        ass_arg = None
        if (title_overlay and a.title) or a.handle:
            ass_path = Path(a.out).with_suffix(".shorts.ass")
            ass_path.write_text(build_shorts_ass(win, [], None, overlay_text,
                                                 title_overlay=title_overlay, handle=a.handle),
                                encoding="utf-8")
            ass_arg = ass_path
        out = render(Path(a.cover), Path(a.audio), ass_arg, Path(a.out), win,
                     fps=a.fps, crf=a.crf, top_frac=a.top_frac)
        print(f"RENDER_OK: {out}  ({out.stat().st_size / 1e6:.1f} MB)")
        return 0

    # ---- 보컬: [Chorus] 태그 우선, 없으면 반복줄 폴백 ----
    if not a.align or not a.lyrics_ko:
        print("ERROR: 보컬은 --align/--lyrics-ko 필요(또는 --instrumental)"); return 2
    lines = load_align(Path(a.align))
    seq = parse_sections(Path(a.lyrics_ko))
    matched = attach_sections(lines, seq)
    if not matched:
        print(f"[WARN] align({len(lines)})↔가사({len(seq)}) 매핑 불일치 — 섹션 신뢰도 낮음",
              file=sys.stderr)
    win, reason = detect_chorus(lines, min_sec=a.min_sec, max_sec=a.max_sec, which=a.which)
    if win is None:
        win, reason = detect_by_repetition(lines, min_sec=a.min_sec, max_sec=a.max_sec)
    if win is None:
        # 최종 폴백: RMS 피크 구간 + 그 창에 걸치는 자막줄 표시
        pw, prs = detect_peak_window(Path(a.audio), min_sec=a.min_sec, max_sec=a.max_sec)
        if pw is not None:
            idxs = [ln.idx for ln in lines if ln.start < pw.t1 - 1e-6 and ln.end > pw.t0 + 1e-6]
            win = Window(pw.t0, pw.t1, idxs, "RMS-peak(fallback)"); reason = "ok(rms-fallback)"
    if win is None:
        print(f"DETECT_FAIL: {reason}")
        for bi, (s, e) in enumerate(_blocks(lines, "chorus")):
            print(f"  candidate#{bi}: {lines[s].start:.2f}-{lines[e].end:.2f} "
                  f"({lines[e].end - lines[s].start:.1f}s) lines {s}..{e}")
        return 2

    shown = [f"{i}:{lines[i].start:.2f}-{lines[i].end:.2f}" for i in win.line_idxs]
    print(f"DETECT_OK: {reason}")
    print(f"  window: {win.t0:.2f} -> {win.t1:.2f}  dur={win.dur:.2f}s  sections_matched={matched}")
    print(f"  lines: {', '.join(shown)}")
    for i in win.line_idxs:
        print(f"    [{i}] {lines[i].section:10s} | {lines[i].text}")
    if a.dry_run:
        return 0

    ass_path = Path(a.out).with_suffix(".shorts.ass")
    en = en_lines_matched(Path(a.lyrics_en), len(lines)) if a.lyrics_en else None
    ass_path.write_text(build_shorts_ass(win, lines, en, overlay_text or Path(a.out).stem,
                                         title_overlay=title_overlay, handle=a.handle),
                        encoding="utf-8")
    print(f"  ASS: {ass_path}")
    out = render(Path(a.cover), Path(a.audio), ass_path, Path(a.out), win,
                 fps=a.fps, crf=a.crf, top_frac=a.top_frac)
    print(f"RENDER_OK: {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
