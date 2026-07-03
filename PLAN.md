# PLAN — 실행 계획 & 마일스톤

> *언제 / 어떤 순서로.* 헌장·아키텍처는 HADES.md, 현재 상태는 CONTEXT.md 참조.

## 마일스톤

| Phase | 내용 | 상태 |
|---|---|---|
| 0 | repo 골격 · .gitignore · 설정 스키마 | ✅ 완료 |
| 1 | 자막 엔진(KO 정렬 → 액션 ASS, KO+EN dual) | ✅ 완료·픽셀검증 |
| 2 | 영상 합성(Ken Burns + 자막, 1440p 1-pass CRF16) | ✅ 완료·엔드투엔드 검증 |
| 3 | YouTube 업로드(사용자 트리거 `upload_scheduler.py`·재시도·멱등) | ✅ 완료 (geureoke 공개 발행) |
| 4 | Threads 게시(토큰 갱신·재시도·멱등) | ✅ 코드 완료 (토큰 대기) |
| P0 | 프리플라이트·매니페스트·htdemucs_ft·재시도·시크릿 chmod | ✅ 완료 |
| 5 | 곡 엔드투엔드 완주 | ✅ **5곡 완주**(geureoke 공개 발행). 「관람차」는 음원 미생성 보류 |
| P1 | 알려진 가사 직접 CTC forced-align(MMS `scripts/align_mms.py`) | ✅ 완료·실음원 검증 |
| P2 | AI 공시 플래그 · Drive 자동 백업 | ⬜ 첫 릴리스 후 |
| P3 | Mel-RoFormer · AV1 · Remotion · Threads 네이티브 | ⬜ 천장(보류) |
| P4 | 인스트루멘털 멀티씬 크로스페이드(BGM 커버 여러 장 전환) | ⬜ 후순위(백로그) — 현행 instrumental 은 단일 커버 Ken Burns |

## 곡 완주 순서 (일반 · `<곡>`=slug)

1. `tracks/_template/`을 복사해 `tracks/<곡>/`에 `lyrics_ko.txt`·`lyrics_en.txt`(줄 수 1:1) 배치
2. `cover_render.py`(또는 fal 배경 `hades/fal_bg.py`)로 커버 생성 → `.cover_ok` 승인
3. Suno Pro로 음원 생성 → `audio.mp3` 투입
4. `scripts/align_mms.py <곡>` 또는 `python pipeline.py --track tracks/<곡>/config.yaml --steps align`
   → 싱크 육안 확인, 필요 시 `config.yaml`의 `align.offset_ms` 보정
5. `--steps video` → 최상화질 dual mp4 (커버 게이트 통과 필요)
6. 발행: **사용자가 직접** `upload_scheduler.py --track <곡>` 실행(대화형 OAuth·일일캡·멱등)

## 완료 기준 (DoD) — HADES §5

1. KO 자막이 음원에 정렬·싱크 육안 확인
2. 영상이 최상 화질 프로파일(1440p·1-pass CRF16·H.264 High)로 렌더
3. 곡 폴더에 음원·KO/EN 가사·커버·산출물 보존
4. YouTube 업로드 + (선택)Threads 게시, 매니페스트 기록(멱등)
5. 메타데이터(제목·설명·가사·태그) 채워짐

## 범위 규율 (HADES §2.6)

P0만 반영 완료. **P1~P3은 첫 곡 완주 검증 이후로 보류.**
