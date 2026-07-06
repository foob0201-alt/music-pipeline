# INVENTORY 20260706 — HADES 미디어 전수 조사 (읽기 전용)

> **정리작전 1단계.** 근무지 `C:\hades` 단일 확정. 이동·삭제·수정 일절 없이 **목록화만** 수행.
> 길이=ffprobe(초), md5=md5sum. 생성일 2026-07-06.

---

## 0. 요약

- **내부 mp3:** 38개 · **내부 mp4:** 11개 (총 49 미디어 파일)
- **정본 대조:** 라이브 `tracks/*/audio.mp3` 10곡 모두 FINGERPRINTS 원장 md5와 **일치**(오염 없음). `radio`만 원장 미등재(신규).
- **주요 이상:** ①`donghae` 폴더에 `audio.mp3`+`donghae.mp3` 동일본 중복 ②`ganda/gueup/owol` 오디오만 존재(가사·커버·렌더 없음) ③`radio` 렌더 미완(out/ 비어있음, 가사 없음) ④geureoke 오디오 동일본이 내부 4곳에 산재.
- **외부:** `_RETIRED_20260706_원본보존`(OneDrive 내 전 파이프라인 봉인 사본) = **봉인됨, 스캔 제외**. 그 외 OneDrive에 격리 판정 대상 잔존 음원 다수. 데스크톱·다운로드·문서 트리엔 HADES 미디어 없음.
- **이동·삭제 0건.**

---

## 1. C:\hades 내부 — mp3 전수

| 상대경로 | 크기(B) | 수정일 | 길이(s) | md5 | 정본 대조 |
|---|---|---|---|---|---|
| `audio.mp3` (루트) | 5,310,582 | 2026-06-26 12:23:05 | 219.96 | `08007c27ee31f73b4164affb605425e8` | = amumaldo (원장 OK) |
| `tracks/amumaldo/audio.mp3` | 5,310,582 | 2026-06-26 12:23:05 | 219.96 | `08007c27ee31f73b4164affb605425e8` | 원장 OK ✓ |
| `tracks/bomnal/audio.mp3` | 4,527,366 | 2026-06-29 15:31:17 | 194.24 | `e0e8f9c241f9c8e6be84996c358e7cf4` | 원장 OK ✓ |
| `tracks/donghae/audio.mp3` | 4,780,614 | 2026-07-01 10:32:06 | 210.80 | `5a20e32734c14723b3b29728b17b2579` | 원장 OK ✓ |
| `tracks/donghae/donghae.mp3` | 4,780,614 | 2026-07-01 10:32:06 | 210.80 | `5a20e32734c14723b3b29728b17b2579` | ⚠️ audio.mp3와 **동일본 중복** |
| `tracks/ganda/audio.mp3` | 5,958,865 | 2026-07-01 13:39:45 | 258.92 | `7fb0453a6cff28672b11f42d5877d4c8` | 원장 OK ✓ |
| `tracks/geoul_oneul/audio.mp3` | 4,604,526 | 2026-06-29 11:48:44 | 204.80 | `7b13bf64d135921a620c3c7f956a294f` | 원장 OK ✓ |
| `tracks/geureoke/audio.mp3` | 3,758,809 | 2026-07-01 13:53:47 | 169.76 | `981cfbc9489e46544b309ae5f05ccc64` | 원장 OK ✓ |
| `tracks/gueup/audio.mp3` | 4,091,012 | 2026-07-01 13:39:02 | 178.80 | `4109e58f7c0404af66b8b32847c6b2a3` | 원장 OK ✓ |
| `tracks/okryeon/audio.mp3` | 4,402,839 | 2026-07-01 13:37:34 | 193.12 | `15b3405efb9decf9bbb76472641e4b9a` | 원장 OK ✓ |
| `tracks/owol/audio.mp3` | 3,952,670 | 2026-07-01 13:40:13 | 175.84 | `2220c367208db94ecfb641e168d68103` | 원장 OK ✓ |
| `tracks/radio/audio.mp3` | 4,495,134 | 2026-07-03 10:40:44 | 194.40 | `801dc91a3d6f132b5b503a617c2483d3` | ⚠️ **원장 미등재**(신규) · = 음원/Early morning radio |
| `tracks/songdo/audio.mp3` | 4,451,282 | 2026-07-01 13:38:41 | 196.08 | `03d6aaffba046ed27672c9fd601620cc` | 원장 OK ✓ |
| `_archive_20260701_141302/AMU__geureoke_contaminant.mp3` | 3,758,809 | 2026-07-01 13:44:33 | 169.76 | `981cfbc9489e46544b309ae5f05ccc64` | 과거 amumaldo 오염분(내용=geureoke), 격리보관됨 |

