# HADES PROJECT — SESSION HANDOFF & LOOP ORCHESTRATION
> Language: English (fastest for Claude to parse; communication with 영석고고 remains formal Korean 존댓말)
> Last updated: 2026-07-06 (full replacement — HADES FINAL architecture, current rules, merged track ledger)
> Supersedes: ALL prior CONTEXT.md versions, CONTEXT2.md, and any CONTEXT (n).md duplicates.
> Exactly ONE CONTEXT.md must exist, at repo root. Delete every other CONTEXT-named file on sight.

---

## 0. MANDATORY FIRST ACTION — MEMORY PROTOCOL
Every session, before responding to 영석고고, Claude must:
1. Recall this entire file in detail — not a skim.
2. If anything is uncertain (track history, standards, unresolved items, preferences),
   search past conversations first (conversation_search / recent_chats). Never assume "없음".
3. Never ask 영석고고 to repeat anything established here or in past chats.
4. This file is authoritative over Claude's conversational memory when they conflict.
This rule does not degrade over the session.

---

## 1. ROLE MODEL
- **Navigator = Claude chat (CS, outside the loop)**: all judgment — research, lyrics,
  standards, sequencing, risk, go/no-go, exception approvals.
- **Executor = Claude Code**: runs only confirmed decisions, provided as copyable
  instructions. Stops at every gate. Never self-approves. Ambiguity → return to Navigator.
- **Commander = hades_loop.py (code, NOT an LLM)**: deterministic state machine that
  dispatches modules per tick once built. Claude Code is the *hand* that operates the
  commander; the commander itself is code so state survives session loss (state.json).
- **Watchers = hooks (code, exit-2)**: mechanical interdiction between decisions and actions.

Navigator discipline (recorded failures — do not repeat):
(1) Answer questions in the same turn asked.
(2) Never reverse a confirmed decision without checking charter + prior decisions first.

---

## 2. HADES FINAL ARCHITECTURE (confirmed 2026-07-03/04 — supersedes pipeline.py --auto)

**Composition: 14 units + CS. Exactly 3 LLM seats inside the loop. Everything else is code.**

| Unit | Role | Model | Status |
|---|---|---|---|
| CS 네비게이터 | standards·design·exceptions | Claude chat (Opus-class), outside loop | — |
| 대장 hades_loop.py | state machine·dispatch·1/day cap·HOLD·brief | code | **NOT BUILT** |
| 전령 courier.py | Telegram sendMessage (brief/HOLD) + getUpdates polling (phone approvals) | code | **NOT BUILT** |
| preflight.py | md5+duration ↔ FINGERPRINTS, lyric line counts, font | code (CLI --track/--all/--register) | **live (2026-07-09; 13곡 지문 검증, donghae KO/EN 애드립 불일치 포착)** |
| cover_smith | fal_bg v3 + cover_render --bg composite | code (bg = fal FLUX.2 pro) | live |
| gate1_verify | tone_check histogram + scene_check + composite integrity → .cover_ok | code + LLM below | live |
| **scene_check** | Gate 1 visual judgment (lyric-anchor consistency, no faces/text) | **Sonnet 4.6 vision** (headless) | live |
| align_sub | MMS_FA + dual ASS | code | live |
| encode | CRF16 render + ffprobe 9 items + **item 10: render date ≥ spec date** | code | live (item 10 new) |
| make_shorts v2 | dedicated vertical re-render 1080×1920, **clip 20–40s (chorus-hook-priority: shortest length that fully captures the chorus hook; no forced extension); chorus auto-detect min-length param = 20s**, shorts-only ASS | code (portable, stdlib+ffmpeg) | **live (amumaldo proven: 56.01–82.43=26.4s, Gate2 10/10)** |
| upload_scheduler | cadence cap·ledger·main↔shorts alternation·disclosure | code | **live (geureoke proven)** |
| **meta_gen** | per-track description/tags | **Haiku 4.5 → Sonnet escalation** on duplication threshold | not built |
| watchdog | stall/orphan-lock/claude-p-timeout monitoring | code | not built |
| **auditor 암행어사** | 1-in-5 published-output audit, bypasses commander, reports direct to CS | **Sonnet 4.6 vision** | not built |
| 헌병 hooks ×3 | cover_gate·secret_guard·danger_guard | code (exit-2) | live (d972c6d) |

**Commander spec (locked):** runs via schtasks as resident Python process; lockfile
(no duplicate execution); idempotent ticks; every dispatch/hold/publish written to
decision_log.jsonl with rationale; daily 3-line brief → courier → phone.

