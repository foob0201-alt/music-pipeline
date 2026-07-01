# CONTEXT — 프로젝트 현재 상태 (세션 인계)

> 하데스 §2.3(이전 대화 세세히 기억)을 파일로 고정한 **살아있는 상태 문서**.
> 새 세션은 이 문서를 먼저 읽고, 불확실하면 과거 대화를 검색해 보강한다.
> 위계: HADES.md → **AGENTS.md**(팀헌장) → PLAN.md → **CONTEXT.md** → README.md.
> 이 파일이 유일한 CONTEXT 원본이다(과거 CONTEXT2·CONTEXT3·CONTEXT (n).md는 여기로 병합·폐기).
_최종 갱신: 2026-07-01 — geureoke 완주·발행패키지, 동해로 마스터, upload_scheduler·커버 승인게이트 도입, CONTEXT3 병합(정책 리서치·충돌 플래그·Shorts·규율 교훈)_

## 1. 한 줄 요약
**「그렇게 지나간다」(geureoke) 마스터 완주 + 발행 패키지 준비 완료.** 확정 커버(FLUX.2 Soft Grain Analog 사계절 순환)로 재인코딩, ffprobe 9/9 PASS, 자막 싱크 검증, `youtube_description.txt`(제목·설명·태그) 작성. **「동해로」(donghae)도 실음원 교체 후 마스터 완주.** 곡 단위 업로드 도구 `upload_scheduler.py` 신설(사용자 트리거·일일캡·매니페스트), 커버 승인 게이트(`.cover_ok`)·config 기반 커버 제목 오버라이드 도입.
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
| **`upload_scheduler.py`** (곡 단위 업로드·일일캡1·매니페스트·설명파싱) | ✅ 신설·dry-run 검증 |
| `.venv-align` (torch·torchaudio·yaml·PIL·fal·uroman — **정렬/커버 실행 인터프리터**) | ✅ |
| 훅: cover_gate / secret_guard(FAL_KEY·fal) / danger_guard (settings.json 공유) | ✅ Live |
| `pipeline.py --auto` 전체체인 / 오디오 정체성 preflight / `make_shorts.py` | ⬜ 미빌드 |

## 3. 확정 결정 (네비게이터 최종)
- 포맷: **가로 1440p**(2560×1440) · 발행 모드 **dual**(KO 위 노랑 카라오케 + EN 아래 크림).
- 화질(확정): **H.264 High · yuv420p · BT.709 tv · CRF16 · 1-pass · preset medium · 30fps · AAC 48k ~380k · +faststart(moov@front)**. (정적 커버+자막이라 2-pass와 화질 동등·시간 ½.) ※ HADES.md §4.3의 2-pass/60fps/preset-slow은 **구스펙** — §9 참조.
- 자막: Malgun Gothic · KO 골드 `&H0000D7FF` · EN 크림 `&H00BED7DC` · margin 315(KO)/201(EN) · gap 114 · PlayRes 2560×1440.
- 정렬: **torchaudio MMS_FA**(uroman) 단일 진실원 `align.json`. (Demucs→WhisperX 경로는 폐기.)
- **커버 승인 게이트**: `tracks/<slug>/out/.cover_ok`(cover.jpg sha256) 일치해야 video 인코딩 진행. 승인=`approve_cover(slug)`. 재렌더마다 재승인(캐리오버 없음).
- **커버 제목 오버라이드**(config.yaml→cover_render 반영): `title_ko_scale`·`title_en_gap`·`title_en_scale`.
- **발행 정합(중요)**: 파이프라인 **자동 배포는 끈다**(`youtube.enabled` 자동 배선 금지). 업로드는 **`upload_scheduler.py`를 사용자가 직접 실행**(대화형 OAuth 1회)하는 경로로 통일 — 즉 "파이프라인 자동발사 금지 + 스케줄러 통한 사용자 트리거 업로드". 계정 **reina2hj@gmail.com**.