### 음원/ (대장 폴더 — 원본 보관)

| 상대경로 | 크기(B) | 수정일 | 길이(s) | md5 |
|---|---|---|---|---|
| `음원/Early morning radio.mp3` | 4,495,134 | 2026-07-01 13:30:25 | 194.40 | `801dc91a3d6f132b5b503a617c2483d3` |
| `음원/If we meet again.mp3` | 4,792,182 | 2026-07-01 13:28:43 | 208.60 | `0fd769039cb0fa1b69db7443541f008d` |
| `음원/If we meet again (1).mp3` | 4,809,595 | 2026-07-01 13:35:18 | 208.60 | `83963eedac9710edf0818d95e04e3fdb` |
| `음원/Neon Pulse.mp3` | 5,017,258 | 2026-07-01 13:34:55 | 209.68 | `18277a4993e6a64a2427e2126f2ab329` |
| `음원/Shadow (Electropop Bounce Remix).mp3` | 5,348,440 | 2026-07-01 13:36:17 | 236.80 | `a39f7bf86f1958b117801d32d7892bc7` |
| `음원/Spring Rain Dance Night (리믹스).mp3` | 4,436,526 | 2026-07-01 13:28:10 | 190.64 | `ee2c80ffa4a0b7640492cfb9165d599d` |
| `음원/The Vow That Defies Death.mp3` | 4,816,014 | 2026-07-01 13:30:43 | 204.08 | `744cc28020105167bb5f07de723d5088` |
| `음원/The Vow That Defies Death (1).mp3` | 5,158,715 | 2026-07-01 13:34:34 | 224.40 | `024fe58ff3fe9539c9f5fa0266e85b20` |
| `음원/간다 말했다.mp3` | 5,958,865 | 2026-07-01 13:39:45 | 258.92 | `7fb0453a6cff28672b11f42d5877d4c8` | 
| `음원/거울 속의 오늘(트로트).mp3` | 4,604,526 | 2026-07-01 13:28:32 | 204.80 | `7b13bf64d135921a620c3c7f956a294f` |
| `음원/그날의 오월.mp3` | 3,952,670 | 2026-07-01 13:40:13 | 175.84 | `2220c367208db94ecfb641e168d68103` |
| `음원/그냥 좋았어 (리믹스).mp3` | 6,772,693 | 2026-07-01 13:38:14 | 292.12 | `56509f6079469e21a23ea811d6d30979` |
| `음원/그렇게 지나간다.mp3` | 3,758,809 | 2026-07-01 13:37:54 | 169.76 | `981cfbc9489e46544b309ae5f05ccc64` |
| `음원/동해로 (Remastered).mp3` | 4,780,614 | 2026-07-01 13:30:56 | 210.80 | `a27e4cc9e27bebc382459771cb2d02d3` |
| `음원/번지다 (Epic Bounce Drop Remix).mp3` | 5,216,455 | 2026-07-01 13:36:47 | 234.84 | `d01467725e8ad1e7ef4320e99a056921` |
| `음원/변함없는 노을.mp3` | 5,136,199 | 2026-07-01 13:37:09 | 220.88 | `b6b05ef9b03a3b682fde74bc97df45bd` |
| `음원/봄날 그방.mp3` | 4,527,366 | 2026-07-01 13:29:15 | 194.24 | `440a78302fc2acf587a866c7075075e6` |
| `음원/살펴 가.mp3` | 3,614,722 | 2026-07-01 13:34:04 | 161.88 | `aa276033b542b5a00f7f7fd91de7d7bc` |
| `음원/새 폴더/geureoke.mp3` | 3,758,809 | 2026-07-01 13:44:33 | 169.76 | `981cfbc9489e46544b309ae5f05ccc64` |
| `음원/송도 유원지.mp3` | 4,451,282 | 2026-07-01 13:38:41 | 196.08 | `03d6aaffba046ed27672c9fd601620cc` |
| `음원/오늘만 같으면 구읍뱃터.mp3` | 4,091,012 | 2026-07-01 13:39:02 | 178.80 | `4109e58f7c0404af66b8b32847c6b2a3` |
| `음원/옥련동.mp3` | 4,402,839 | 2026-07-01 13:37:34 | 193.12 | `15b3405efb9decf9bbb76472641e4b9a` |
| `음원/좋은 아침이야, 엄마 (리믹스).mp3` | 4,080,690 | 2026-07-01 13:35:39 | 184.68 | `3cffb5ea66f5bc1ba337d2e636dccf66` |

