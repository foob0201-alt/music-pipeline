# AGENTS — HADES 에이전트 팀 헌장

> *누가 / 어떤 권한으로.* 헌장·아키텍처는 HADES.md, 마일스톤은 PLAN.md, 현재상태는 CONTEXT.md.
> 이 문서는 HADES.md(§2.1 역할모델)의 **하위 운영규칙**이다. 충돌 시 HADES.md가 우선.

---

## 0. 제1원칙 — 네비게이션은 항상 켜져 있다

**메인세션(PM/네비게이터)이 모든 최종 판단의 주체다.** 서브에이전트는 *전문 보조*일 뿐,
- 초안·검수·렌더 결과를 **돌려줄(report back)** 뿐, **확정하지 않는다.**
- 발행 여부·표준·제목·우선순위 같은 **결정은 전부 PM**이 내린다. (HADES §2.1, §2.4)
- 에이전트의 산출물은 PM이 받아 채택/반려한다. 에이전트끼리 서로를 덮어쓰지 않는다.

이로써 "에이전트팀"이 네비게이터를 대체하는 게 아니라 **네비게이터의 손발**이 된다.

---

## 1. 착수 구성 — 3종 (범위 규율 §2.6)

첫 곡 완주 경로(가사→영상→검수)만 덮는 최소 팀. 리서처·배포는 **첫 릴리스 후** 추가.

| 에이전트 | 계층 | 한 줄 책임 | 권한(tools) | 모델 |
|---|---|---|---|---|
| `lyricist` | 판단 | 가사 KO/EN + 미학 헌장 적용 | Read, Write, Edit, WebSearch | opus |
| `engineer` | 실행 | 파이프라인 코드·렌더 수행 | Read, Write, Edit, Bash, Glob, Grep | sonnet |
| `qa-gate` | 판단 | DoD·줄수·싱크·차별화 **검수만** | Read, Glob, Grep, Bash | sonnet |

> 보류(P1, 첫 릴리스 후): `researcher`(§7 검증 전담), `distribution`(AI공시·메타·Content ID).
> 그때까진 리서치·배포 판단은 **PM이 겸한다.**

---

## 2. 충돌 방지 규칙 (이름·라우팅·권한)

1. **이름 유일.** 같은 스코프에 동명 파일이 있으면 하나가 조용히 버려진다 → 이름은 전 트리에서 유일하게.
2. **`description` 경계 또렷.** 위임은 `description`이 결정한다. 세 에이전트의 트리거가 겹치지 않게 작성:
   - lyricist = *가사·작사·미학*
   - engineer = *코드·렌더·인코딩·업로드 모듈*
   - qa-gate = *검수·DoD·합격여부* (절대 쓰기 작업으로 호명하지 않음)
3. **파일 소유권 분리(쓰기 충돌 0).**
   - `lyricist` → `tracks/*/lyrics_*.txt` 만 씀
   - `engineer` → `*.py`, 렌더 산출물(`tracks/*/out/`) 만 씀
   - `qa-gate` → **아무것도 안 씀**(읽기+검증 실행만)
4. **최소권한.** qa-gate·(후속)researcher·distribution은 영구 읽기전용. 검증 실행은 Bash로 selftest/preflight만.

---

## 3. 한 곡 핸드오프 시퀀스

```
PM(분배·기준 제시)
  └─▶ lyricist : 가사 KO/EN 작성 + 미학 검수 → PM에 초안 회신
        └─▶ PM 채택
  └─▶ engineer : python pipeline.py --steps align → video (렌더) → PM에 산출물 회신
        └─▶ PM 확인
  └─▶ qa-gate : selftest + DoD 체크 → 합격/반려 회신
        └─▶ PM : 합격 시 발행 결정 → CONTEXT.md 갱신
```

각 단계는 **PM을 거쳐** 다음으로 넘어간다. 에이전트→에이전트 직접 연결 없음(판단 우회 방지).

---

## 4. 정의(Definition of Done) — qa-gate 검사 항목

1. KO/EN 줄수 1:1
2. `python scripts/selftest.py` PASS (자막엔진 색분리·채움)
3. 영상이 1440p·H.264 High·BT.709·AAC 384k 프로파일
4. 곡 폴더에 음원·가사·커버·산출물 보존
5. 미학 헌장 준수: 직접 진술 없음 · 장소=은유 · 수미상관 · **양산형 아님**
6. 메타데이터(제목·설명·가사·태그) 채워짐
