# CareAuth AI — Implementation Plan for Antigravity
### Fully agent-run build, one Lead Agent + 5 subagents, no fixed time-box

**Source:** `CareAuth-AI-PRD.md` v1.0
**Adaptation:** the PRD is written for a 5-person team working a fixed 9-hour
hackathon day. This plan keeps the PRD's role split and scope in full, but drops
the clock — each phase runs until it's genuinely done, gated by quality, not by
a deadline. It re-maps the 5 team roles onto **5 parallel Antigravity
subagents**, spawned and coordinated by **one Lead Agent** — including the
contract freeze itself. You are not writing contracts or code. Your role is:
kick off the Lead Agent with one prompt, upload the PRD, and approve/reject at
two review checkpoints. Everything else is agent-executed.

---

## 0. Operating model

| PRD role | Becomes |
|---|---|
| Lead | **Lead Agent** (Antigravity, Manager Surface, main session) |
| Backend Developer | Subagent `BE`, spawned by Lead Agent |
| AI Developer 1 (RAG + Coverage) | Subagent `AI-1`, spawned by Lead Agent |
| AI Developer 2 (Documentation) | Subagent `AI-2`, spawned by Lead Agent |
| AI Developer 3 (Orchestrator + Communication) | Subagent `AI-3`, spawned by Lead Agent |
| Frontend Developer | Subagent `FE`, spawned by Lead Agent |
| You | Kick off + approve at 2 checkpoints; present the demo when it's ready |

**No phase has a time budget.** The PRD's own T+0:45 / T+3:00 / T+6:30 / T+9:00
markers existed to keep a 5-person *human* team synchronized within one working
day. That constraint doesn't apply here — the Lead Agent runs each phase until
its exit criterion is actually met, however long that takes, and moves on only
then. Below, "exit criterion" replaces every deadline the PRD used.

**Your two review checkpoints (the only places you're in the loop):**
1. **After contract freeze** — approve the frozen contracts before the Lead
   Agent spawns the 5 subagents on top of them. A bad contract here breaks all
   five downstream builds, so this one review is worth doing even though
   everything else runs autonomously.
2. **After integration** — approve that the happy-path demo actually runs
   before the Lead Agent moves into polish/rehearsal-prep.

Everything else — the Lead Agent runs on its own: it freezes the contract,
spawns and monitors five subagents in parallel, runs a completion checkpoint
once all five report done, merges their work, runs integration, hardens the
demo, and works through the polish list until the list runs out or nothing
useful remains to add.

**Why one review gate still matters, briefly:** Antigravity's own design
principle is that agents produce *artifacts* (plans, diffs, screenshots)
specifically so a human can verify before the agent's work compounds on top of
it. Skipping both checkpoints entirely means a bad contract or a broken
integration could burn a lot of five parallel agents' output before anyone
notices. Two checkpoints is close to zero manual effort, so this plan keeps
them rather than removing them.

---

## 1. Before you start (2 minutes)

1. Open Antigravity, create the `careauth-ai` project/workspace.
2. Attach or upload `CareAuth-AI-PRD.md` to the Lead Agent's context (or place
   it at the repo root as `/PRD.md` so the Lead Agent can read it directly).
3. Paste the **Master Prompt** below into the Lead Agent's Manager Surface
   session.
4. Let it run for as long as it takes. Respond only when it asks for the two
   checkpoint approvals.

---

## 2. The Master Prompt (paste once, into the Lead Agent)