**md5 중복 클러스터(내부):**
- `981cfbc9…` (geureoke, 169.76s) — 4곳: `tracks/geureoke/audio.mp3`, `_archive…/AMU__geureoke_contaminant.mp3`, `음원/그렇게 지나간다.mp3`, `음원/새 폴더/geureoke.mp3`
- `08007c27…` (amumaldo, 219.96s) — 2곳: 루트 `audio.mp3`, `tracks/amumaldo/audio.mp3`
- `5a20e327…` (donghae, 210.80s) — 2곳: `tracks/donghae/audio.mp3`, `tracks/donghae/donghae.mp3`
- `801dc91a…` (radio, 194.40s) — 2곳: `tracks/radio/audio.mp3`, `음원/Early morning radio.mp3`
- 라이브↔대장 동일본: ganda·geoul_oneul·owol·gueup·okryeon·songdo 각 1:1 일치
- ⚠️ **대장≠라이브(원장 기록대로):** `음원/봄날 그방`(440a7830) ≠ bomnal 빌드(e0e8f9c2) · `음원/동해로(Remastered)`(a27e4cc9) ≠ donghae 빌드(5a20e327)

---

## 2. C:\hades 내부 — mp4 전수

| 상대경로 | 크기(B) | 수정일 | 길이(s) | md5 |
|---|---|---|---|---|
| `tracks/amumaldo/out/amumaldo_dual.mp4` | 59,145,170 | 2026-06-29 16:21:25 | 219.96 | `ada487eb4a89c167ba07479bc08f32a1` |
| `tracks/bomnal/out/bomnal_dual.mp4` | 62,515,600 | 2026-07-03 17:16:45 | 193.90 | `effad05e96ef41eafd8cf6a940bdda94` |
| `tracks/bomnal/out/_old_pre115/bomnal_dual.mp4` | 60,871,960 | 2026-06-29 18:11:43 | 193.90 | `256f74b5d8b53ee71e4af0764186b65a` |
| `tracks/donghae/out/donghae_dual.mp4` | 92,400,563 | 2026-07-01 11:44:25 | 210.80 | `fa771b5ef180b9f29e24787d6f72272b` |
| `tracks/geoul_oneul/out/geoul_oneul_dual.mp4` | 73,769,993 | 2026-06-30 16:19:00 | 204.80 | `a3e268ea11936701e52b01c62c5022ae` |
| `tracks/geureoke/out/geureoke_dual.mp4` | 104,626,783 | 2026-07-01 17:23:21 | 169.76 | `b57608ae7d4852deb1d3eafea89d5fbc` |
| `tracks/geureoke/out/subtitle_test_100.mp4` | 4,801,651 | 2026-07-02 11:07:18 | 19.50 | `797b70f13fe859318d504c8f3aa8b7ce` |
| `tracks/geureoke/out/subtitle_test_115.mp4` | 4,883,215 | 2026-07-02 11:08:53 | 19.50 | `3be3812d5d9f9dee23d40c82da353225` |
| `tracks/geureoke/out/subtitle_test_125.mp4` | 5,008,273 | 2026-07-02 11:10:14 | 19.50 | `21f553db649a5e14bbd03e465e4ceb86` |
| `tracks/okryeon/out/okryeon_dual.mp4` | 157,503,857 | 2026-07-03 11:36:53 | 193.12 | `16b02e313a47bf3ceffba376a2a1f385` |
| `tracks/songdo/out/songdo_dual.mp4` | 202,241,834 | 2026-07-02 14:56:42 | 196.07 | `22aa02c2f0faf9c9c5437923cccc2e60` |

**렌더 완료 곡(dual mp4 보유):** amumaldo · bomnal · donghae · geoul_oneul · geureoke · okryeon · songdo (7곡)
**미완/테스트 잔여:** `geureoke/out/subtitle_test_{100,115,125}.mp4`(자막 스케일 테스트 3종) · `bomnal/out/_old_pre115/bomnal_dual.mp4`(1.15 재렌더 이전 구규격)

---

## 3. tracks/<슬러그>/ 표준 배치 위반