**Headless LLM call standard:** all `claude -p` calls use
`--bare --output-format json --allowedTools <minimal set>` — prevents interactive stalls.

**Courier security:** chat_id allowlist (one user), command format validation,
TELEGRAM_BOT_TOKEN registered in secret_guard patterns. No dependency on Claude
Channels preview (message-loss + silent-stall risk).

**Safety caps:** fal re-seed max 3 attempts → HOLD_COVER. Shorts render deferred to
UPLOADED+1 day. Human touchpoints fixed at three: Suno generation · HOLD approvals
(phone/Telegram) · spot-check = reviewing auditor's report (not rewatching video), 1 per 5 uploads.

### State machine
```
INGESTED ─preflight→ READY ─cover_smith→ COVER_WAIT ─gate1(auto)→ COVER_OK
 ─align_sub→ SUBBED ─encode→ ENCODED ─gate2(9+1)→ APPROVED
 ─scheduler(1/day cap)→ UPLOADED ─(+1 day)→ SHORTS_QUEUED ─scheduler→ SHORTS_UP → DONE

HOLDs (human via Telegram): HOLD_IDENTITY (preflight mismatch) ·
HOLD_COVER (2 consecutive scene_check fails / re-seed cap) · HOLD_QC (gate2 fail)

instrumental branch: skips align_sub + SUBBED entirely; Gate2 = ffprobe + fingerprint only.
```
Concurrency: encode strictly serial (CPU-bound, one at a time); other modules may
run across tracks in parallel. Publishing: commander enforces 1/day regardless of queue depth.

### Gate 1 automation (charter §1.4 sign-off, 2026-07-03)
Human cover tap RETIRED as default. Replaced by triple chain: tone_check histogram →
scene_check (Sonnet vision) → composite integrity. Exception: 2 consecutive scene_check
failures → HOLD_COVER + Telegram notification.

---

## 3. KEY RULES (never violate)
- **Lyrics delivery — RULE REVERSED (2026-07-02, supersedes all prior versions):
  lyrics are ALWAYS typed in chat as code blocks for copy-paste. NEVER present_files /
  download files. Chat code blocks confirmed the most stable method.**
- gwanramcha (관람차): CANCELLED. Never raise as a candidate.
- geoul_oneul (거울속의 오늘): CLOSED golden reference. Do not touch.
- 간다 말했다: memorial elegy for a friend who died by suicide. Navigator handles cover
  and tone DIRECTLY. No romantic framing. Memorial/twilight concept only.
- Gate 1: .cover_ok required before encode, every render, no stale carryover.
- Gate 2: 9 ffprobe items + item 10 (render date ≥ final spec confirmation date) all pass.
- No upload fires outside upload_scheduler's cadence cap. 1/day total (main+shorts),
  shorts never same day as its main video (+1 day minimum), main↔shorts alternation.
- Executor never self-approves at any gate. Commit after Navigator sign-off; push separate.
- Suno: Style field English descriptors only (no real artist names — moderation).
  Lyrics field Korean-only + English section tags. Instrumental toggle OFF always
  (ON locks the lyrics field; suppress vocals via style descriptors + tags instead).
- HADES.md charter edits require explicit Navigator sign-off even for factual fixes.
- Every new session: reread §0 and search past conversations before assuming absence.

---

## 4. VISUAL / COVER STANDARDS (confirmed 2026-07-02/03)
- **Lyrics-first direction:** cover background derives from the song's lyric content
  (emotion, scene, narrative) — never genre defaults or other-track references.
- **Tone mandate:** always bright, blue, vivid, high-key — clear blue sky / azure /
  crisp daylight. BAN: golden-hour, warm, sepia, film-wash, haze, muted/grey, gloom.
  Negative prompt must include: `no yellow tint, no sepia, no film wash, no haze,
  no muted/grey, no gloom`.
- **fal prompt v3:** scene anchor front-loaded from cited lyric lines → camera/composition
  mid → color grade rear. Ocean/sky words BANNED from scene slot unless present in lyrics.
- 2–3 seed candidates generated; re-seed cap 3 → HOLD_COVER.
- Immutable signature layers (code, always last): Reina sign top-right · dither ~1.5 LSB ·
  bright tone · title typography · 64×64 survival.
- Known quality issue (open): fal output 1024×576 → ~5× upscale blur; reduce center glow,
  raise bg resolution. Tuning pending.

