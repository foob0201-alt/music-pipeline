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
| preflight.py | md5+duration ↔ FINGERPRINTS, lyric line counts, font | code | **NOT BUILT (P0)** |
| cover_smith | fal_bg v3 + cover_render --bg composite | code (bg = fal FLUX.2 pro) | live |
| gate1_verify | tone_check histogram + scene_check + composite integrity → .cover_ok | code + LLM below | live |
| **scene_check** | Gate 1 visual judgment (lyric-anchor consistency, no faces/text) | **Sonnet 4.6 vision** (headless) | live |
| align_sub | MMS_FA + dual ASS | code | live |
| encode | CRF16 render + ffprobe 9 items + **item 10: render date ≥ spec date** | code | live (item 10 new) |
| make_shorts v2 | dedicated vertical re-render 1080×1920, 0–32s, shorts-only ASS | code | **NOT BUILT** |
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
| 그렇게 지나간다 | geureoke | vocal | **UPLOADED via scheduler (first auto upload), video oeWC8JtWDTs, unlisted — public-visibility decision pending** |
| 송도유원지 | songdo | vocal | Uploaded manually, ledger backfilled, first scale=1.15 render, fal composite. **Pending: Studio 합성콘텐츠 disclosure toggle + unique description check (web UI, reina2hj account)** |
| 아무말도 | amumaldo | vocal | Rendered, PC pass. **Upload status CONFLICTED in records (auto-uploaded 7-03 vs pending) — verify against upload_ledger before any action** |
| 봄날 | bomnal | vocal | Re-rendered 2026-07-03 17:16 (scale 1.15, KO126/EN103, 62,515,600B). Awaiting scheduled upload. cmp byte-check old-vs-new still pending |
| 동해로 | donghae | vocal | fal-composited render exists. **G2 item 10 check pending: render date ≥ spec date — confirm before publication** |
| 옥련동 | okryeon | vocal | Lyrics placed (28 KO/EN). Queued as first Gate-1 unmanned-verified track |
| 그날의 오월 | owol | vocal | Lyrics delivered (31 KO/EN; scene anchor: May park path, solitary figure, NO ocean). **Staged as first fully unattended end-to-end proving run** |
| Early Morning Radio | radio | instrumental | Publish HOLD — BGM motion rebuild (RGBA loop→ffmpeg) + Gate 1 re-approval pending |
| 마지막 순간 | majimak | instrumental | Design confirmed (120 BPM, piano/strings lead, soft brass final hook only, Dm→F). Awaiting Suno generation |
| 간다 말했다 | ganda | vocal | HOLD — memorial protocol (§3) |
| 물길 | mulgil | vocal | Lyrics confirmed (hook option B), contemporary acoustic indie folk. Awaiting Suno |
| 담배연기 곡 | (slug TBD) | vocal | Lyrics+style confirmed (~102 BPM neo-soul groove). Slug assignment pending |
| 지나간 불빛 곡 | (slug TBD) | vocal | Lyrics confirmed (original preserved), B Dorian Bm11–E9 vamp, 88 BPM. Slug pending |
| 거울속의 오늘 | geoul_oneul | vocal | CLOSED golden reference |
| 변함없는 노을 · 그림자 (+legacy pool) | — | vocal | Old 1080p exists, redo needed, unpiped |
| 관람차 | gwanramcha | — | CANCELLED |

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
- Upload quota (corrected 2026-07): ~100/day dedicated bucket — quota is NOT the constraint;
  **cadence/pattern is** (channel-level inauthentic-content enforcement). Honest synthetic-
  content disclosure per upload; unique human-written description per video.
- Machine: no discrete GPU (UHD 610) — encode permanently CPU-bound; QSV preview only.
- fal.ai FLUX.2 pro — FAL_KEY user-level env var, os.environ only, secret_guard enforced.
- Remote work: VS Code Remote Tunnels chosen; one-time desktop setup (tunnel service +
  powercfg sleep-off) NOT YET DONE — must be performed physically at office.
- Monetization path: YPP (1,000 subs + 4,000 watch-hrs) → DistroKid EP/album bundles.
  Korean DSPs on hold.
