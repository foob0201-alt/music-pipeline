#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scripts/align_mms.py — HADES 정렬 실행자 (네비게이터 설계)
# ---------------------------------------------------------------------------
# 가사 보유 → torchaudio MMS_FA 직접 CTC forced-align (전사/보컬분리 생략).
# 한국어는 uroman 로마자화로 모델 사전에 매칭, <star> 토큰으로 무음/간주 흡수해
# 균등분할 폴백의 누적 드리프트를 제거한다.
#
#   입력 : tracks/<track>/<track>.mp3  (config.yaml paths.audio 우선, 레거시 audio.mp3 폴백)
#          tracks/<track>/lyrics_ko.txt   (섹션태그 [..] / 공백줄은 자동 제외)
#   출력 : tracks/<track>/out/align.json          ← 싱크의 단일 진실원(줄/단어 타임코드)
#          tracks/<track>/out/_align_preview.lrc   ← 음원과 같이 틀어 육안 검증(렌더 불필요)
#
# 실행 : (.venv-align 의 python 으로) python scripts/align_mms.py <track>
#   예 : .venv-align\Scripts\python scripts\align_mms.py amumaldo
#
# 역할 경계(HADES §2.1): 실행자는 받아 실행만. 정렬 로직/파라미터는 네비게이터 결정.
# ---------------------------------------------------------------------------

import sys, os, re, json, subprocess, tempfile
from pathlib import Path

import torch
import torchaudio
import soundfile as sf
import numpy as np

SR = 16000  # MMS_FA bundle.sample_rate

# ----- 0. 인자 / 경로 ------------------------------------------------------
if len(sys.argv) < 2:
    print("usage: python scripts/align_mms.py <track_name>")
    sys.exit(1)
TRACK = sys.argv[1]
ROOT  = Path(__file__).resolve().parents[1]          # scripts/ 의 상위 = repo 루트
TDIR  = ROOT / "tracks" / TRACK

def _resolve_audio(tdir: Path, track: str) -> Path:
    """음원 경로 해석: config.yaml paths.audio → <slug>.mp3 → 레거시 audio.mp3(경고)."""
    cfg_name = None
    cfgp = tdir / "config.yaml"
    if cfgp.exists():
        try:
            import yaml
            c = yaml.safe_load(cfgp.read_text(encoding="utf-8")) or {}
            cfg_name = (c.get("paths") or {}).get("audio")
        except Exception:
            cfg_name = None
    for name in ([cfg_name] if cfg_name else []) + [f"{track}.mp3"]:
        p = tdir / name
        if p.exists():
            return p
    legacy = tdir / "audio.mp3"
    if legacy.exists():
        print(f"[warn] 레거시 파일명 audio.mp3 사용 — 표준 명은 {track}.mp3")
        return legacy
    return tdir / f"{track}.mp3"

AUDIO = _resolve_audio(TDIR, TRACK)
LYRKO = TDIR / "lyrics_ko.txt"
OUT   = TDIR / "out"; OUT.mkdir(parents=True, exist_ok=True)

for p in (AUDIO, LYRKO):
    if not p.exists():
        print(f"[ERR] 파일 없음: {p}"); sys.exit(2)

torch.set_num_threads(os.cpu_count() or 4)
device = torch.device("cpu")

# ----- 1. 가사 파싱 (섹션태그/공백 제외, 본문 줄만) -------------------------
def load_lines(path: Path):
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("[") and s.endswith("]"):     # [Verse 1] / [Chorus] 등 섹션태그
            continue
        out.append(s)
    return out

ko_lines = load_lines(LYRKO)
print(f"[i] KO 본문 줄수: {len(ko_lines)}")

# ----- 2. 로마자화 (MMS는 uroman 학습 → uroman으로 매칭) --------------------
def make_romanizer():
    # (a) 공식 uroman 파이썬 패키지 — 모델 학습과 동일 계열
    try:
        import uroman as _ur
        u = _ur.Uroman()
        return lambda t: u.romanize_string(t, lcode="kor")
    except Exception:
        pass
    # (b) uroman-fast (Rust)
    try:
        from uroman_fast import romanize as _rf
        return lambda t: _rf(t, lang="kor")
    except Exception:
        pass
    # (c) CLI 폴백
    def _cli(t):
        r = subprocess.run([sys.executable, "-m", "uroman", t, "-l", "kor"],
                           capture_output=True, text=True, encoding="utf-8")
        return (r.stdout or "").strip()
    return _cli

romanize = make_romanizer()

def normalize(word: str) -> str:
    """uroman → 소문자 → 사전 외 문자 제거 (a-z 만 유지)."""
    return re.sub(r"[^a-z]", "", romanize(word).lower())

# 단어 단위로 펼치되, 어떤 줄에 속한 단어인지 기록 (transcript[i] ↔ meta[i])
transcript, meta = [], []
for li, line in enumerate(ko_lines):
    for surf in line.split():
        nw = normalize(surf)
        if not nw:                      # 순수 문장부호 등은 정렬 토큰에서 제외
            continue
        transcript.append(nw)
        meta.append((li, surf))

