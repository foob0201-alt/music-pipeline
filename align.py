r"""
align.py — 보컬분리 · KO 정렬 · EN 1:1 상속 · 액션 ASS / LRC 생성

설계:
- 음원은 한국어 보컬 → **KO를 음원에 정렬**(forced alignment). 인식이 빗나가도 화면엔 항상 실제 가사.
- EN은 단어 타임스탬프가 없으므로 KO 줄과 **1:1 타임코드 상속**(줄 단위).
- 액션 자막: 줄 팝업(\fad+\t 스케일) + 단어 색채움(\kf). libass 네이티브 1패스.
- ASS 빌더(build_ass_*)는 **순수 함수**라 음원/WhisperX 없이도 단위검증 가능.
"""
from __future__ import annotations

import difflib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from hades_util import Context, get_logger, read_lyric_lines

log = get_logger("align")


# ---------------------------------------------------------------- 타이밍 모델
@dataclass
class LineTiming:
    text: str
    start: float           # 초
    end: float
    words: List[Tuple[str, float, float]] = field(default_factory=list)  # (word, ws, we)


# ---------------------------------------------------------------- ASS 시간 포맷
def ass_time(t: float) -> str:
    if t < 0:
        t = 0.0
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


# ---------------------------------------------------------------- 스타일 블록
def _style_block(cfg: dict, mode: str) -> str:
    # 기본값은 config.yaml 실효값과 일치(이원화 제거): 폰트=Malgun Gothic,
    # font_size=110, dual 마진=315/201. config가 있으면 config 우선, 없어도 동일 결과.
    s = cfg.get("subtitle", {})
    font = s.get("font", "Malgun Gothic")
    scale = float(s.get("scale", 1.0))                 # subtitle_scale: 폰트·마진·갭 비례 확대
    fs = int(round(s.get("font_size", 110) * scale))
    primary = s.get("highlight_color", "&H0000D7FF")   # 채워진(부른) 색 = 노랑
    secondary = s.get("primary_color", "&H00FFFFFF")   # 아직 안부른 색 = 흰색
    en_color = s.get("en_color", "&H00BED7DC")         # 크림
    outline_c = s.get("outline_color", "&H00202020")
    back_c = "&H64000000"
    outline = s.get("outline", 3)
    shadow = s.get("shadow", 1)

    # 모드별 세로 위치(아래 정렬, MarginV 클수록 위) — scale에 비례해 마진·갭 재계산
    if mode == "dual":
        ko_mv = int(round(s.get("dual_ko_margin", 315) * scale))
        en_mv = int(round(s.get("dual_en_margin", 201) * scale))
    else:
        ko_mv = en_mv = int(round(s.get("margin_v", 96) * scale))

    fmt = ("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
           "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
           "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
           "Alignment, MarginL, MarginR, MarginV, Encoding")
    ko = (f"Style: KO,{font},{fs},{primary},{secondary},{outline_c},{back_c},"
          f"1,0,0,0,100,100,0,0,1,{outline},{shadow},2,60,60,{ko_mv},1")
    en = (f"Style: EN,{font},{int(fs*0.82)},{en_color},{en_color},{outline_c},{back_c},"
          f"0,1,0,0,100,100,0,0,1,{max(2,outline-1)},{shadow},2,60,60,{en_mv},1")
    lines = [fmt, ko, en]
    return "\n".join(lines)