## 5. TECHNICAL STANDARDS (confirmed — no change without separate sign-off)
- **fal cover models: text2img backgrounds stay FLUX.2 pro (`fal-ai/flux-2-pro` / `.../edit`).
  EXCEPTION — img2img with strength control uses FLUX.1 dev (`fal-ai/flux/dev/image-to-image`),
  because flux-2-pro/edit does not expose a `strength` parameter. Applied to kkotboda (꽃보다)
  person-cover img2img (Navigator-approved 2026-07-08). fal_bg.py: `--input-image/--strength`,
  MODEL_IMG2IMG. Source image is fal-upload-only; local original preserved; enable_safety_checker=False.**
- Video: libx264 · CRF 16 · preset medium · 1-pass · 2560×1440 · 30fps
- Audio: AAC 48kHz ~380k · Color: H.264 High · yuv420p · BT.709 tv · moov@front
- Subtitles: Malgun Gothic · **subtitle.scale = 1.15** (base 110 → KO 126 / EN 103,
  margins/gap recalculated proportionally; code default and config unified) ·
  KO gold `&H0000D7FF` karaoke · EN cream `&H00BED7DC` · PlayRes 2560×1440
- Alignment: torchaudio MMS_FA (.venv-align, Py3.11, torch CPU, uroman) —
  align.json is the single source of truth
- Instrumental type: no subtitles; 2–3 fal scene transitions MANDATORY (policy defense,
  not aesthetics); RMS-energy-based scene boundaries (not equal splits); ≤3 scenes;
  same palette/style family across scenes; title+Reina signature first scene only;
  BGM motion = one short transparent RGBA particle loop in Python → ffmpeg compositing
  (per-frame Python generation retired — too slow on CPU-only machine)

---

## 6. TRACK LEDGER (2026-07-06 merged state)