## 4. 곡 이력 / 큐
| 곡 | 장소·컨셉 | 장르 | 상태 |
|---|---|---|---|
| 아무말도 | 놀이터 벤치·여름밤 | 업템포 일렉트로-R&B | 마스터 완주·검증. 업로드 대기(캡 준수) |
| 봄날 | 그 봄날의 방·여름비 재회 | future soul | 마스터 완주·검증. 업로드 대기 |
| 거울 속의 오늘 (geoul_oneul) | 거울 앞·잔상 | mirror afterimage R&B | **CLOSED 골든레퍼런스 — 건드리지 말 것** |
| 동해로 | 올림픽대로 여름 로드트립 | R&B | **마스터 완주**(실음원 210.8s 교체 후 재정렬·재렌더). 업로드 대기 |
| **그렇게 지나간다** | 사계절 순환=인내(장소 은유 아님) | smooth urban R&B ~90 BPM +gospel | **완주+발행패키지 준비.** 첫 스케줄러 업로드 후보(§4.1) |
| 송도유원지 / 그날의 오월 / 변함없는 노을 / 그림자 | — | — | 가사 有, 구 1080p MP4 존재 → 재제작 필요 |
| 간다 말했다 | 친구 애도 | — | **민감: 자살한 친구 애도 — 로맨틱 프레이밍 금지, 추모/황혼 컨셉만** |
| 관람차 (gwanramcha) | 밤바다·관람차 순환 | 네오소울 R&B | **취소/격리**(작업트리 제거 → `_archive_*`/휴지통, git 미추적). ※ HADES.md §5는 아직 이걸 첫곡 확정으로 기재 — 충돌, §9 참조 |

### 4.1 geureoke 상세
- 렌더/검수/커버 확정. cover `sha256 526fb5daf0a9…`, RESULT.txt **9/9 PASS**, duration **169.760s**(align/audio 일치).
- 커버 오버라이드(geureoke 전용): `title_ko_scale=104` · `title_en_gap=62` · `title_en_scale=145`.
- 발행 패키지: `tracks/geureoke/out/youtube_description.txt`(1행 제목 / 3행~ 설명 / 태그 섹션).
- **다음 첫 액션**: `upload_scheduler.py --track geureoke`를 첫 실제 업로드로 실행(스케줄러 실전 검증 겸) → 게시 확인. (client_secret 준비 필요, §7.)

## 5. YouTube 발행 정책·쿼터 (2026-07 리서치 — 발행 전략의 근거)
- **쿼터 정정**: `videos.insert` 비용이 ~1,600 → **~100 units/업로드**(2025-12-04)로 하락, **2026-06-01부터** 업로드는 10k 공유풀과 분리된 **전용 일일 버킷(~100건)**으로 과금. **쿼터는 더 이상 실질 제약 아님**(HADES.md §4.4의 "하루 ~6건"은 구정보).
- **최대 리스크는 쿼터가 아니라 발행 "패턴/속도"**: "repetitious content"가 **"inauthentic content"**(2025-07)로 개칭되고 **채널 단위** 제재로 이동. 2026-01 대규모 정리(16채널·구독 3,500만·조회 47억 종료). 업계 소식통이 **"Suno 같은 툴로 만든 음악 플레이리스트 + 정적 이미지"**를 위험 예시로 명시 — 우리 파이프라인 표면형과 구조적으로 유사(단, 원작 가사·트랙별 스타일·forced-align·게이트별 인간 검수라는 차별화는 정책이 "처벌 안 함"이라 명시한 바로 그 요소).
- **트리거 = "인간 팀이 낼 수 없는 생산 속도"**: 신규 채널이 구조적으로 유사한 다수 영상을 거의 동시에 올리는 패턴이 최고 위험. 쿼터 여유와 무관.
- **수익화**: 신규 "Reina" 채널은 업로드 속도와 무관하게 구독 1,000 + 시청 4,000시간(최근 12개월) 필요 → 1~10번 곡을 빠르게 올릴 **보상은 없고 리스크만** 있음.
- **행동 지침**: 업로드는 **하루 1~2건**으로 페이싱(`upload_scheduler.py` 캡), 영상마다 **진짜 편집 판단이 보이는 개별 설명/노트**(가사 발췌·제작 노트), Studio에서 **"변경/합성 콘텐츠" 공시 토글 정직하게** 체크(정확한 AI-보조 라벨은 알고리즘 불이익 없음, 미표기 리스크가 더 큼).

## 6. Shorts 크롭 공식 (make_shorts.py 구현 참고 — 미빌드)
2560×1440 마스터 → 9:16 중앙 크롭 → 1080×1920 스케일:
```
-vf "crop=810:1440:(iw-810)/2:0,scale=1080:1920"
```
align.json의 첫 `[Chorus]` 타임스탬프로 30~40초 구간 선택 후 위 필터 적용. **주의**: Shorts는 본편과 **같은 날 올리지 말 것**(신규 채널 반복 신호) — 최소 하루 간격.