def _header(cfg: dict, mode: str, title: str) -> str:
    v = cfg.get("video", {})
    w, h = v.get("resolution", [2560, 1440])
    return (
        "[Script Info]\n"
        f"Title: {title} [{mode}]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {w}\n"
        f"PlayResY: {h}\n\n"
        "[V4+ Styles]\n"
        f"{_style_block(cfg, mode)}\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def _action_tag(cfg: dict) -> str:
    a = cfg.get("subtitle", {}).get("action", {})
    fin = a.get("fade_in_ms", 250)
    fout = a.get("fade_out_ms", 250)
    pop = a.get("pop_scale", 1.06)
    p = int(pop * 100)
    # 페이드 + 부드러운 팝(살짝 커졌다 안착)
    return (f"{{\\fad({fin},{fout})"
            f"\\t(0,180,\\fscx{p}\\fscy{p})\\t(180,360,\\fscx100\\fscy100)}}")


def _karaoke_text(lt: LineTiming) -> str:
    """줄의 단어 타임스탬프를 \\kf(센티초)로 변환. 단어 사이 공백 유지."""
    if not lt.words:
        return lt.text
    parts: List[str] = []
    cursor = lt.start
    for w, ws, we in lt.words:
        gap = max(0.0, ws - cursor)
        if gap > 0.02:
            parts.append(f"{{\\k{int(round(gap*100))}}}")  # 침묵 구간 hold
        dur = max(1, int(round((we - ws) * 100)))
        parts.append(f"{{\\kf{dur}}}{w}")
        parts.append(" ")
        cursor = we
    return "".join(parts).rstrip()


# ---------------------------------------------------------------- ASS 빌더(순수함수)
def build_ass(cfg: dict, title: str, mode: str,
              ko: List[LineTiming], en: Optional[List[str]]) -> str:
    out = [_header(cfg, mode, title)]
    tag = _action_tag(cfg)

    def ev(style: str, start: float, end: float, text: str) -> str:
        return f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{tag}{text}"

    for i, lt in enumerate(ko):
        if mode in ("ko", "dual"):
            out.append(ev("KO", lt.start, lt.end, _karaoke_text(lt)))
        if mode in ("en", "dual") and en is not None and i < len(en):
            out.append(ev("EN", lt.start, lt.end, en[i]))
    return "\n".join(out) + "\n"


def write_lrc(path: Path, ko: List[LineTiming]) -> None:
    lines = []
    for lt in ko:
        m, s = divmod(lt.start, 60)
        lines.append(f"[{int(m):02d}:{s:05.2f}]{lt.text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 미리보기용 균등분할(음원/Whisper 없이)
def dummy_timings(lines: List[str], total: float = 180.0,
                  per_word: bool = True) -> List[LineTiming]:
    """음원 없이 자막 레이아웃/색 검증용. 줄·단어를 균등 분할."""
    n = max(1, len(lines))
    seg = total / n
    res: List[LineTiming] = []
    for i, ln in enumerate(lines):
        st, en = i * seg, (i + 1) * seg
        words = []
        if per_word:
            toks = ln.split()
            if toks:
                wseg = (en - st) / len(toks)
                words = [(t, st + j * wseg, st + (j + 1) * wseg) for j, t in enumerate(toks)]
        res.append(LineTiming(ln, st, en, words))
    return res


# ---------------------------------------------------------------- align.json(MMS_FA 산출) → 타이밍
def timings_from_align_json(path: Path) -> List[LineTiming]:
    """scripts/align_mms.py 가 만든 align.json(줄/단어 타임코드)을 LineTiming으로 적재.
    싱크의 단일 진실원 — 폴백(균등분할)을 대체한다."""
    data = json.loads(path.read_text(encoding="utf-8"))
    res: List[LineTiming] = []
    for L in data.get("lines", []):
        words = [(w["w"], float(w["start"]), float(w["end"])) for w in L.get("words", [])]
        res.append(LineTiming(L["ko"], float(L["start"]), float(L["end"]), words))
    return res


# ---------------------------------------------------------------- 보컬 분리 (htdemucs_ft, P0)
def separate_vocals(audio: Path, out_dir: Path, model: str = "htdemucs_ft") -> Path:
    """Demucs로 보컬 트랙 추출. 실패/미설치 시 원본 음원 경로 반환(정렬은 가능)."""
    try:
        import demucs.separate  # noqa: F401
    except ImportError:
        log.warning("demucs 미설치 — 보컬분리 생략, 원본으로 정렬")
        return audio
    sep_dir = out_dir / "_demucs"
    sep_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["python", "-m", "demucs.separate", "-n", model,
           "--two-stems", "vocals", "-o", str(sep_dir), str(audio)]
    log.info("demucs(%s) 보컬 분리…", model)
    subprocess.run(cmd, check=True)
    voc = next(sep_dir.glob(f"{model}/**/vocals.wav"), None)
    return voc if voc else audio


# ---------------------------------------------------------------- KO forced-align (WhisperX)
def align_ko(audio_for_align: Path, ko_lines: List[str], cfg: dict) -> List[LineTiming]:
    """WhisperX 단어 타임스탬프를 실제 가사 줄에 매핑. 미설치 시 균등분할 폴백."""
    a = cfg.get("align", {})
    try:
        import whisperx
    except ImportError:
        log.warning("whisperx 미설치 — 균등분할 폴백(미리보기 품질)")
        dur = _probe_dur(audio_for_align)
        return dummy_timings(ko_lines, dur)

    device = a.get("device", "cpu")
    ct = a.get("compute_type", "int8" if device == "cpu" else "float16")
    model = whisperx.load_model(a.get("whisper_model", "large-v3"), device,
                                compute_type=ct, language="ko")
    wav = whisperx.load_audio(str(audio_for_align))
    res = model.transcribe(wav, language="ko")
    amodel, meta = whisperx.load_align_model(language_code="ko", device=device)
    aligned = whisperx.align(res["segments"], amodel, meta, wav, device,
                             return_char_alignments=False)
    rec_words = [(w["word"], w.get("start"), w.get("end"))
                 for w in aligned.get("word_segments", [])
                 if w.get("start") is not None]
    return _map_words_to_lines(ko_lines, rec_words, _probe_dur(audio_for_align))


def _probe_dur(audio: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(audio)],
            capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception:  # noqa: BLE001
        return 180.0


def _map_words_to_lines(ko_lines: List[str],
                        rec: List[Tuple[str, float, float]],
                        total: float) -> List[LineTiming]:
    """인식단어열 → 실제 줄에 그리디 매핑. 빗나가도 화면엔 실제 가사."""
    if not rec:
        return dummy_timings(ko_lines, total)
    res: List[LineTiming] = []
    ri = 0
    for line in ko_lines:
        target = line.replace(" ", "")
        consumed: List[Tuple[str, float, float]] = []
        acc = ""
        # 줄 길이만큼 인식단어를 소비(difflib로 과소비 방지)
        while ri < len(rec) and len(acc) < len(target):
            w, ws, we = rec[ri]
            nxt = acc + w.replace(" ", "")
            if len(nxt) > len(target) * 1.4 and consumed:
                break
            consumed.append((w, ws, we))
            acc = nxt
            ri += 1
        if consumed:
            st, en = consumed[0][1], consumed[-1][2]
            # 표시 단어는 실제 가사 토큰에 인식 타임스탬프를 균등 재배치
            toks = line.split()
            if toks:
                wseg = (en - st) / len(toks)
                words = [(t, st + j * wseg, st + (j + 1) * wseg) for j, t in enumerate(toks)]
            else:
                words = []
            res.append(LineTiming(line, st, en, words))
        else:
            # 인식 소진 → 이후 줄은 균등 분할로 채움
            res.append(LineTiming(line, total, total + 0.01, []))
    return res


# ---------------------------------------------------------------- 단계 진입점
def run(ctx: Context) -> Context:
    cfg = ctx.cfg
    a = cfg.get("align", {})
    ko_lines = read_lyric_lines(ctx.lyrics_ko)
    en_lines = read_lyric_lines(ctx.lyrics_en) if ctx.lyrics_en and ctx.lyrics_en.exists() else None

    # 1순위: scripts/align_mms.py 가 남긴 align.json(실제 forced-align) — 폴백 대체
    align_json = ctx.out_dir / "align.json"
    if align_json.exists():
        ko_t = timings_from_align_json(align_json)
        if len(ko_t) != len(ko_lines):
            log.warning("align.json 줄수(%d) ≠ lyrics_ko 줄수(%d) — align.json 텍스트 기준 사용",
                        len(ko_t), len(ko_lines))
        log.info("align.json 사용: %s (MMS_FA 타임코드, %d줄)", align_json, len(ko_t))
    else:
        src = ctx.audio
        if a.get("use_demucs", True) and ctx.audio.exists():
            src = separate_vocals(ctx.audio, ctx.out_dir, a.get("demucs_model", "htdemucs_ft"))
        ko_t = align_ko(src, ko_lines, cfg) if ctx.audio.exists() else dummy_timings(ko_lines)

    # offset 보정
    off = a.get("offset_ms", 0) / 1000.0
    if off:
        for lt in ko_t:
            lt.start += off
            lt.end += off
            lt.words = [(w, ws + off, we + off) for w, ws, we in lt.words]

    modes = cfg.get("subtitle", {}).get("modes", ["dual"])
    for mode in modes:
        ass = build_ass(cfg, ctx.title, mode, ko_t, en_lines)
        p = ctx.out_dir / f"{ctx.track_dir.name}_{mode}.ass"
        p.write_text(ass, encoding="utf-8")
        ctx.ass_map[mode] = p
        log.info("ASS 생성: %s", p)

    lrc = ctx.out_dir / f"{ctx.track_dir.name}.lrc"
    write_lrc(lrc, ko_t)
    ctx.lrc = lrc
    return ctx