| Track | Slug | Type | State |
|---|---|---|---|
| 그렇게 지나간다 | geureoke | vocal | **PUBLIC — verified via YouTube API 2026-07-07 (privacyStatus=public, madeForKids=false), video oeWC8JtWDTs. Prior "unlisted/pending" note was stale; decision resolved, no action.** |
| 송도유원지 | songdo | vocal | Uploaded manually, ledger backfilled, first scale=1.15 render, fal composite. **Pending: Studio 합성콘텐츠 disclosure toggle + unique description check (web UI, reina2hj account)** |
| 아무말도 | amumaldo | vocal | Rendered, PC pass, cover confirmed + gate1 승인 (ce448fa). **PUBLIC 2026-07-08 — scheduled task fired 09:03 (unlisted upload, video LNv510hamvw, ledger n=3), Studio synthetic-content disclosure set, flipped unlisted->public via API 2026-07-08T12:06 (embeddable/publicStatsViewable=true). Prior "un-uploaded/7-03 auto" confusion fully resolved.** |
| 봄날 | bomnal | vocal | **PUBLIC 2026-07-07 — video Qvs-Npkyub8 (root ledger n=2 + manifest). Uploaded unlisted via scheduler, Studio 합성콘텐츠 disclosure toggled ON, then flipped unlisted->public via API (embeddable=true, publicStatsViewable=true, madeForKids=false). Unique description. Consumed 2026-07-07 cadence slot.** **REPLACEMENT 2026-07-08 — MANUAL UPLOAD BY COMMANDER: new-cover re-render (fal img2img... no, txt2img seed 484202, color_field; Gate1 waive-logged _gate1_verify.log; G2 10/10 PASS; bomnal_dual.mp4 161,090,407B @13:38:58; old 62.5MB backed up _pre_newcover_*). Excluded from auto-schedule (no schtasks). Idempotent ledger block active (upload_scheduler skips any track already in upload_ledger). Ledger n=4 = bomnal manual, video_id TBD (backfill after 선생님 uploads via Studio). Old Qvs-Npkyub8 (n=2) to be retired: private 24h -> delete after new goes public.** NOTE: OAuth scope bug fixed (upload_youtube.py SCOPES upload->force-ssl); upload_scheduler instrumental(_bgm.mp4) + ledger-idempotency guards added. |
| 동해로 | donghae | vocal | **GATE1 APPROVED 2026-07-07 — new fal bg 328806 (native 2560×1440, tone_check OK: bright141/sat113/warmR-B −64/gray0.24) selected by PM scene_check, composited via cover_render (color_field, title 동해로/To the Sea + Reina), .cover_ok signed sha256 f5e71343. RE-RENDERED 2026-07-07 13:08 with new cover (donghae_dual.mp4 190.7MB, 210.8s), G2 10/10 PASS (incl. item 10 render date ≥ approval date). PUBLISH-READY. SCHEDULED 2026-07-09 09:00 (schtasks HADES_donghae_0709, Interactive-only → PC must be logged in; unlisted staging + ledger + log via _sched_publish_0709.py; unique description written). Public flip needs manual Studio synthetic-content disclosure on 07-09.** |
| 옥련동 | okryeon | vocal | Lyrics placed (28 KO/EN). Queued as first Gate-1 unmanned-verified track |
| 그날의 오월 | owol | vocal | Lyrics delivered (31 KO/EN; scene anchor: May park path, solitary figure, NO ocean). **Staged as first fully unattended end-to-end proving run** |
| Early Morning Radio | radio | instrumental | **DONE 2026-07-07 — BGM motion v1 built (12s seamless qtrle loop, particles+notes, bpm72, glow omitted), Gate1 PASS (.cover_ok 6906708716e0), CRF16 encoded radio_bgm.mp4 (128MB, 194.4s), Gate2 PASS (30fps per config/CONTEXT §5; CLAUDE.md §4.1 "60fps" is a stale line — flag for charter fix). publish_hold lifted. Fixed bgm_motion._pipe_qtrle stderr-PIPE deadlock + upload_scheduler instrumental (_bgm.mp4) naming. GATE1 FORMALLY RE-RUN 2026-07-08: tone_check PASS + scene_check.py actually executed on bg-only (raw FAIL on no_face_no_text = radio's diegetic brand/dial text) -> Navigator WAIVED (diegetic object lettering, logged _gate1_verify.log + decision_log.jsonl), .cover_ok re-issued 11:48 (same hash). Gate2 10/10 PASS (item10: render after original approval; re-issue same-hash). RE-SCHEDULED 2026-07-10 09:00 (HADES_radio_0710, Interactive-only). Public flip needs manual Studio disclosure 07-10.** |
| 마지막 순간 | majimak | instrumental | Design confirmed (120 BPM, piano/strings lead, soft brass final hook only, Dm→F). Awaiting Suno generation |
| 간다 말했다 | ganda | vocal | HOLD — memorial protocol (§3) |
| 물길 | mulgil | vocal | Lyrics confirmed (hook option B), contemporary acoustic indie folk. Awaiting Suno |
| 담배연기 곡 | (slug TBD) | vocal | Lyrics+style confirmed (~102 BPM neo-soul groove). Slug assignment pending |
| 지나간 불빛 곡 | (slug TBD) | vocal | Lyrics confirmed (original preserved), B Dorian Bm11–E9 vamp, 88 BPM. Slug pending |
| 거울속의 오늘 | geoul_oneul | vocal | CLOSED golden reference |
| 변함없는 노을 · 그림자 (+legacy pool) | — | vocal | Old 1080p exists, redo needed, unpiped |
| 관람차 | gwanramcha | — | CANCELLED |
| 꽃보다 오렌지 보다 너 | kkotboda | vocal | **DONE 2026-07-08 — Ghibli-watercolor img2img PERSON cover (FLUX.1 dev exception `fal-ai/flux/dev/image-to-image`, drama93b brown-hair, 세로→16:9 canvas-composite bg_kkotboda.png). Gate1 PASS (.cover_ok da78f73a; scene_check allow_person). Lyrics KO/EN 18 each (EN=PM translation), MMS_FA align, CRF16 kkotboda_dual.mp4 (62,104,086B / 204.8s), Gate2 9+1 PASS (dual subs KO126/EN103 verified). Audio md5 4f412257 (FINGERPRINTS). SCHEDULED 2026-07-11 09:00 (HADES_kkotboda_0711, unlisted staging). Code: cover_render+kkotboda, scene_check+allow_person, fal_bg img2img.** |
| 그날 | geunal | vocal | **커버 DONE 2026-07-08 — DARK CYBERPUNK AI bg (txt2img FLUX.2 pro, seed 30401 a.jpg, 2560×1440, NOT photoreal). Gate1 PASS (.cover_ok 28199d6b) with 2 Navigator waives: tone_check FAIL (dark, §4 bright-blue mandate deliberately overridden) + scene_check no_face_no_text FAIL (diegetic cyberpunk neon signage). Audio audio.mp3 (md5 94c72b2c, 169.24s), FINGERPRINTS 등재, config.yaml. Lyrics KO/EN 28 each (Korean-sung — KO align basis; EN Navigator-provided, V1 +1 line to match KO). MMS_FA align (28 lines, real not fallback), CRF16 geunal_dual.mp4 (136,001,247B / 169.24s), Gate2 9+1 PASS (dual KO-top/EN-below verified @t=12s). SCHEDULED 2026-07-12 09:00 (HADES_geunal_0712, unlisted staging).** |

Inventory scale: ~25–30 tracks ready overall (FINGERPRINTS.md), 100+ long-term.
Catalog harmonic rotation: three grammar families (functional / modal vamp / pedal point)
tracked per track to avoid catalog-wide sameness.

---

## 7. RECURRING ERROR CLASSES & COUNTERMEASURES (audit 2026-07-04)

| # | Error | Root cause | Countermeasure | Status |
|---|---|---|---|---|
| 1 | Audio↔track mismatch (donghae incident; 봄날그방.mp3) | no identity check | preflight.py fingerprints | NOT BUILT |
| 2 | Stale-spec render approved (bomnal) | no date check | G2 item 10 | INSTITUTED |
| 3 | Double-nested folders / misplaced client_secret | repo path | C:\hades migration | **VERIFY DONE** |
| 4 | OneDrive locking/placeholder during renders | repo in OneDrive | same migration; OneDrive = free 5GB cold storage for audio originals ONLY, no pipeline role | **VERIFY DONE** |
| 5 | fal bg upscale blur / center glow | 1024×576 source | resolution↑ glow↓ tuning | OPEN |
| 6 | Executor gate self-approval drift | oversight gap | G2 item 10 + auditor direct-to-CS line | auditor NOT BUILT |
| 7 | Unexplained render-time variance (8min vs 25–30min) | unknown | one-line note in RESULT.txt per track; investigate zoompan/system load | OPEN |
| 8 | PowerShell hook blind spot | matcher covers Bash/Read/Edit/Write only | extend matcher | OPEN |

---

## 8. BUILD ORDER (confirmed plan, 2026-07-06)
```
0. VERIFY C:\hades migration complete (robocopy result·git remote·render run) — first Executor task
1. CONTEXT replacement (this file) — commit after Navigator sign-off
2. preflight.py (P0 — closes error #1)
3. hades_loop.py + courier.py built together (brief needs a destination)
4. watchdog.py (same week as commander)
5. donghae date check → publish queue cleanup (incl. amumaldo ledger reconciliation,
   geureoke public-visibility decision)
6. owol fully unattended end-to-end run — first unmanned proof
7. make_shorts.py v2 → main↔shorts alternating publication begins
8. auditor.py — effective from 5 accumulated uploads
9. meta_gen → threads · radio BGM motion rebuild · majimak & BGM line intake
```
Rationale for owol before full batch: proving the unmanned chain before commanding it
(charter §7 — no building HQ from unverified parts). MV tooling investment FROZEN until
channel revenue (decision 2026-07-03).

## 9. ENVIRONMENT & ACCOUNTS
- Repo: `C:\hades` · GitHub `foob0201-alt/music-pipeline` (private)
- YouTube: `reina2hj@gmail.com`, handle `@reinamusic_0217` — firewalled from business
  account `foob0201@gmail.com` (cross-account ToS cascade defense). OAuth client_secret
  reused from TAEYEON ERP GCP project, token cached.
- Instagram: Reina creator account CREATED (2026-07-09), handle `@reinamusic_0217`
  (unified with YouTube handle). Account type: Creator (Business 전환 가능 — 릴스 빌드 시
  Graph API 호환 재확인 항목). Bio link = https://youtube.com/@reinamusic_0217
- Upload quota (corrected 2026-07): ~100/day dedicated bucket — quota is NOT the constraint;
  **cadence/pattern is** (channel-level inauthentic-content enforcement). Honest synthetic-
  content disclosure per upload; unique human-written description per video.
- Machine: no discrete GPU (UHD 610) — encode permanently CPU-bound; QSV preview only.
- fal.ai FLUX.2 pro — FAL_KEY user-level env var, os.environ only, secret_guard enforced.
- Remote work: VS Code Remote Tunnels chosen; one-time desktop setup (tunnel service +
  powercfg sleep-off) NOT YET DONE — must be performed physically at office.
- Monetization path: YPP (1,000 subs + 4,000 watch-hrs) → DistroKid EP/album bundles.
  Korean DSPs on hold.

---

## 10. SESSION UPDATE 2026-07-09 (2nd)
완료 처리:
- 4) IG 계정 세팅 완료 — 크리에이터 계정 생성·핸들 @reinamusic_0217 확정 (07-09)

