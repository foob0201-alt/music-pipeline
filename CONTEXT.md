# CONTEXT — 프로젝트 현재 상태 (세션 인계)

> 하데스 §2.3(이전 대화 세세히 기억)을 파일로 고정한 **살아있는 상태 문서**.
> 새 세션은 이 문서를 먼저 읽고, 불확실하면 과거 대화를 검색해 보강한다.
> 위계: HADES.md → **AGENTS.md**(팀헌장) → PLAN.md → **CONTEXT.md** → README.md.
_최종 갱신: 2026-06-29 — 「아무말도」·「봄날」 마스터 완주·ffprobe 검증, git 도입_

## 1. 한 줄 요약
**「아무말도」·「봄날」 두 곡 마스터 완주·ffprobe 검증 완료.** 파이프라인(MMS_FA 강제정렬 → dual 자막 ASS → 1440p 렌더) 실가동 검증, 코드 제너러티브 커버(STYLES: luminous_dawn·bright_nocturne) 동작, **git 도입**(원격 origin) 완료.
(이전: 7개 모듈 빌드 · 자막엔진 1440p 픽셀검증 · align→video 엔드투엔드 통과.)

## 2. 빌드된 것 (이번 세션)
| 파일 | 상태 |
|---|---|
| `hades_util.py` (설정·컨텍스트·매니페스트·재시도·시크릿) | ✅ |
| `preflight.py` (P0 선행검증: 파일·ffmpeg·폰트·KO/EN 줄수) | ✅ |
| `align.py` (보컬분리·KO정렬·EN 1:1·액션 ASS·LRC) | ✅ 픽셀검증 |
| `make_video.py` (Ken Burns·자막굽기·2-pass 1440p) | ✅ 엔드투엔드 |
| `upload_youtube.py` (버전별·재시도·멱등) | ✅ 코드 |
| `post_threads.py` (토큰갱신·재시도·멱등) | ✅ 코드 |
| `pipeline.py` (오케스트레이터·의존성 자동보강) | ✅ |
| `config.yaml` / `requirements.txt` / `.gitignore` | ✅ |
| `scripts/make_cover.py` / `scripts/selftest.py` | ✅ |

검증 결과: dual 프레임 픽셀 — 노랑(KO 채움) 793 / 흰색(KO) 902 / 크림(EN) 796 → PASS.
영상 산출 — 2560×1440 · H.264 · yuv420p(bt709) · AAC 384k/48k.

## 3. 확정 결정 (네비게이터 최종)
- 첫 곡 제목: **관람차** (부제 *월미도*)
- 포맷: **가로 1440p** · 첫 발행 모드: **dual**(KO 위 + EN 아래, 색 분리)
- 자막 액션: action(팝업+단어 색채움) · 화질: 1440p·2-pass·H.264 High
- 정렬: KO 음원 force-align(미설치 시 균등분할 폴백) + EN 1:1 타임코드 상속

## 4. 곡 이력
| 곡 | 장소/컨셉 | 장르 | 상태 |
|---|---|---|---|
| 그날의 오월 | 올림픽공원 5월 | R&B-pop (Peaches) | MP4 전달 |
| 송도유원지 | 인천 장소 회상 | city-pop R&B | MP4+메타 |
| 옥련동 / 이 길 | 순환 관계 | gospel-R&B | 편곡 다회 |
| 그렇게 지나간다 | 계절의 견딤 | R&B-pop+gospel | 방향 확정 |
| 변함없는 노을 | 올림픽대로 노을 | R&B 78 BPM | MP4, 제목 보류 |
| 그림자 | 어둠→빛 치유 | R&B-pop 92 BPM | MP4 전달 |
| 친구의 죽음 애도 | 상실·작별 | 록 발라드 | 제작 |
| 김치송 | 발효=인내 | 멜로딕 트랩 | Suno 패키지 |
| 아무말도 | 놀이터 벤치·여름밤 | 업템포 일렉트로-R&B | **마스터 완주·검증** |
| 봄날 | 그 봄날의 방·여름비 재회 | future soul (Suno) | **마스터 완주·검증** |
| 관람차 (월미도) | 밤바다·관람차 순환 | 네오소울 R&B | 가사·커버 준비, 음원 대기 |

## 5. 사용자 선호 / 작업 방식
- **존댓말** 필수. 간결·직접(짧은 말 → 전체 패키지).
- 미학: 간접 표현(감각·물성·동작), **장소=감정 은유**, **수미상관**.
- 장르는 레퍼런스로 호명 → 즉시 적용. Suno: 영어 섹션 태그·영어 애드립.

## 6. 미결정 / 보류
- 변함없는 노을 최종 제목(변함없는 노을 vs 올림픽대로).
- 관람차 음원·커버 투입(P1 직접 forced-align은 실음원 확보 후).
- P2/P3는 첫 릴리스 후.

## 7. 지금 당장 다음 액션
1. 관람차 `lyrics_ko.txt`·`lyrics_en.txt` → `tracks/gwanramcha/`
2. 커버 생성 → `tracks/gwanramcha/cover.jpg`
3. Suno Pro 음원 → `tracks/gwanramcha/audio.mp3`
4. `python pipeline.py --track tracks/gwanramcha/config.yaml --steps align` → 싱크 확인 → `--steps all`
