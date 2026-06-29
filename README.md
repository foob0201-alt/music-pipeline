# HADES 음악 파이프라인 — README

> 위계: **HADES.md**(헌장·원칙·아키텍처) → **PLAN.md**(마일스톤) → **CONTEXT.md**(지금 상태) → **README.md**(실행).

가사(KO/EN) → 액션 자막 영상(1440p) → YouTube·Threads 자동 발행.
Suno 음원 다운로드만 수동, 나머지는 `python pipeline.py --steps all` 한 줄.

---

## 1. 설치 (최초 1회)

### 시스템
- Python 3.10+
- ffmpeg (`sudo apt install ffmpeg` / `brew install ffmpeg`)
- 한글 폰트: `sudo apt install fonts-noto-cjk`

### 파이썬
```bash
pip install -r requirements.txt
# torch는 플랫폼별 설치 권장:
#   CPU:  pip install torch torchaudio
#   CUDA: https://pytorch.org (cu12x 휠)
```
> GPU가 있으면 WhisperX/Demucs가 수십 배 빠릅니다. CPU만 있으면
> `config.yaml`의 `align.device: cpu`, `compute_type: int8`, `whisper_model: medium` 권장.

---

## 2. 곡 폴더 준비

`tracks/_template/`을 복사해 `tracks/<곡명>/`을 만들고 다음을 채웁니다.

| 파일 | 설명 |
|---|---|
| `audio.mp3` | Suno에서 내려받은 음원 |
| `lyrics_ko.txt` | 한글 가사(한 줄=자막 한 줄, `[Verse]` 등 섹션줄은 자동 제외) |
| `lyrics_en.txt` | 영어 가사(KO와 **줄 수 1:1**) |
| `cover.jpg` | 커버(1440p 권장) — `scripts/make_cover.py`로 생성 가능 |
| `config.yaml` | (선택) 곡별 설정. 루트 `config.yaml` 위에 병합됨 |

커버 헬퍼:
```bash
python scripts/make_cover.py --title "관람차" --subtitle "월미도" \
    --out tracks/gwanramcha/cover.jpg --top 0a1428 --bottom 1b3a5f
```

---

## 3. 실행

```bash
# 자막만 먼저 뽑아 타이밍 확인(권장)
python pipeline.py --track tracks/gwanramcha/config.yaml --steps align

# 영상 합성(자막 없으면 align 자동 선행)
python pipeline.py --track tracks/gwanramcha/config.yaml --steps video

# 전체 (align→video→upload→threads)
python pipeline.py --track tracks/gwanramcha/config.yaml --steps all
```

산출물: `tracks/<곡>/out/<곡>_<모드>.{ass,mp4}`, `<곡>.lrc`, `manifest.json`.

### 자막이 밀릴 때
`config.yaml`의 `align.offset_ms`로 전체를 +/- 이동(예: `-150`).

---

## 4. 업로드 권한 (최초 1회)

### YouTube (무료, 하루 ~6건)
1. Google Cloud Console → 프로젝트 생성 → **YouTube Data API v3** 사용설정
2. OAuth 동의화면 구성 + 본인 계정 테스트 사용자 추가
3. 데스크톱 OAuth 클라이언트 → JSON을 `client_secret.json`으로 저장
4. 첫 업로드 시 브라우저 로그인 → `token.json` 자동 생성·재사용
5. `config.yaml`에서 `youtube.enabled: true`, `privacy`(처음엔 `unlisted` 권장)

### Threads (무료, 본인 계정 검수 불요)
- Meta 개발자 앱에서 장기 액세스 토큰 발급 → `threads_token.json` 저장
- `config.yaml`에서 `threads.enabled: true`, `user_id` 입력

> 크레덴셜·토큰은 `.gitignore`로 차단되며 실행 시 권한 600으로 강제됩니다.

---

## 5. 검증

```bash
python scripts/selftest.py    # 음원 없이 자막엔진(KO 채움+EN 색분리) 픽셀검증
```

---

## 6. 파일 구성

| 파일 | 역할 | 구분 |
|---|---|---|
| `pipeline.py` | 단계 오케스트레이션 | 실행 |
| `align.py` | 보컬분리·정렬·ASS/LRC 생성 | 실행 |
| `make_video.py` | Ken Burns + 자막 + 2-pass 인코딩 | 실행 |
| `upload_youtube.py` | YouTube 버전별 업로드 | 실행 |
| `post_threads.py` | Threads 게시 | 실행 |
| `preflight.py` | 선행조건 검증(P0) | 실행 |
| `hades_util.py` | 설정·컨텍스트·매니페스트·재시도·시크릿 | 실행 |
| `config.yaml` | 모든 파라미터 | 설정 |
| `scripts/` | 커버 생성·셀프테스트 | 보조 |