유지 사항:
- IG 연동(FB 페이지 연결·Meta 앱·Graph API 토큰) 착수 조건 확정: 숏츠 실발행 검증 통과 후
  (07-11 amumaldo 숏츠 발행 확인이 트리거).
- 릴스 소급분: 큐 일괄 적재 허용, 실발행은 캐던스 순차 (신규 계정 스팸 감지 방어 —
  1일 1~2건, reels_post.py 설계에 반영).

예외 (일회성, 영구 규칙 변경 아님):
- 캐던스 일회성 예외 — Commander 승인 2026-07-10: 1일 1건 캡을 **07-10~07-12** 숏츠 백로그
  소진 건에 한해 **1일 2건**으로 일시 해제. **07-13부터 정상 캡(1일 1건) 복귀.**
- donghae 숏츠는 메인 수동 업로드 완료 + (메인+1일) 조건 충족 후 07-13 이후 별도 편입
  (이번 창에서 제외). → **갱신 07-10: Commander가 donghae 숏츠를 07-12에 명시 편입(위 제외 상회).
  단 donghae 메인은 여전히 수동 미업로드 상태.**

숏츠 v2 (제목 오버레이 + EN 마진 수정 60→96 + @reinamusic_0217 핸들) — 5곡 재렌더 완료(07-10):
- PUBLIC 발행 예약(2/day 예외): **07-11 geureoke·songdo / 07-12 bomnal·donghae / 07-13 radio.**
- 5건 소진 후 예외 종료 → 정상 캐던스(1일 1건) 복귀. 오늘(07-10)은 추가 발행 없음(캡 초과 확인).
- 기발행분 amumaldo·kkotboda·geunal 숏츠는 v1 그대로(미변경). 구 예약 스크립트 8개 정리.
- 합성콘텐츠 고지는 Data API 설정 불가 — public 발행 후 Studio 고지는 Commander 책임.