if not transcript:
    print("[ERR] 로마자화 결과가 비었습니다 — uroman 설치 확인 "
          "(.venv-align\\Scripts\\python -m pip install uroman)")
    sys.exit(3)
print(f"[i] 정렬 토큰(단어) 수: {len(transcript)}")

# ----- 3. 오디오 16k 모노 디코드 (ffmpeg→wav→soundfile; mp3 백엔드 회피) ----
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, "a16k.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(AUDIO),
                    "-ac", "1", "-ar", str(SR), "-f", "wav", wav], check=True)
    data, sr = sf.read(wav, dtype="float32")
if data.ndim > 1:
    data = data.mean(axis=1)
assert sr == SR, f"resample 실패: {sr}"
waveform = torch.from_numpy(np.ascontiguousarray(data)).unsqueeze(0)   # [1, N]
total_sec = waveform.size(1) / SR
print(f"[i] audio: {total_sec:.2f}s @ {SR} mono")

# ----- 4. MMS_FA forced-align ---------------------------------------------
from torchaudio.pipelines import MMS_FA as bundle
print("[i] MMS_FA 로드 (최초 1회 ~1.2GB 다운로드 후 캐시)…")
model     = bundle.get_model(with_star=True).to(device)
tokenizer = bundle.get_tokenizer()
aligner   = bundle.get_aligner()

try:
    with torch.inference_mode():
        emission, _ = model(waveform.to(device))
        token_spans = aligner(emission[0], tokenizer(transcript))
except RuntimeError as e:
    # CPU 메모리 부족 시: 풀패스 실패 → 보고 후 청크 버전으로 전환
    print(f"[ERR] 정렬 실패(메모리 가능성): {e}")
    print("      → 이 로그를 네비게이터에게 전달하면 청크 분할 버전으로 교체합니다.")
    sys.exit(4)

num_frames = emission.size(1)
ratio = waveform.size(1) / num_frames               # samples per emission frame

def to_sec(spans):
    t0 = ratio * spans[0].start / SR
    t1 = ratio * spans[-1].end / SR
    dur = max(1, sum(s.end - s.start for s in spans))
    sc  = sum(s.score * (s.end - s.start) for s in spans) / dur
    return t0, t1, float(sc)

assert len(token_spans) == len(transcript), "토큰/단어 수 불일치"

# 단어 → 줄 집계
lines = [{"idx": i, "ko": ko_lines[i], "start": None, "end": None, "words": []}
         for i in range(len(ko_lines))]
for (li, surf), spans in zip(meta, token_spans):
    t0, t1, sc = to_sec(spans)
    L = lines[li]
    L["words"].append({"w": surf, "start": round(t0, 3), "end": round(t1, 3),
                       "score": round(sc, 3)})
    L["start"] = t0 if L["start"] is None else min(L["start"], t0)
    L["end"]   = t1 if L["end"]   is None else max(L["end"],   t1)

# 단어가 안 잡힌 줄(이론상 없음) 이웃 사이로 보간
for i, L in enumerate(lines):
    if L["start"] is None:
        prev = next((lines[j]["end"]   for j in range(i-1, -1, -1)        if lines[j]["end"]   is not None), 0.0)
        nxt  = next((lines[j]["start"] for j in range(i+1, len(lines))    if lines[j]["start"] is not None), total_sec)
        L["start"], L["end"] = prev, nxt

# 줄 시작 단조 증가 보정 (역전/겹침 방지)
for i in range(1, len(lines)):
    if lines[i]["start"] < lines[i-1]["start"]:
        lines[i]["start"] = lines[i-1]["start"]
    if lines[i]["end"] < lines[i]["start"]:
        lines[i]["end"] = min(total_sec, lines[i]["start"] + 0.5)

for L in lines:
    L["start"] = round(L["start"], 3)
    L["end"]   = round(L["end"], 3)

# ----- 5. 저장: align.json + 미리보기 LRC ----------------------------------
(OUT / "align.json").write_text(json.dumps(
    {"track": TRACK, "duration": round(total_sec, 3),
     "method": "torchaudio MMS_FA (uroman, with_star)",
     "n_lines": len(lines), "lines": lines},
    ensure_ascii=False, indent=2), encoding="utf-8")

def lrc_ts(t):
    m = int(t // 60); s = t - 60 * m
    return f"[{m:02d}:{s:05.2f}]"

(OUT / "_align_preview.lrc").write_text(
    "\n".join(lrc_ts(L["start"]) + L["ko"] for L in lines) + "\n",
    encoding="utf-8")

print(f"[OK] {OUT/'align.json'}")
print(f"[OK] {OUT/'_align_preview.lrc'}  ← 음원과 같이 재생해 줄 타이밍 육안 확인")
print("\n=== 처음 8줄 미리보기 ===")
for L in lines[:8]:
    print(f"  {L['start']:7.2f} - {L['end']:7.2f}   {L['ko']}")