> 표준: `<슬러그>.mp3` / `lyrics_ko.txt` / `lyrics_en.txt` / `cover.jpg` / `out/*.mp4`
> ※ **공통 규격 편차:** 전 트랙이 오디오 파일명을 표준 `<슬러그>.mp3`가 아니라 파이프라인 관례인 **`audio.mp3`**로 사용 중(FINGERPRINTS도 audio.mp3 기준). 아래는 그 외 개별 위반만 표기.

| 슬러그 | 위반/이상 |
|---|---|
| `_template` | (템플릿) audio·cover 없음, lyrics만 — 정상 |
| `amumaldo` | 정상(audio·lyrics·cover·out mp4). 여분: `config.yaml`, `verify_sub.png` |
| `bomnal` | 정상. 여분: `out/_old_pre115/`(구규격 mp4 보관) |
| `donghae` | ⚠️ **`audio.mp3`+`donghae.mp3` 동일본 중복** · 여분: `bg_donghae.png`,`bg_test.png`,`RESULT.txt`,`out/files (1)`,`out/files (1).zip`(잔재) |
| `ganda` | ⚠️ **audio.mp3만 존재** — lyrics_ko/en·cover·out 전부 없음(미착수) |
| `geoul_oneul` | 정상(out mp4 보유). 여분: `bg_test.png`,`RESULT.txt`. `.lrc` 없음(align.json은 있음) |
| `geureoke` | 정상. 여분: 자막테스트 `_subtest_*.ass`+mp4 3종, `upload_manifest.json`,`youtube_description.txt` |
| `gueup` | ⚠️ **audio.mp3만 존재** — lyrics·cover·out 없음(미착수) |
| `okryeon` | 정상(out mp4 보유). ⚠️ `config.yaml` 없음 · 여분: `_stale_oldtemplate/`, bg_*.png 3종, `state.json`, `out/HOLD_NOTIFY.txt`, 커버후보 cand_*.jpg |
| `owol` | ⚠️ **audio.mp3만 존재** — lyrics·cover·out 없음(미착수) |
| `radio` | ⚠️ **out/ 비어있음(렌더 미완)** · lyrics_ko/en 없음 · 있음: audio,cover,config,bg_*.png 3종,state.json,cover_base.jpg |
| `songdo` | 정상(audio·lyrics·cover·config·out mp4 완비). 여분: bg_*.png 다수, 커버후보 cand_*.jpg |

---

## 4. C:\hades 외부 미디어 스캔 (참고용 · 격리 판정 대상)