---

## SESSION UPDATE 2026-07-10

### 완료
- amumaldo/kkotboda/geunal 숏츠 발행 (당일 1일2건 예외 중 4건 집행 — Navigator 지시 오류, 재발 방지 기록)
- unlisted 6건(메인 radio·kkotboda·geunal, 숏츠 amumaldo·kkotboda·geunal) → public 전환 완료
  (재업로드 없음, privacyStatus만 변경, 조회수/URL 유지)
  ※ 합성콘텐츠 고지 토글은 API 확인 불가 — 사전 완료 전제. 미완료 시 Studio 직접 확인 필요
- 숏츠 EN 자막 잘림 수정: 좌우 마진 60→96px, 2줄 자동 줄바꿈 (make_shorts.py 기본값 반영)
- 숏츠 제목 오버레이 신규: 상단 세이프존, Malgun Gothic Bold 64px, 흰+아웃라인, 0.4s 페이드인
  + 하단 좌측 @reinamusic_0217 핸들 (v2 사양 확정, 기본값 반영)
- 미발행 숏츠 5곡(geureoke·songdo·bomnal·donghae·radio) 신규 사양 전량 재렌더 완료.
  기발행 3곡(amumaldo·kkotboda·geunal)은 구버전 유지, 재작업 없음

### 미결 — 다음 세션 최우선
1. 신규 숏츠 5건 발행 확인: 07-11 geureoke·songdo / 07-12 bomnal·donghae / 07-13 radio
   (1일2건 예외 소진 후 1일1건 복귀)
   > (Executor 검증 2026-07-13: 5건 전량 public 발행 확인 — geureoke uAdqXyCI2bA · songdo PRUPCNpie-k
   >  · bomnal GnkpE752a1w · donghae tLwx83-uPGQ · radio Emi99FTLotA. 작업 스케줄러 3일 정상 발화.)
2. bomnal 메인 — 구버전(public, 조회수 보유) vs 신커버 재렌더본(Qvs-Npkyub8) 교체 여부 미확정
   (교체 시 조회수/좋아요 리셋 인지 필요)
3. IG 연동 — Meta 전화인증(SMS) 실패로 보류. 재시도 또는 카드 인증 경로 전환 필요.
   Facebook 페이지(Reina-music)·IG 크리에이터 계정(@reinamusic_0217) 생성 완료, 연동만 미완
4. donghae 메인 미업로드 — 07-12 donghae 숏츠 발행 전 메인 업로드 필수 확인
   > (Executor 검증 2026-07-13: donghae 숏츠는 07-12 public 발행됐으나 donghae 메인은 여전히 미업로드
   >  — 메인 없이 숏츠만 공개된 상태. 확인 필요.)
