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
| radio | Early morning radio.mp3 | `801dc91a3d6f132b5b503a617c2483d3` | 194.40 | OK | 신규(2026-07-06 등재) |

## 참고: 기존 빌드 트랙 (별도 md5)
| slug | md5 | duration(s) | 비고 |
|---|---|---|---|
| amumaldo | `08007c27ee31f73b4164affb605425e8` | 219.96 | 루트 audio.mp3와 동일본 |
| bomnal   | `e0e8f9c241f9c8e6be84996c358e7cf4` | 194.24 | 음원 '봄날 그방'(440a7830)과 md5 상이 |
| donghae  | `5a20e32734c14723b3b29728b17b2579` | 210.80 | 음원 '동해로(Remastered)'(a27e4cc9)과 md5 상이 |
| geoul_oneul | `7b13bf64d135921a620c3c7f956a294f` | 204.80 | 음원 '거울 속의 오늘(트로트)'와 동일본 |
| geureoke | `981cfbc9489e46544b309ae5f05ccc64` | 169.76 | 음원 '그렇게 지나간다'와 동일본 |