### 4.1 봉인 구역 — 스캔 제외
- **`…\OneDrive\바탕 화면\1_진행중\Claude_AI작업\음악생성\music-pipeline\_RETIRED_20260706_원본보존\`**
  → 전 파이프라인(tracks·음원·루트 audio 포함)의 **원본 보존 사본**. 지침대로 **봉인됨**으로만 표기, 상세 목록·해시 대조 제외.

### 4.2 격리 판정 대상 — OneDrive 잔존 음원 (다운로드 미유발, 논리크기만)
> OneDrive 동기화 폴더. placeholder 가능성 있어 ffprobe·md5 **미실행**(다운로드 트리거 금지). 경로·논리크기만.

**`…\Claude_AI작업\2025\bgm\`** (구 BGM 스템, 9개):
| 파일 | 논리크기(B) |
|---|---|
| `bgm_may.mp3.mp3` | 3,952,672 |
| `calm.mp3.mp3` | 3,841,044 |
| `epic.mp3.mp3` | 4,237,270 |
| `epic.mp3 (2).mp3` | 4,994,304 |
| `exciting.mp3.mp3` | 3,154,755 |
| `exciting.mp3 (2).mp3` | 6,765,923 |
| `오월 공원미스트.mp3` | 3,797,411 |
| `오월 미스트비 (Remastered).mp3` | 3,738,041 |
| `오월의 미스트비 (리믹스).mp3` | 4,403,801 |

**`…\Claude_AI작업\음악생성\`** (루즈 음원, 9개):
| 파일 | 논리크기(B) | 비고 |
|---|---|---|
| `아무말도.mp3` | 5,310,582 | 크기=amumaldo 라이브와 동일(동일본 추정) |
| `bomnal_audio.mp3` | 4,527,366 | 크기=bomnal 라이브와 동일 |
| `_archive_misplaced/봄날 그방.mp3` | 4,527,366 | 크기=bomnal 라이브와 동일 |
| `donghae.mp3` | 4,780,614 | 크기=donghae 라이브와 동일 |
| `Early morning radio.mp3` | 4,495,134 | 크기=radio 라이브와 동일 |
| `If we meet again.mp3` | 4,792,182 | 크기=음원/If we meet again와 동일 |
| `The Vow That Defies Death.mp3` | 4,816,014 | 크기=음원/The Vow…와 동일 |
| `거울 속의 오늘(트로트).mp3` | 4,604,526 | 크기=geoul_oneul 원본과 동일 |
| `살펴 가.mp3` | 3,894,798 | 크기=음원/살펴 가(3,614,722)와 **상이** |

*(placeholder 판정: `attrib` 조회는 다운로드 미유발로 수행했으나 속성문자 미검출 — 상태 불명 처리. 확정 대조 필요 시 별도 승인 후 materialize.)*

### 4.3 앱/시스템 노이즈 (HADES 무관 — 개수 요약)
- Chrome 확장(Acrobat) 안내영상 `summary*.mp4` ×10
- KakaoTalk 이모티콘 사운드/영상 (`DigitalItem/*.mp3`, `Contacts/*.mp4`) ×25
- Microsoft Solitaire 광고캐시(VungleSDK) `*.mp4` ×8
- VS Code 접근성 시그널 사운드 `media/*.mp3` ×30
- Chrome 확장 알림음 `notification.mp3` ×1
→ 격리 대상 아님(설치 앱 리소스).

### 4.4 데스크톱·다운로드·문서
- `Desktop` 0 · `Downloads` 0 · `Documents` 0 — **HADES 미디어 없음.**
- OneDrive 플레이스홀더: 4.2 항목 외 강제 다운로드 없음.

---

## 5. FINGERPRINTS.md 전문 (정본 판정 기준 대조용)

```markdown
# 음원 지문 원장 (Fingerprint Ledger)

> 곡별 `audio.mp3`의 md5·duration 원장. 음원 정체성 사고(과거 donghae 오음원) 재발 방지용.
> 대장(음원/) 원본에서 복사 시 md5가 일치해야 무결. 재교체 시 이 원장 갱신.

| slug | 원본(음원/) | md5 | duration(s) | 대장대조 | 배치 |
|---|---|---|---|---|---|
| songdo | 송도 유원지.mp3 | `03d6aaffba046ed27672c9fd601620cc` | 196.08 | OK | 1차 |
| okryeon | 옥련동.mp3 | `15b3405efb9decf9bbb76472641e4b9a` | 193.12 | OK | 1차 |
| gueup | 오늘만 같으면 구읍뱃터.mp3 | `4109e58f7c0404af66b8b32847c6b2a3` | 178.80 | OK | 1차 |
| owol | 그날의 오월.mp3 | `2220c367208db94ecfb641e168d68103` | 175.84 | OK | 1차 |
| ganda | 간다 말했다.mp3 | `7fb0453a6cff28672b11f42d5877d4c8` | 258.92 | OK | 1차 |

## 참고: 기존 빌드 트랙 (별도 md5)
| slug | md5 | duration(s) | 비고 |
|---|---|---|---|
| amumaldo | `08007c27ee31f73b4164affb605425e8` | 219.96 | 루트 audio.mp3와 동일본 |
| bomnal   | `e0e8f9c241f9c8e6be84996c358e7cf4` | 194.24 | 음원 '봄날 그방'(440a7830)과 md5 상이 |
| donghae  | `5a20e32734c14723b3b29728b17b2579` | 210.80 | 음원 '동해로(Remastered)'(a27e4cc9)과 md5 상이 |
| geoul_oneul | `7b13bf64d135921a620c3c7f956a294f` | 204.80 | 음원 '거울 속의 오늘(트로트)'와 동일본 |
| geureoke | `981cfbc9489e46544b309ae5f05ccc64` | 169.76 | 음원 '그렇게 지나간다'와 동일본 |
```

**원장 대조 결과:** 라이브 `tracks/*/audio.mp3` 전 곡이 원장 md5와 일치. 원장 미등재 신규 = **radio**(`801dc91a…`, 194.40s, 원본=음원/Early morning radio.mp3). → 원장 등재 권고.

---

이동·삭제 0건 — 본 조사는 읽기 전용으로 수행되었으며 어떤 파일도 이동·삭제·수정하지 않았음을 확인함.