5. 백로그 전수 인벤토리 표 — 계속 이월 (Executor 미보고)
6. kkotboda·geunal Studio 고지 재확인 — public 전환 전제 항목, 실제 완료 미검증
7. reels_post.py 설계 — IG 연동 후 착수

### 참고
- 캐던스 초과(4건) 재발 방지: 발행 앞당김 지시 전, 당일 기예정 건수 선확인을 Navigator 프로세스에 반영

---

## 11. YPP & CADENCE (2026-07-13 확정)

### YPP 2단계 구조 (Navigator 확정)
- **Tier1 (수익화 진입 기반):** 구독 **500** + (90일 **숏츠 300만뷰** 또는 **3,000 공개 시청시간**)
  + 90일 내 **공개 업로드 3건**.
- **Tier2 (정식 YPP):** 구독 **1,000** + (**4,000 시청시간** 또는 **1,000만 숏츠뷰**).
- **집계 주의:** 숏츠 시청시간은 **4,000시간에 미집계**(숏츠뷰 경로로만 카운트).
  **unlisted 시청은 어느 지표에도 미집계** → 반드시 public 상태에서 노출돼야 함.

### 지표 추적
- `hades/ypp_tracker.py` (주 1회) — channels.list statistics로 구독/누적조회수/공개영상 조회,
  결과 STATUS.md append. **90일 숏츠뷰는 Analytics API 필요** — 미연동이라 누적 조회수 프록시 사용.
- 현재(2026-07-13): **구독 7/500 · 숏츠뷰(프록시) 2,273/3,000,000 · 공개영상 19건**.

### DSP 트리거 재정의 (Navigator 확정)
- 기존 "YPP 후 DistroKid" → **"YPP Tier1 진입 또는 30곡" 중 먼저 도달 시** DSP 배포 착수.

### 자격·인증
- **2FA·고급 인증 = YPP 신청 자격 조건** (선생님 웹UI 작업 진행 중).

### 캐던스 규칙 강화
- **48시간 내 연속(2건+) 업로드 지양** — 임프레션 풀 분산 방지. 정상 캐던스 **1일 1건** 유지.
- **1일 2건 예외는 향후 재검토**(원칙상 지양; 백로그 소진용 일회성으로만 사용됐고 종료됨).

---

## 12. GLOBAL META & CHANNEL RECON (2026-07-13 확정)

### 글로벌 메타 표준 (P0)
- **모든 업로드:** `snippet.defaultLanguage="ko"` + `snippet.defaultAudioLanguage="ko"`
  + `localizations["en"]{title,description}`. EN 제목 = 표준 제목의 " / " 뒤 부분,
  EN 설명 = youtube_description EN 인트로 + lyrics_en(인스트루멘털은 (Instrumental)).
- 구현: `upload_scheduler.insert_video`(ko 항상 + localizations 옵션), `hades/localize.py`.
- **소급 완료:** 기존 **15건**(메인 7 + 숏츠 8) videos.update 성공 15/15.
  donghae 정규 메인 미업로드 → 16번째 메인 부재.