## 7. YouTube 채널 셋업 (수동·1회 — 미확정)
- 채널 **"Reina"**는 **별도 구글 계정 `reina2hj@gmail.com`** 아래에 둔다 — 사업용 계정 `foob0201@gmail.com`과 **방화벽 분리**(한 채널 정책위반이 동일 구글계정 전 채널로 전이되는 종료 리스크 격리). (과거 "동일 계정" 메모는 오기 → 정정.)
- 핸들 목표 `@reinamusic_0217` 류 — 계정 변경으로 **재확인 필요**(핸들 변경 14일 2회 제한).
- `upload_scheduler.py` OAuth는 `reina2hj@gmail.com`으로 로그인; **`client_secret.json`은 기존 프로젝트 것을 재사용해도 OK(확인됨)**.
- **상태: 계정 전환 후 채널 존재 재확인 안 됨 — 셋업 완료로 단정 말고 영석고고에게 확인.**

## 8. 사용자 선호 / 작업 방식
- **존댓말** 필수. 간결·직접(짧은 말 → 전체 패키지).
- 미학: 간접 표현(감각·물성·동작), **장소=감정 은유**(또는 계절 은유), **수미상관**, 곡마다 차별화.
- 장르는 레퍼런스로 호명 → 즉시 적용. Suno: 영어 섹션 태그·영어 애드립.
- 가사 파일: 가급적 파일로 투입(채팅 붙여넣기는 줄바꿈 유실 위험). 부득이 붙여넣으면 UTF-8로 재구성.
- Windows PS 5.1 `Get-Content|Set-Content`는 한글(UTF-8) 파일을 cp949로 왕복해 **손상** → 편집은 UTF-8 안전 방식만.

## 9. HADES.md 충돌 플래그 (텍스트 정정 필요 — 헌장 편집은 별도 사인오프)
헌장(HADES.md)이 현재 확정 표준과 어긋나는 4곳. **HADES.md는 사인오프 없이 편집 금지** → 여기 플래그만.
| # | 위치 | 문제 | 정정값 |
|---|---|---|---|
| 1 | §3.1 데이터흐름 | Demucs→WhisperX 정렬 경로로 표기 | MMS_FA 직접 CTC forced-align으로 대체됨(§6·VISUAL과 일치, 다이어그램만 미갱신) |
| 2 | §4.3 최상화질 | "2-pass VBR 16-24Mbps·60fps·preset slow" | 확정=CRF16·1-pass·preset medium·30fps(§6에선 이미 확정으로 기재, §4.3만 미갱신) |
| 3 | §4.4 배포 | "YouTube API 하루 ~6건" | ~100건/일 전용버킷(2026-06-01~), §5 참조 |
| 4 | §5 의사결정 로그 | "첫 곡 관람차(월미도)" 확정으로 기재 | gwanramcha 취소됨 → 실제 첫 완주(아무말도)로 대체 |

## 10. 미결정 / 보류
- 관람차: 보류(격리). 재개 시 `_archive_*`/휴지통에서 복구.
- geureoke 실제 업로드: client_secret 준비 + OAuth 후 사용자가 스케줄러 실행.
- 채널 존재 재확인(§7), HADES.md 4건 정정(§9), 리서처·배포 에이전트·P2/P3, 오디오 정체성 preflight(과거 donghae 오음원 사고 재발 방지)·`make_shorts.py`.

## 11. 네비게이터 규율 — 세션 교훈 (반복 방지 로그)
geureoke 발행 단계에서 발생한 네비게이터 실수 2건, 고정 교훈으로 기록:
1. **미응답 질문** — 영석고고가 "다른 프로젝트의 client_secret.json 재사용 가능?"을 물었는데 그 턴에 답하지 않고 넘어감. → **규칙: 직접 질문은 같은 턴에 답한다.** (본 건 결론: 재사용 OK — §7.)
2. **정정에 흔들린 판단** — 근거 설명 없이 "수동 업로드(A)"로 밀었다가, "자동화하려고 만든 것 아니냐"는 지적 후 charter §4(자동 업로드)와 상충함을 인정·번복. → **규칙: 판단 확정 전에 헌장·기존 결정과 충돌부터 대조한다. 사용자가 모순을 잡아내게 두지 말 것. 확정된 것은 흔들지 않는다(HADES §2.4).** (정합 결론은 §3: 파이프라인 자동발사 금지 + 스케줄러 통한 사용자 트리거 업로드.)

## 12. 지금 당장 다음 액션
1. geureoke 발행: client_secret 배치 후 `.venv-align/Scripts/python.exe upload_scheduler.py --track geureoke`(사용자 직접, OAuth 1회 → reina2hj). client_secret 없으면 안내 출력.
2. 업로드 후 `upload_manifest.json`(video_id·url) 확인 → RESULT.txt 발행줄 추가 → CONTEXT 곡이력 갱신.
3. 채널 존재 재확인(§7). 이후 업로드는 하루 1~2건 페이싱(§5).
4. 다음 곡: 가사→커버(fal+승인)→align_mms→align,video→발행패키지. (양산 신호 회피)
