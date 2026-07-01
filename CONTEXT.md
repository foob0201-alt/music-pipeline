# CONTEXT — 프로젝트 현재 상태 (세션 인계)

> 하데스 §2.3(이전 대화 세세히 기억)을 파일로 고정한 **살아있는 상태 문서**.
> 새 세션은 이 문서를 먼저 읽고, 불확실하면 과거 대화를 검색해 보강한다.
> 위계: HADES.md → **AGENTS.md**(팀헌장) → PLAN.md → **CONTEXT.md** → README.md.
_최종 갱신: 2026-07-01 — 「그렇게 지나간다」 완주·발행패키지, 「동해로」 마스터, upload_scheduler·커버 승인게이트 도입_

## 1. 한 줄 요약
**「그렇게 지나간다」(geureoke) 마스터 완주 + 발행 패키지 준비 완료.** 확정 커버(FLUX.2 배경 Soft Grain Analog 사계절 순환)로 재인코딩, ffprobe 9/9 PASS, 자막 싱크 검증, `youtube_description.txt`(제목·설명·태그) 작성. **「동해로」(donghae)도 실음원 교체 후 마스터 완주.** 곡 단위 수동 업로드 도구 `upload_scheduler.py` 신설, 커버 승인 게이트(`.cover_ok`)·config 기반 커버 제목 오버라이드 도입.
(이전: 「아무말도」·「봄날」 마스터 완주·검증, 파이프라인 실가동, git 도입.)

## 2. 빌드된 것 (누적)
| 파일 | 상태 |
|---|---|
| `hades_util.py` (설정·컨텍스트·매니페스트·재시도·시크릿·**cover 승인/게이트**) | ✅ |
| `preflight.py` / `align.py`(MMS_FA) / `make_video.py`(커버게이트→1440p) | ✅ 검증 |
| `pipeline.py` (오케스트레이터·의존성 자동보강) | ✅ |
| `cover_render.py` (코드 제너러티브 + **fal 배경 color_field** + **config 제목 오버라이드**) | ✅ |
| `hades/fal_bg.py` (FLUX.2 배경 생성, FAL_KEY 환경변수) | ✅ |
| `scripts/align_mms.py` (torchaudio MMS_FA forced-align → align.json) | ✅ |
| `upload_youtube.py` / `post_threads.py` (버전별·재시도·멱등) | ✅ 코드 |
| **`upload_scheduler.py`** (곡 단위 수동 업로드·일일캡1·매니페스트·설명파싱) | ✅ 신설·dry-run 검증 |
| `.venv-align` (torch·torchaudio·yaml·PIL·fal·uroman — **정렬/커버 실행 인터프리터**) | ✅ |

## 3. 확정 결정 (네비게이터 최종)
- 포맷: **가로 1440p**(2560×1440) · 발행 모드 **dual**(KO 위 노랑 카라오케 + EN 아래 크림).
- 화질: H.264 High · yuv420p · bt709 · +faststart · AAC 48k · CRF16 1-pass(정적 커버+자막).
- **커버 승인 게이트**: `tracks/<slug>/out/.cover_ok`(cover.jpg sha256)가 일치해야 video 인코딩 진행. 승인=`approve_cover(slug)`.
- **커버 제목 오버라이드**(config.yaml, cover_render 반영): `title_ko_scale`·`title_en_gap`·`title_en_scale`.
- **발행은 수동 전용** — `youtube.enabled` 자동 배선 금지. 계정 **reina2hj@gmail.com**. `upload_scheduler.py`는 사용자가 직접 실행(대화형 OAuth).

## 4. 곡 이력
| 곡 | 장소/컨셉 | 장르 | 상태 |
|---|---|---|---|
| 아무말도 | 놀이터 벤치·여름밤 | 업템포 일렉트로-R&B | 마스터 완주·검증 |
| 봄날 | 그 봄날의 방·여름비 재회 | future soul | 마스터 완주·검증 |
| 거울 속의 오늘 | 거울 앞·잔상 | mirror afterimage R&B | 렌더 산출물 有 |
| 동해로 | 올림픽대로 여름 로드트립 | R&B | **마스터 완주**(실음원 210.8s 교체 후 재정렬·재렌더) |
| **그렇게 지나간다** | 사계절 순환=인내(장소 은유 아님) | smooth urban R&B ~90 BPM +gospel | **완주+발행패키지 준비**(음원 169.76s·커버 확정·9/9 PASS) |
| 관람차 (월미도) | 밤바다·관람차 순환 | 네오소울 R&B | **보류/격리**(작업트리에서 제거 → `_archive_*`/휴지통, git 미추적) |

## 5. 사용자 선호 / 작업 방식
- **존댓말** 필수. 간결·직접(짧은 말 → 전체 패키지).
- 미학: 간접 표현(감각·물성·동작), **장소=감정 은유**(또는 계절 은유), **수미상관**, 곡마다 차별화.
- 장르는 레퍼런스로 호명 → 즉시 적용. Suno: 영어 섹션 태그·영어 애드립.
- Windows PS 5.1 `Get-Content|Set-Content`는 한글(UTF-8) 파일을 cp949로 왕복해 **손상** → 편집은 UTF-8 안전 방식만.

## 6. 미결정 / 보류
- 관람차: 보류(격리됨). 재개 시 `_archive_*`/휴지통에서 복구.
- geureoke 실제 YouTube 업로드: 사용자가 `upload_scheduler.py` 직접 실행(client_secret 준비 + OAuth 필요).
- 리서처·배포 에이전트, P2/P3 천장 기능: 후속.

## 7. 지금 당장 다음 액션
1. geureoke 발행: `.venv-align/Scripts/python.exe upload_scheduler.py --track geureoke` (사용자 직접, 대화형 OAuth). client_secret 없으면 안내 출력.
2. 업로드 후 `upload_manifest.json`(video_id·url) 확인 → CONTEXT 곡 이력 갱신.
3. 다음 곡 착수(원재료 수령 시): 가사→커버(fal 배경+승인)→align_mms→align,video→발행패키지.