```
You are the Lead Agent for CareAuth AI, a prior-authorization workflow
assistant MVP. The full product spec is in /PRD.md — read it now before doing
anything else.

There is no fixed deadline for this build. Do not time-box any phase or rush
to a clock. Each phase below has an EXIT CRITERION — move to the next phase
only when that criterion is genuinely met, however long it takes. Quality and
correctness against the PRD matter more than speed.

Your job has three parts, in order:

═══════════════════════════════════════════════════════════════
PART 1 — CONTRACT FREEZE (do this yourself, do not delegate it)
═══════════════════════════════════════════════════════════════

This is the highest-leverage work of the build: every subagent you spawn
afterward will build against what you produce here, in parallel, without
talking to each other. Get this precise or their work won't compose later —
take as long as you need to get it right rather than moving fast.

Read PRD.md §14 (AI Input/Output Contracts), §18 (Data Model), and §19 (API
Requirements) carefully — do not paraphrase or "improve" these schemas, copy
them exactly. Produce:

1. contracts/contracts.py — Pydantic models for:
   - CoverageResult (§14.1 output shape exactly, including evidence_strength as
     a derived enum high/medium/low — never a raw confidence float — and
     status including "unknown" as a valid value)
   - DocumentationResult (§14.2 output shape exactly, including mandatory flag
     and source_section on every required_document entry)
   - SubmissionPacket and ResolutionResult (§14.3, both operations, kept as two
     distinct schemas, not one shape with nullable fields)
   - The uniform error contract from §19 with its error codes
2. contracts/contracts.ts — same shapes, TypeScript interfaces.
3. The frozen document type enum (§18, verbatim, 9 values) — put it in both
   files.
4. SQLModel table stubs for the full data model in §18 (no business logic yet)
   in app/models/.
5. FastAPI router stubs (paths only, from §19, returning 501) in app/api/.
6. Repo skeleton per §17's module layout:
   app/{api,models,schemas,services,agents,mock_payer,seed,storage}/
   frontend/  contracts/  .env.example  README.md

EXIT CRITERION: contracts.py, contracts.ts, the enum, and the empty router
file all exist, are internally consistent with each other, and match §14/§18/
§19 exactly with no invented fields.

Commit this with message "contract freeze" and STOP. Report back a summary:
what you froze, and any place where you had to make a judgment call because
the PRD was ambiguous (there should be very few — most of §14/§18/§19 is
exact).

Wait for my explicit approval before continuing to Part 2. Do not spawn any
subagent until I approve.

═══════════════════════════════════════════════════════════════
PART 2 — SPAWN AND COORDINATE 5 PARALLEL SUBAGENTS
═══════════════════════════════════════════════════════════════

(Only after I approve Part 1.)

Spawn 5 subagents, each scoped to its own directories so they can never edit
the same file (this is your main defense against merge conflicts — enforce
it):

- Subagent BE  → owns app/api/, app/models/, app/services/, app/storage/,
  app/seed/ (reference data + seed.py; NOT app/seed/policies/), app/mock_payer/
- Subagent AI-1 → owns app/agents/coverage/, app/agents/rag/,
  app/seed/policies/
- Subagent AI-2 → owns app/agents/documentation/
- Subagent AI-3 → owns app/agents/communication/, app/agents/orchestrator.py,
  app/agents/json_repair.py (shared utility, used by all three agents' retry
  path)
- Subagent FE  → owns frontend/

Give every subagent this shared preamble, verbatim:
"The frozen contracts in /contracts/contracts.py and /contracts/contracts.ts
are the law — do not modify them; flag instead if you think they need to
change. The document type enum is frozen — do not add, remove, or rename
values. Stay inside your owned directories only. temperature=0.2 for any LLM
call you write. No agent calls another agent directly — all agent-to-agent
flow goes through the orchestrator, owned by AI-3, which you are not building
unless you ARE AI-3. There is no deadline — build it correctly and completely
against your brief rather than quickly. Produce a short plan artifact first;
proceed unless something in your brief is genuinely ambiguous, in which case
flag it to the Lead Agent rather than guessing."

Then give each subagent its role brief, drawn directly from PRD §11 (Detailed
Feature Requirements), §12 (AI Agent Architecture), §13 (RAG Architecture), §16
(Frontend Requirements), §17 (Backend Requirements), §20 (Mock Insurance
System), §21 (UX Requirements), §25 (Security), §33 (Demo Scenario, for exact
seed data):

--- BE brief ---
Deliverable 1 FIRST: a mock API server serving every §19 endpoint with
contract-shaped fixture JSON, before any real DB logic — this unblocks FE
immediately. Then: real SQLModel data layer; seed data (2 payers, 3 plans, 4
services, 3 patients, 1 coverage_rules table per §18's shape, mock payer script
table per §20's exact table — MRI Brain/1 rejected/insufficient_clinical_
documentation, MRI Brain/2 approved/ABC-AUTH-88214, CT Abdomen/1 more_info_
required/missing_document, CT Abdomen/2 approved, Specialist Consult/1
approved, Knee Arthroscopy/1 rejected/service_not_covered, 2s response delay).
State machine per §15's exact transition table, enforced ONLY in
app/services/request_service.py, never in the router, never trusted from the
frontend. current_input_hash = SHA256(clinical_context, service_id, plan_id,
sorted document doc_types+ids); server refuses SUBMIT on hash mismatch (409
ANALYSIS_STALE). Event emission on every state change per §18's request_events
table. Security minimum bar per §25 SEC-1 through SEC-7 (file type/size
limits, UUID storage names, parameterised queries, CORS, secrets in .env
only). EXIT CRITERION: every §19 endpoint is real (not fixture), state machine
transitions all enforced with guards, /admin/reset works. You block FE and
AI-3. You are blocked by nothing after contract freeze.

--- AI-1 brief ---
Deliverable 1 FIRST: author 5 policy markdown files in app/seed/policies/ per
§13's exact filenames and content requirements (## §N.N headings, 400-900
words each, sound like real policy documents, each stating in-content it is
sample/illustrative text). MRI Brain under ABC Gold PPO must require prior
authorization with required docs insurance_card, physician_order, clinical_
notes, prior_imaging_report — keep this in lockstep with BE's coverage_rules
seed; coordinate with BE (via the Lead Agent) if they diverge. Then: chunker
(by heading, max 500 tokens, 50-token overlap, retain policy_document_id/
title/section_ref/text) + embedder (embed once at startup, persist as BLOB) +
in-memory NumPy cosine retriever (k=4, similarity floor 0.25, BM25 fallback if
embedding API unreachable) per §13's pipeline. Then Coverage Agent per §14.1's
exact schema. Hard constraints from §12/§23/§26: cannot output a status
contradicting the coverage_rules row (post-validation, rule wins on conflict,
log a warning); evidence_strength is derived, never raw confidence; every
evidence snippet must exist verbatim as a substring of its source chunk
(validate before persistence, drop+retry on failure — this is EX-2, the
actual anti-hallucination control); does not decide required documents or
judge clinical appropriateness, declines direct clinical questions. EXIT
CRITERION: coverage_agent.analyze(input) -> CoverageResult works
independently, testable without the rest of the system, returns correct
verbatim-validated citations for at least the MRI Brain/ABC Gold PPO pair.

--- AI-2 brief ---
Deliverable 1 FIRST, no LLM: pure-Python required-vs-present reconciliation
per §11 F3 — read required_document_types from coverage_rules (injected,
never invented), set-difference against attached declared types, flag
unmatched attachments as unrecognized (informational), ready_for_submission =
(mandatory missing count == 0). Then LLM layer for why_required/how_to_obtain/
blocking_summary per §14.2's exact schema, grounded in the retrieved policy
chunk. Hard constraints: required list must be byte-identical to
coverage_rules (assert set equality post-generation, LLM cannot add/remove
entries); does not open/read/parse file contents — declared type is trusted;
does not diagnose or judge coverage. EXIT CRITERION:
documentation_agent.analyze(input) -> DocumentationResult works
independently, correctly flags the missing prior_imaging_report for the demo
scenario. Coordinate with BE (via Lead Agent) on coverage_rules shape.

--- AI-3 brief ---
Start immediately against stub coverage_agent/documentation_agent functions
that return contract-shaped fixtures — do not wait for AI-1/AI-2's real
agents, swap real imports in later. Build the orchestrator (pure Python, no
LLM) per §12: asyncio.gather fan-out to both agents in parallel, join, apply
the exact combined rule (ready_for_submission = coverage.status in
("covered", "prior_authorization_required") and coverage.status != "unknown"
and documentation.ready_for_submission), persist analyses, emit events.
Failure handling per §22: retry once with repair instruction on malformed
JSON, on second failure mark that agent status:"error" and force
ready_for_submission=false — a failed agent never yields an optimistic
result. Then Communication Agent, two operations per §14.3's exact schemas:
generate_packet (submission_number format PA-{YYYYMMDD}-{seq}) and
analyze_response (payer_reason_verbatim carried through unmodified, separate
from the paraphrased explanation; reason_classification from the fixed
7-value enum; recommended_actions typed with kind+doc_type so the UI can
deep-link uploads; resubmission_checklist ordered, <=5 items). Build the
shared json_repair.py utility used by all three agents' retry path. EXIT
CRITERION: orchestrator.run() produces a correctly-joined combined assessment
from two real (not stub) agent calls once AI-1/AI-2 are ready; both
Communication Agent operations return schema-valid output. You block BE's
integration. You are blocked by nothing — build against stubs now.

--- FE brief ---
Stack: Next.js 15 App Router + TypeScript + Tailwind + shadcn/ui, server
components for reads, client components for forms/polling, no state library.
Start against BE's mock server fixtures the moment they exist, work entirely
against fixtures until told the real backend is wired — do not wait for real
endpoints, and flag to the Lead Agent if BE's mock server isn't up yet when
you're ready to start. Build exactly 4 routes per §16: / (dashboard, 6 status
counters, requests table, no filter/sort/search); /requests/new (single-
column form, mandatory doc-type select per uploaded file); /requests/[id]
(the core screen — Coverage card with collapsible Policy Evidence and a
derived evidence_strength badge with tooltip, never call it confidence;
Documentation card as a ✅/❌ checklist with inline per-row upload controls;
Resolution panel rendered ONLY in ACTION_REQUIRED; reverse-chronological
Timeline); /payer (visually distinct mock insurer console, Scripted/Manual
toggle). Loading behaviour is required, not optional: two INDEPENDENT
skeleton cards during ANALYZING, each resolving the moment its own result
lands, polling GET /requests/{id} every 1500ms — a single full-screen spinner
is a rejected design. UX rules from §21: one primary action per state;
disabled buttons always show a tooltip naming the blocker; AI coverage output
framed as "Based on [plan] policy §X" never "CareAuth AI has determined"; any
post-analysis field/document change shows an amber stale-analysis banner and
disables Submit. Persistent footer disclaimer per §16's exact wording. EXIT
CRITERION: all 4 routes work correctly against the real backend, skeleton
states and stale-analysis banner both verified working. You block nothing.
You are blocked by BE's mock server only, at the start.

Monitor all 5 subagents until every one of them reports its EXIT CRITERION
met. When all five report done, pull each subagent's final artifact and
verify independently: is it actually demonstrable (a real curl-able
endpoint, a real analyze() call returning a valid result, all 4 routes
rendering correctly)? If any subagent's result doesn't actually meet its
exit criterion despite reporting done, send it back with specific feedback
rather than accepting the report at face value. If a subagent has clearly
drifted from its brief partway through, stop it and restart it narrowly with
a corrected brief rather than letting the session argue itself back on track
in a context-heavy state. Report this verification result to me in one short
summary; you do not need my approval to proceed past it, only to flag if
something had to be cut from scope entirely (as opposed to just taking
longer).

═══════════════════════════════════════════════════════════════
PART 3 — INTEGRATION, HARDENING, POLISH
═══════════════════════════════════════════════════════════════

Once all 5 subagents' deliverables are verified complete:

1. Integration: wire real AI-1/AI-2/AI-3 agents into BE's /analyze endpoint in
   place of AI-3's stubs; point FE at the real backend instead of fixtures;
   run the full path by hand (create → analyze → blocked → upload →
   re-analyze → ready → submit → reject → resolve → resubmit → approve) and
   fix whatever breaks. This is the one part of the build where five
   independently-correct pieces either compose or don't — take it carefully,
   iterating until it's actually right, rather than treating it as a fast
   pass.

   EXIT CRITERION: the full happy path runs end to end at least once,
   correctly, not roughly.

   STOP HERE and report to me once that's true. Wait for my approval before
   moving to hardening — this is the second and last checkpoint.

2. Demo hardening (only after my approval): run the exact demo scenario from
   PRD §33 (patient Ahmed Ali, ABC Gold PPO, MRI Brain, scripted payer mode)
   repeatedly, fixing every break, until it completes five consecutive times
   without error — do not stop at fewer than five clean runs even if it takes
   many attempts. Pre-seed the demo request in DRAFT with 3 documents
   attached so the demo never opens on an empty form. Verify
   POST /admin/reset restores clean state in <2s. Build response caching to
   disk for every demo-scenario agent response, with a DEMO_CACHE=1 env flag
   to replay cached responses instead of calling the LLM — treat this as
   effectively mandatory insurance, not optional, even though PRD §30 lists
   it as nice-to-have #1. Produce one screen recording of a full successful
   run as a fallback.

   EXIT CRITERION: 5/5 consecutive clean runs of the demo scenario, caching
   in place, screen recording produced.

3. Polish, strictly in PRD §30's priority order, working down the list until
   either the list is exhausted or an item genuinely doesn't improve the demo
   enough to justify touching working code: toast notifications on state
   transitions; packet export as a downloadable file; a third payer with a
   differing rule set; similarity score badges on evidence items;
   email-preview rendering of the packet; document content preview; dashboard
   charts; search/filtering. Do NOT build a free-text AI chat interface under
   any circumstance — it directly contradicts the product's stated non-goals
   in PRD §7.

   Before touching a Must-Have file for a polish item, re-verify the 5/5
   clean-run result from step 2 still holds afterward — a polish change that
   breaks the demo is worse than not making it. If a change regresses the
   demo, revert it rather than debugging under pressure.

Report back to me with: what's built, what got cut and why, and a final
checklist against PRD §35's definition of done (the demo scenario runs 5/5
times cleanly, and every AI statement on screen traces to either a policy
citation or the payer's own verbatim words).
```

