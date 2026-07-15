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
# 청크 모드(장곡 OOM 회피): --chunk-sec N → 무음경계에서 분할, 청크별 forward emission을
# 전역 프레임 오프셋으로 병합 후 전체 transcript로 1회 정렬(align.json 스키마 불변).
# 0=풀패스(기존 동작, 회귀 위험 없음). 무음(RMS 저점 ≥0.5s)에서만 컷 → 가사 줄 미분할.
CHUNK_SEC = 0.0
if "--chunk-sec" in sys.argv:
    CHUNK_SEC = float(sys.argv[sys.argv.index("--chunk-sec") + 1])
elif "--chunk" in sys.argv:
    CHUNK_SEC = 40.0
# 하이브리드(2026-07-15 Navigator 승인): 청크는 풀패스 OOM 회피용 폴백 전용.
# 오디오가 FULLPASS_MAX 이하면 --chunk-sec 지정돼도 풀패스(반복 후렴 ±0.3s 정확).
# 초과(장곡 OOM 위험)만 청크. → owol(175s) 풀패스=회귀 자동통과 / ganda(258s) 청크.
FULLPASS_MAX = 220.0
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


def _silence_cuts(data, sr, min_sil=0.5, win=0.05, low_pct=12):
    """무음(RMS 저점 ≥min_sil초) 구간의 중앙 샘플 인덱스 — 청크 컷 후보(가사 줄 미분할)."""
    hop = max(1, int(sr * win))
    rms = np.array([float(np.sqrt(np.mean(data[i:i+hop] ** 2)) if len(data[i:i+hop]) else 0.0)
                    for i in range(0, len(data), hop)])
    thr = np.percentile(rms, low_pct)
    silent = rms < thr
    need = max(1, int(min_sil / win))
    cuts, run = [], None
    for i, s in enumerate(silent):
        if s and run is None:
            run = i
        elif not s and run is not None:
            if i - run >= need:
                cuts.append(((run + i) // 2) * hop)
            run = None
    if run is not None and len(silent) - run >= need:
        cuts.append(((run + len(silent)) // 2) * hop)
    return cuts


def _chunk_ranges(n, sr, cuts, target_sec):
    """무음 컷에서만 분할해 ~target_sec 청크 범위 생성(고정길이 금지). 무음 없으면 이어붙임."""
    target = int(target_sec * sr)
    cuts = sorted(cuts)
    ranges, start = [], 0
    while start < n:
        if start + target >= n:
            ranges.append((start, n)); break
        ideal = start + target
        cand = [c for c in cuts if start + int(target * 0.4) <= c <= start + int(target * 1.6)]
        cut = min(cand, key=lambda c: abs(c - ideal)) if cand else min(n, ideal)
        if cut <= start:
            cut = min(n, start + target)
        ranges.append((start, cut)); start = cut
    return ranges


def _emission_chunked(model, waveform, sr, target_sec, device):
    """무음경계 청크별 forward → 프레임축 병합(전역 오프셋). 풀패스 OOM 회피, 결과는 전역 동일."""
    data = waveform[0].cpu().numpy()
    cuts = _silence_cuts(data, sr)
    ranges = _chunk_ranges(len(data), sr, cuts, target_sec)
    ems = []
    for a, b in ranges:
        with torch.inference_mode():
            e, _ = model(waveform[:, a:b].to(device))
        ems.append(e.cpu())
    return torch.cat(ems, dim=1), ranges


def _spans_to_wt(spans, ratio, offset_sec=0.0):
    """token_spans(단어별 리스트) → 단어별 (t0,t1,score) 전역 초. transcript 순서."""
    out = []
    for sp in spans:
        t0 = ratio * sp[0].start / SR + offset_sec
        t1 = ratio * sp[-1].end / SR + offset_sec
        dur = max(1, sum(s.end - s.start for s in sp))
        sc = sum(s.score * (s.end - s.start) for s in sp) / dur
        out.append((t0, t1, float(sc)))
    return out


word_times = [None] * len(transcript)        # meta 순서 단어별 (t0,t1,score)
try:
    if CHUNK_SEC > 0 and total_sec <= FULLPASS_MAX:
        print("[하이브리드] %.1fs ≤ %.0fs → 청크 지정됐지만 풀패스 사용(반복 후렴 정확)."
              % (total_sec, FULLPASS_MAX))
    if CHUNK_SEC > 0 and total_sec > FULLPASS_MAX:
        # ── 청크 align v2: 오버랩 청크 포워드(OOM 회피, 이음새 무결) + 적응 star 2패스 ──
        # OOM은 '모델 포워드'에서만 난다(258s ~1.7GB). 이를 피하되 정렬은 풀패스와
        # 동일해야 한다. 두 축으로 해결:
        #  (A) 오버랩 포워드: 각 청크를 ±PAD 여유로 forward 후 코어 프레임만 잘라 병합
        #      → 이음새 프레임을 이웃 문맥이 있는 프레임으로 대체 → concat emission이
        #      풀패스 emission에 근접(경계 아티팩트 제거).
        #  (B) 적응 star: 라인마다 star를 넣으면 짧은 전환이 애매해져 밀리고, star가
        #      전무하면 긴 간주가 가사를 강제 흡수해 드리프트한다. 그래서 1패스(라인마다
        #      star)로 큰 간주(>GAP_STAR)만 찾고, 2패스에서 앞뒤 + 큰 간주에만 star를
        #      넣어 정렬 → 짧은 전환은 풀패스처럼 타이트, 긴 간주는 star가 흡수.
        # aligner는 같은 emission에 2회(초 단위)뿐 — 포워드는 1회.
        import ctypes
        def _peak_mb():
            try:
                class _PMC(ctypes.Structure):
                    _fields_ = [("cb", ctypes.c_ulong), ("pfc", ctypes.c_ulong),
                                ("pws", ctypes.c_size_t), ("ws", ctypes.c_size_t),
                                ("qppp", ctypes.c_size_t), ("qpp", ctypes.c_size_t),
                                ("qpnpp", ctypes.c_size_t), ("qpnp", ctypes.c_size_t),
                                ("pfu", ctypes.c_size_t), ("ppfu", ctypes.c_size_t)]
                k = ctypes.windll.kernel32
                k.GetCurrentProcess.restype = ctypes.c_void_p    # 64bit 핸들 절단 방지
                c = _PMC(); c.cb = ctypes.sizeof(c)
                ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                    ctypes.c_void_p(k.GetCurrentProcess()), ctypes.byref(c), c.cb)
                return c.pws / 1e6 if ok else -1.0           # PeakWorkingSetSize
            except Exception:
                return -1.0

        PAD = 32000        # 오버랩 여유(2s) — 수용영역 충분(8s 실험도 반복밀림 개선 無)
        FR = 320           # 샘플/프레임(stride) — 코어 프레임 범위 환산용
        GAP_STAR = 4.0     # 이 이상의 무가사 간주 경계에만 star 삽입(짧은 전환은 제외)
        N = len(ko_lines)
        data = waveform[0].cpu().numpy()
        cuts = sorted(_silence_cuts(data, SR))
        ranges = _chunk_ranges(len(data), SR, cuts, max(CHUNK_SEC, 40.0))
        # (A) 오버랩 포워드 → 코어 프레임만 병합(이음새 아티팩트 제거)
        cores = []
        for a, b in ranges:
            sa = max(0, a - PAD); sb = min(len(data), b + PAD)
            with torch.inference_mode():
                e, _ = model(waveform[:, sa:sb].to(device))
            e = e.cpu()
            T = e.size(1)
            j0 = 0 if a == 0 else max(0, min(T, round((a - sa) / FR)))
            j1 = T if b == len(data) else max(j0, min(T, round((b - sa) / FR)))
            cores.append(e[:, j0:j1, :])
        emission = torch.cat(cores, dim=1); del cores
        ratio = waveform.size(1) / emission.size(1)

        def _align_stars(bound_set):
            """bound_set 라인 경계 앞 + 앞/뒤에 star 삽입해 정렬 → word별 (t0,t1,sc)."""
            sk, cur = [None], None                    # head star
            for k, (li, surf) in enumerate(meta):
                if cur is not None and li != cur and li in bound_set:
                    sk.append(None)
                cur = li
                sk.append(k)
            sk.append(None)                           # tail star
            w = ["*" if x is None else transcript[x] for x in sk]
            wtt = _spans_to_wt(aligner(emission[0], tokenizer(w)), ratio)
            out = [None] * len(transcript)
            for pos, x in enumerate(sk):
                if x is not None:
                    out[x] = wtt[pos]
            return out

        # (B) 1패스: 라인마다 star → 라인 시작/끝 → 큰 간주(>GAP_STAR) 경계 탐지
        wtA = _align_stars(set(range(1, N)))
        lsA = [1e9] * N; leA = [-1.0] * N
        for k, (li, surf) in enumerate(meta):
            t0, t1, _ = wtA[k]
            lsA[li] = min(lsA[li], t0); leA[li] = max(leA[li], t1)
        big = set(li for li in range(1, N)
                  if lsA[li] < 1e8 and leA[li - 1] > -1 and lsA[li] - leA[li - 1] > GAP_STAR)
        # (B) 2패스: 앞/뒤 + 큰 간주 경계에만 star(짧은 전환은 풀패스처럼 타이트) → 최종
        wtB = _align_stars(big)
        for k in range(len(transcript)):
            word_times[k] = wtB[k] if wtB[k] is not None else wtA[k]
        del emission
        print("[청크] 오버랩forward %d청크(%s) PAD=%.0fs | 큰간주>%.0fs 경계: %s | 피크 %.0fMB" % (
            len(ranges), ", ".join("%.0f-%.0fs" % (a / SR, b / SR) for a, b in ranges),
            PAD / SR, GAP_STAR, sorted(l + 1 for l in big), _peak_mb()))
    else:
        with torch.inference_mode():
            emission, _ = model(waveform.to(device))
            token_spans = aligner(emission[0], tokenizer(transcript))
        word_times = _spans_to_wt(token_spans, waveform.size(1) / emission.size(1))
except RuntimeError as e:
    print(f"[ERR] 정렬 실패(메모리 가능성): {e}")
    print("      → 풀패스 OOM이면 --chunk-sec 35 로 재시도(무음경계 청크 분할).")
    sys.exit(4)

assert len(word_times) == len(transcript), "토큰/단어 수 불일치"

# 단어 → 줄 집계
lines = [{"idx": i, "ko": ko_lines[i], "start": None, "end": None, "words": []}
         for i in range(len(ko_lines))]
for k, (li, surf) in enumerate(meta):
    t0, t1, sc = word_times[k]
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

# ----- 4.5 병합 검증 (라인수 일치 · 단조증가 · 청크경계 >10s 이상치 없음) --------
_n = len(lines)
_mono = all(lines[i]["start"] >= lines[i-1]["start"] for i in range(1, _n))
_gaps = [(i, round(lines[i]["start"] - lines[i-1]["end"], 2))
         for i in range(1, _n) if lines[i]["start"] - lines[i-1]["end"] > 10]
print("[검증] 라인 %d/%d  단조증가=%s  >10s간격=%d%s" %
      (_n, len(ko_lines), _mono, len(_gaps), (" %s" % _gaps) if _gaps else ""))
if _n != len(ko_lines):
    print("[WARN] 라인수 불일치 — align.json 확인 필요")

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
