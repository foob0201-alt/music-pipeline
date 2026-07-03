# HADES PROJECT — SESSION HANDOFF & LOOP ORCHESTRATION

> Language: English core + Korean where confirmed verbatim. Communication with 영석고고: formal Korean 존댓말.
> Last updated: 2026-07-02 (major session: standards unification, batch-1 start, songdo complete, unattended-loop v1 signed off)
> Single source of truth. Supersedes all prior CONTEXT files.

## 0. MANDATORY FIRST ACTION — MEMORY PROTOCOL
1. Recall this entire file in detail before responding.
2. If uncertain about song history / confirmed standards / open items / preferences — SEARCH past conversations first (conversation_search / recent_chats). Never assume "없음".
3. Never ask 영석고고 to repeat anything established here or in past chats.
4. This file overrides conversational memory when they conflict.

## 1. ROLES & COMMUNICATION RULES
- Navigator = Claude (all judgment: lyrics, standards, sequencing, go/no-go). Executor = Claude Code (runs confirmed decisions, stops at gates). GATE1(cover) is now **auto-approved by the scene_check verifier** (Navigator sign-off 2026-07-03, 헌장 §1.4) — the "never self-approves" rule is superseded for cover approval by an automated verifier signature; scene_check 2-consecutive FAIL → HOLD_COVER (human intervention). Watchers = hooks (exit-2).
- Executor runs all commands; Navigator provides them in copyable code blocks. 영석고고 relays only.
- **Lyrics delivery rule (2026-07-02 confirmed):** Navigator types lyrics as plain code blocks in chat → 영석고고 copy-pastes into repo files. Do NOT deliver as download files. This is the most stable method (영석고고 confirmed).
- **Cover background principle (2026-07-03 revised, fal_bg v3 — VISUAL §3.1):** direction always from the SONG'S LYRICS. Prompt is 3-layer: **SCENE**(lyric-anchored scene; sky/water/sea only when lyrically real) / **CAMERA**(wide-shot, airy, title space, 16:9) / **GRADE**(house-fixed: `day`=high-key cool blue-leaning, or `bright_nocturne` for night songs, no deep black). **Negative prompts removed** (FLUX.2 Pro unsupported) → carried over as **positive** phrasing (vivid clean saturation · clear transparent air · high-key). Blue comes from GRADE, not forced sky/sea. genlog records scene-anchor lyric lines. 3 tone_check-passed candidates → auto GATE1 (scene_check), phone only on HOLD.

## 2. PIPELINE — CURRENT + UNATTENDED LOOP v1 (signed off, building)
Current per-track flow: ① preflight(fingerprint) → ② cover(fal FLUX.2 pro v3 3-layer + cover_render --bg) → [GATE1 auto: tone_check + scene_check + composite integrity → .cover_ok; HOLD_COVER on 2× scene_check FAIL] → ③ align(MMS_FA) → ④ subtitle(dual ASS) → ⑤ encode(CRF16 1-pass) → [GATE2] → ⑥ upload(scheduler, 1/day; spot-check 1-in-5 → upload_ledger.json) → ⑦ Threads(planned).

**Unattended loop v1 — state machine (signed off 2026-07-02, build in progress):**
NEW → FINGERPRINTED → COVER_CANDIDATES → COVER_OK → ALIGNED → SUBTITLED → ENCODED → VERIFIED → QUEUED → UPLOADED → POSTED. State in tracks/<slug>/state.json; --auto resumes from current state; per-track failure isolates (batch continues).

Build order (Executor):
1. pipeline.py --auto (state machine + resume + --status table)
2. inbox_watcher.py (OneDrive inbox/ scan, nightly 22:00 Task Scheduler batch; fingerprint→dedupe→trigger; AWAITING_LYRICS if no lyrics; check OneDrive file-lock → temp files to %TEMP%)
3. meta_gen (headless `claude --bare -p --allowedTools "Read"` → meta.json: scene one-liner per cover principle + unique title/description/tags per track; max-turns 3; Pool-2 billing so keep token-light)
4. sync_check (MMS_FA confidence score in align.json; VERIFIED = ffprobe 9 PASS + fingerprint match + score ≥ threshold[calibrate from 5 completed tracks, floor −10%]; else NEEDS_REVIEW; spot-check 1 in 5)
5. Gate1 automation ✅ DONE (2026-07-03): hades/scene_check.py — headless `claude -p --allowedTools Read` vision verdict (anchor_present · no_lyric_contradiction · no_face_no_text; model claude-sonnet-5). auto_gate1 in hades_state: tone_check + scene_check + composite integrity → approve_cover; 2-consecutive scene_check FAIL → HOLD_COVER + _notify_hold (phone push infra TODO). Per-track `cover_gate_auto: false` keeps manual (radio, pending motion build).
6. threads_post.py Phase A (upload callback → text+YouTube link, 500 chars, 1 hashtag; token refresh 60d; report web-UI click list for Meta app setup before OAuth)

Human per track after v1: Suno generation + 1 cover tap. Gate2 fully automatic + spot check.