---

## 3. What you'll actually be asked to do, end to end

1. Paste the Master Prompt. Wait.
2. **Checkpoint 1:** review the frozen `contracts.py`/`contracts.ts` the Lead
   Agent produces. Check the document type enum, the three agent output
   schemas, and the state machine against PRD §14/§15/§18 (or just skim the
   Lead Agent's own summary of judgment calls it made). Approve, or correct
   and re-approve.
3. Wait while the Lead Agent spawns and runs the 5 subagents, verifies each
   one's completion, and reports back — this may take a while; let it run.
4. **Checkpoint 2:** review that the happy-path demo actually runs once, end
   to end, correctly. Approve, or send it back with what's broken.
5. Wait while it hardens the demo to 5/5 clean runs and works the polish
   list until it's exhausted.
6. You rehearse presenting it, whenever it's ready — that part's still
   yours.

---

## 4. Notes on why this still has two checkpoints, not zero

Removing all human review is possible in Antigravity, but the two kept here
aren't busywork:

- **Skipping checkpoint 1** risks all five subagents building for a long time
  against a contract that's subtly wrong — the exact failure mode contract-
  freeze exists to prevent, just moved one level up (a bad agent-written
  contract instead of a bad set of five independent agent guesses).
- **Skipping checkpoint 2** risks the polish phase running for a long time on
  top of an integration that doesn't actually work end to end, discovered
  only at the very end with everything else already built on top of it.

Both are a few minutes of your time against a large amount of agent work
riding on them being right — that's the trade this plan is making, not a
reason to be hands-on with the code. Removing the clock (per your request)
actually makes these two gates matter *more*, not less: with no deadline
forcing a stop-and-assess moment, these two approvals are now the only
points where anyone checks the work before more gets built on top of it.
