# 설계안 — 보컬 곡 멀티 씬 (make_video.py)

> 상태: **설계 문서 (코드 미구현)**. Navigator 검수·승인 후 착수.
> 작성 2026-07-13. 대상: 메인(16:9) 보컬 영상. 숏츠(9:16)와 별개.

## 1. 목적
단일 커버 + Ken Burns의 정적 인상을 벗어나, 곡의 구조(벌스/후렴/브리지)에 맞춰
**2~3개 씬(배경)**을 전환해 몰입도·차별화를 높인다(AI 슬롭 회피, 미학 헌장).

## 2. 씬 모델
- **씬 2~3개**, 경계 = `align.json` 섹션 타임코드.
  - 2씬: [Verse 계열] → [Chorus 계열] (곡 절반 기점).
  - 3씬: Verse → Chorus → Bridge/Outro.
- 각 씬은 **고유 배경 이미지**(cover.jpg 외 추가 배경 N장 필요 → cover_smith 확장).
  - 배경 파일 규칙(안): `tracks/<slug>/scene_{1,2,3}.jpg` (2560×1440, 기존 커버 규격).
- 씬 지속 = 섹션 경계 사이 구간(오디오 길이에 종속).

## 3. 전환 (xfade)
- ffmpeg `xfade` 크로스디졸브, **전환 1.0~1.5초**(기본 1.2s).
- 각 씬은 개별 zoompan(Ken Burns) 후 xfade로 연결:
  `[s1]zoompan…[v1];[s2]zoompan…[v2];[v1][v2]xfade=transition=fade:duration=1.2:offset=T1`
- 오프셋 = 직전 씬 종료 시점 − 전환시간/2(자연스러운 겹침).

## 4. 렌더 시간 증가 추정 (CPU 기준, UHD 610·GPU 없음)
현행 단일 커버 1-pass CRF16 preset slow: 3.5분 곡 ≈ **기준 T**.
| 구성 | 필터 부하 | 추정 배수 |
|---|---|---|
| 단일 커버(현행) | zoompan×1 | 1.0× (T) |
| 2씬 + xfade×1 | zoompan×2 + xfade | ~1.5× |
| 3씬 + xfade×2 | zoompan×3 + xfade×2 | ~1.9× |
- xfade는 전 프레임 합성이라 CPU 인코딩에서 비용이 큼. preset을 slow→medium으로
  낮추면 3씬도 ~1.4×로 억제 가능(화질 검수 필요).

## 5. 타이틀·사인 / Gate 1 흐름
- **제목 + Reina 사인은 첫 씬에만**(0~섹션1 경계, 페이드아웃). 이후 씬은 배경만.
- **Gate 1 scene_check는 씬별 실행**: scene_1/2/3.jpg 각각 tone_check + scene_check
  (no_face_no_text 등) 통과해야 합성 진행. 한 씬이라도 FAIL → 해당 씬 재생성(HOLD_COVER).
- `.cover_ok`는 씬별 해시 집합(sha256 3개)으로 확장 필요.

## 6. Ken Burns 씬별 변주 (로테이션 표)
단조로움 방지 위해 씬마다 방향·시작점·속도를 로테이션:
| 씬 | 줌 방향 | 시작 위치 | 속도(zoom_end) |
|---|---|---|---|
| 1 (Verse) | in (확대) | 중앙 | 1.08 (느림) |
| 2 (Chorus) | in | 좌하단→중앙 | 1.12 (보통) |
| 3 (Bridge) | out (축소) | 우상단 | 1.06 (느림) |
- 방향/시작점은 3씬 순환 세트에서 곡별로 오프셋 로테이션(양산형 회피).

## 7. make_video.py 수정 범위 (승인 후) — 코드 미수정
- `_filter()`: 다중 입력(scene_N) + 씬별 zoompan + xfade 체인 빌더.
- `_encode()`: 입력 N장 로드(-loop 각), 씬 경계(align 섹션) 파라미터 수신.
- 씬 경계 계산기: align.json 섹션 → 씬 타임코드(신규 헬퍼).
- 타이틀/사인: 첫 씬 한정 오버레이(자막 ASS 또는 drawtext).
- Gate 연동: hades_state 커버 게이트를 씬별 다중 해시로 확장.
- cover_smith: 곡당 배경 N장 생성 파이프(fal_bg 다회 호출).
- 회귀 위험: 단일 커버 경로 기본 보존(scene 파일 없으면 현행 동작).