### 숏츠 표준 수정 (07-13, docs/shorts_multi.md §8)
- 컷 길이 **30~40초**(자연 가사 단락), 루프 회귀 우선.
- 해시태그 **3~5개 + 영어 카테고리 1~2 필수**(#koreanmusic/#koreanballad/#kindie/#kpopballad),
  **#viral·#fyp 금지 유지**.
- 발행 시각 **±2~3시간 지터**, 3컷째 승격 = **Viewed vs Swiped 75%+ AND 시청률 65%+**.
- EN 오버레이 = KO 동등 가독성(해외 시드 리텐션).

### 채널 실측 원장 갱신
- 채널 실제 **19건** ↔ 원장 백필 **+5건**(video_id 전량 일치). 삭제·제목수정 미실행(보고만).
- **구 중복(조치 대기):** 봄날 `Qvs-Npkyub8`(표준)+`8OppJiu2yzw`(구) / 그렇게지나간다
  `oeWC8JtWDTs`(표준)+`InpBTqQ3Vz4`(구) / 새벽라디오 `2MR5024HnM8`(표준)+`zAWY-8JZSnU`(구).
- **동해로 제목 이탈+핸들 오타:** `TW4-OXXoBeU` "@동해로 @reinamusic_2017"(정본 @reinamusic_0217).

### 지표
- `ypp_tracker` 지역(Analytics) 확장 — **yt-analytics.readonly 스코프 미보유로 미연동**
  (재인증 + API 사용설정 필요). 현재: 구독 7/500 · 공개영상 19.

---

## 13. SESSION 2026-07-13 (owol 무인 런 + Analytics 연동)

### owol 무인 실증 런 완주 — 첫 무인 end-to-end (이정표)
- 「그날의 오월」(owol) — 사령관 정본 가사 31행(1:1). **전 단계 자동판정 PASS:**
  cover_smith(fal 3후보 tone 3/3) → Gate1(scene_check 3/3, 오월 산책로+미스트, .cover_ok)
  → align(MMS_FA 31줄) → subtitle(ASS 31/31) → encode(CRF16, **Gate2 9/9 PASS**)
  → **public 업로드** `OUb-2MJHyYo` (ko default + en localization "That Day in May - Reina").
- ※ 07-13 총 2건(radio_shorts 자동발행 + owol 메인) — 정상 캐던스(1일1건) 대비 1건 초과.
  사령관 "오늘 공개 슬롯" 명시 지시로 집행. 합성콘텐츠 고지는 Studio 확인 필요.

### align CPU 타임아웃 표준 (재발 방지)
- config.yaml align: `cpu_timeout_mult: 6` / `cpu_timeout_floor_sec: 1200`
  = **max(audio_sec×6, 1200s)**. owol 첫 런 560s 중도종료 사고 방지(GPU 없음, CPU 추론 장시간).

### YouTube Analytics 연동
- 재인증(force-ssl + **yt-analytics.readonly**) 완료. `ypp_tracker` 지역 데이터 라이브.
- 90일 실측: **KR 1,837뷰(100%) · 해외 유입 0.0%** (글로벌 메타 적용 초기). 구독 7/500.

### 채널 정합
- donghae `TW4-OXXoBeU` 표준화(「동해로」/ To the Sea - Reina, ko+en, 핸들오타 제거) 채널 확인.
- 비표준 3건 비공개 재확인 — `InpBTqQ3Vz4`(지난 세션 전환 미지속) 재전환 private 완료.

---

## 14. SESSION 2026-07-14

### IG 크로스포스트 (결정 변경)
- **IG 크로스포스트 = 수신 채널로 승격.** 구현 = IG "Facebook에 공유" **자동 토글**(별도 업로드 모듈 없음).
- 활성 시점 = **IG↔FB 페이지 연결 완료 직후**(릴스 빌드와 무관하게 토글만 선행 가능).
- **FB 페이지 핸들 오타 `@reinamusic_2017` → `@reinamusic_0217`** 미확인 — 토글 켤 때 함께 처리.
  (YouTube 쪽 동해로 핸들오타는 07-13에 이미 수정. 이번 건은 **FB 페이지** 핸들.)

### ganda(간다 말했다) — 추모곡, 무인 아님
- 정본 가사 35행(1:1). KO 1행 "나에게 간다 했다"(EN "He Told Me He Was Going") 추가로 35=35.
- **커버 확정:** 다크 트와일라잇 도로 소실점(fal skip-tone, A/991329), 「간다 말했다」/ He Told Me He Was Going,
  scene_check PASS, `.cover_ok`. (밝은톤 tone_check는 이 곡 한정 스킵 — fal_bg `--skip-tone` 신설.)
- **align OOM:** 258.92s 풀패스 MMS_FA 메모리 부족(1.7GB) → **청크 align 빌드 승인**.
  요구: 무음경계 컷(고정길이 금지)·청크별 타임스탬프+전역 오프셋 병합·검증·**owol 회귀 ±0.3s**.
  1차 concat-emission 구현은 회귀 FAIL(경계 불연속 5~9s) → **청크별 독립정렬 2-pass로 재구현 중.**

### 인테이크
- **salpyeoga(살펴 가)** — onedrive 172.60s = 신규 **댄스록 개사판**("괜찮아 나는 뛰어" 훅).
  audio+FINGERPRINTS+config, **정본 KO/EN 43행 확정**(1:1). 구 nu-disco판 161.88s는 _incoming_review 보류(삭제 금지).
- **makes_me_sick_edm(역겨워 Dark EDM)** — audio+FINGERPRINTS(md5 3bdc12f4, 212.48s).
  ⚠️ **전사 블록** — faster-whisper(av 빌드)·openai-whisper(SSL) 설치 실패. 재시도/오프라인 wheel/가사 직접 대기.

### 표준
- align CPU 타임아웃: `config.yaml` `cpu_timeout_mult:6`/`floor:1200` = max(audio×6,1200s).
- fal_bg `--skip-tone`(다크 톤 곡 밝은톤 임계 스킵) / `scripts/align_mms.py --chunk-sec`(장곡 청크, 구현 중).
