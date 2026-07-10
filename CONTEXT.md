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