## 3. TRACK STATE
**Completed/published:** 그렇게 지나간다 geureoke (uploaded oeWC8JtWDTs, switched to PUBLIC 2026-07-02) · 거울속의오늘 geoul_oneul (golden reference, CLOSED) · 동해로 donghae (complete) · 아무말도 amumaldo, 봄날 bomnal (complete, upload queue).
**송도유원지 songdo — COMPLETE 2026-07-02:** first track with subtitle.scale=1.15 + fal daylight-blue background (Songdo skyline + sea + drifting petals, confirmed). Gate2 9/9 PASS, 196.07s fingerprint match. In upload queue.
**Publish FIFO via scheduler (1/day):** 아무말도 → 봄날 → 송도유원지 → (옥련동...).
**Batch 1 (in progress):** 옥련동 okryeon (lyrics 28L KO/EN delivered, cover candidates via fal_bg v2 — scene must carry lyric emotion: walking the road together again, streetlights, hope, bright) · 오늘만같으면 구읍뱃터 gueup (lyrics retrieved, ready) · 그날의 오월 owol · 간다 말했다 ganda (**elegy for friend who died by suicide — memorial/twilight, NO romantic framing; Navigator handles cover/tone directly**).
**Ledger:** FINGERPRINTS.md = 25 publish tracks + hold list. Holds: 5 generic BGM stock files, bgm_may (pending vocal check vs 그날의오월), 동해로(Remastered) (completed-track no-retouch rule), 봄날 그방 (=same generation as 봄날, different encode — confirmed duplicate). Duplicated takes needing selection: If we meet again ×2, The Vow That Defies Death ×2. 그림자: only remix exists locally — original mp3 must be re-downloaded from Suno app (phone, non-urgent).
**Lyrics preload plan:** Navigator retrieves remaining lyrics from past chats batch-by-batch (5/section), delivered as code blocks. Never ask 영석고고 to re-enter lyrics.

## 4. TECHNICAL STANDARDS (confirmed — change only with sign-off)
- Video: libx264 · CRF16 · 1-pass · preset medium · 2560×1440 · 30fps. Audio AAC 48k ~380k. H.264 High · yuv420p · BT.709 tv · +faststart.
- Subtitles: Malgun Gothic · KO gold &H0000D7FF / EN cream &H00BED7DC · margins 315/201 · gap 114 · PlayRes 2560×1440 · **subtitle.scale=1.15 (2026-07-02, code default unified with config — no more dual values)**.
- Align: torchaudio MMS_FA, align.json single source of truth (+confidence score once sync_check built).
- Cover: fal FLUX.2 pro, **2560×1440 explicit pixels**, seed param + genlog per generation. fal_bg v2: house style template (daylight-blue skeleton) + --scene slot + style_ref/ multi-reference images (confirmed covers as anchors; flux-2-pro/edit endpoint, "style only, don't copy composition"; --no-ref fallback) + tone_check (brightness/saturation/yellow-cast histogram, auto-reject+reseed, max-retries) + 3 candidates.
- FINGERPRINTS.md: md5+duration ledger, verified before align, dedupe on ingest.
- danger_guard note: `git commit -F` false-positives as force-push → always use --file= or separate commit/push commands.

## 5. AUTOMATION COMPONENT STATUS
Live: hooks×3 (d972c6d) · code gate (04b3b14) · shared settings (1580a63) · fal_bg v2 (template+ref+tone_check) · upload_scheduler (proven live: geureoke) · FINGERPRINTS ledger · subtitle scale param.
Building (v1 order above): --auto → inbox_watcher → meta_gen → sync_check → gate1 phone path → threads_post.
Known gaps: PowerShell hook matcher (Tier B) · make_shorts.py (after v1; Short posts next day after main, same scheduler cap).

## 6. DISTRIBUTION & MONETIZATION (confirmed strategy)
- All tracks generated under Suno Pro (commercial rights OK). 100+ tracks long-term hobby cadence.
- Phase 1 (now): YouTube Reina channel (reina2hj@gmail.com, firewalled from business account). 1/day uploads, unique per-track descriptions (meta_gen), synthetic-content disclosure, Shorts offset by a day. Goal: YPP 1,000 subs / 4,000 watch hours + authentic-channel history. Inauthentic-content policy = cadence risk, not volume.
- Phase 2 (after channel stabilizes): DistroKid ($22.99/yr unlimited, AI-friendly) → Spotify/Apple/YT Music in EP/album bundles of 6–8 (avoids spam filter). DDEX AI disclosure. Content ID not available for fully-AI audio. Korean DSPs (Melon/Genie) ON HOLD — KOMCA suspends AI-music registration; register human-written LYRICS separately for rights protection.
- Threads Phase A after v1 build: text+link posts within same 1/day cadence.
- Phone workflow: Suno app → save mp3 to OneDrive inbox/ (1 tap) → nightly batch processes → morning cover pick on phone → scheduler publishes. Claude Code Remote Control available for gate approvals from phone.

## KEY RULES (never violate)
- Lyrics into repo: Navigator code-block typing → copy-paste (rule §1).
- Cover backgrounds: lyric-emotion direction + bright daylight-blue tone (rule §1).
- geoul_oneul CLOSED. gwanramcha CANCELLED. Completed tracks never retouched (동해로 Remastered stays on hold).
- Gate1 every render, no stale .cover_ok. **Gate1 approval is automated via scene_check verifier** (2026-07-03, §1.4) — not manual by default; re-render requires re-approval (regenerate → auto re-check). HOLD_COVER on 2× scene_check FAIL escalates to human. Uploads only through scheduler cap (1/day), spot-check 1-in-5. Executor never self-approves *encode/upload* (Gate2 + upload stay as-is).
- Commit per component, push with separate sign-off. HADES.md edits need explicit Navigator sign-off.
- 간다 말했다: memorial framing only.
- Every session: reread §0, search before assuming absence.
