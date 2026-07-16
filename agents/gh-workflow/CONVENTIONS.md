# GH Workflow Conventions

**THE single source** for the dev-workflow taxonomy: title tags, kind
labels, the board Status model, the state machine, refinement scoring, human gates,
the review gate (§8), and the version-bump / testing-cadence policy. Every `gh-*` skill
(`gh-create-issue`, `gh-refine`, `gh-review`, `gh-fixer`, `gh-validate`, `gh-merge`,
`gh-clean`, `gh-resolve`, `gh-lead`) **references this file instead of restating these
tables** — the CLAUDE.md reuse ethos (one canonical home; change it here, reuse it
everywhere) applied to process docs. Re-inlining any table below into a skill is the
duplication debt this file exists to prevent.

- **Instance data lives in [PROFILE.md](PROFILE.md), not here.** This document and
  the `gh-*` skills are **project-agnostic**: every `<key-name>` placeholder (repo,
  board ids, gates, version source, checkout paths, hot files) resolves to
  `agents/gh-workflow/PROFILE.md` in the repository being operated on. Porting the
  pipeline to another project means writing a new PROFILE.md, never editing this
  doc or a skill. · **Provenance:** FABLE_09 §1–§3 (decisions D1–D10, state
  machine, skill architecture), reconciled with the operator decision record
  (2026-07-03) and the live GitHub admin state executed by gh-lead the same day.
- **Authority note — the D1 VETO:** FABLE_09 D1 proposed status-as-exclusive-labels.
  **VETOED by the operator 2026-07-03.** Statuses live **only** on the project's
  GitHub Projects v2 board Status field (`<board-name>`, PROFILE.md — §3). Everywhere the FABLE_09 §2 source text
  says "status label", this doc means the **board Status field** — same 9 states, same
  owners, different storage. **No status labels are ever created.**
- **Read scope:** every `gh-*` skill declares a **Conventions scope** line naming the
  §§ it needs. An agent executing a skill loads **only** its declared sections
  (`grep -n "^## " agents/gh-workflow/CONVENTIONS.md` gives the section offsets; read
  just those line ranges), opening any other section only at the moment a step cites
  it — the §3 board-economy resolve-once pattern applied to this file itself. Only
  `gh-lead` reads the whole document.

---

## 1. Title tags (D3)

Every newly authored issue title follows one format:

```
[TAG] AREA - Concise action-oriented description
```

- `[TAG]` is one value from the **closed set** below — do not invent new tags.
- `AREA` is a short, consistent component/scope tag in caps (e.g. `WEB UI`, `BACKTEST`,
  `CONFIG`, `MCP`, `GH WORKFLOW`). Reuse an existing area rather than coining a
  near-duplicate. **Children reuse their parent epic's `AREA`** so an epic and its
  children scan as one group.
- The description says what changes and where (action-oriented).

### Closed title-tag set

| `[TAG]` | Meaning |
|---|---|
| `[EPIC]` | Parent ticket decomposed into children; its PR merges to `main`. |
| `[CHILD]` | A child of an epic; lands on the epic/parent branch, **not** `main`. |
| `[TASK]` | Standalone unit of work targeting `main`. |
| `[BUG]` | Defect fix. |
| `[CHORE]` | Routine maintenance / migration / bookkeeping with no feature payload. |
| `[SPIKE]` | Time-boxed research / investigation (no PR pipeline — see §4 short-circuit). |
| `[IDEA]` | Early, unrefined concept captured for later refinement (no PR pipeline). |

**Retired as title tags:** `[REFACTOR]` and `[DOCS]`. They remain **kind labels**
(`Refactor` and `documentation` respectively — see §2); they are no longer title tags.
Changes vs the historical gh-create-issue set: **added** `[CHORE]` and `[IDEA]`; **kept**
`[CHILD]` (the epic-branch flow depends on distinguishing children); **retired**
`[REFACTOR]`/`[DOCS]` as tags.

### Title → tag examples

- `[EPIC] WEB UI - Build a new dashboard website` → children `[CHILD] WEB UI - …`
- `[TASK] CONFIG - Add a volatility entry gate setting`
- `[BUG] ORDERS - Fix reconciliation when partial fills arrive out of order`
- `[CHORE] GH WORKFLOW - Backfill statuses on the open backlog`
- `[SPIKE] GH WORKFLOW - Sweeper routine design`

Avoid vague titles that skip the convention: `Improve code`, `Fix bug`, `Add a button`.

---

## 2. Kind / category labels

Kind labels describe **what the ticket is** and **stay on the issue** for its whole life.
They are orthogonal to status (status is board-owned — §3). Apply one (or more) kind
label at creation matching the work. The D9 dedupe (§10) applies to kind labels only.

**Current set — 14 labels** (reconciles gh-create-issue's and gh-lead's historical
tables into one authority):

| Label | Meaning | Lead action |
|---|---|---|
| `App Error` | Bug / error report surfaced from the running application's error logs. | Workable; triage root cause vs expected/recoverable before allocating. |
| `New Feature` | New feature or capability request. | Informational kind; workable when refined. |
| `Refactor` | Senior-Architect refactor, hardening, or cleanup work (see `CLAUDE.md`). | Informational kind; workable when refined. Kind label for retired `[REFACTOR]` tag. |
| `documentation` | Primarily docs — README, CLI help, skill files, CONTRIBUTING. | Workable, scoped strictly to docs — no behavioral code. Kind label for retired `[DOCS]` tag. |
| `Spike` | Time-boxed research to answer questions or explore a solution. | Workable as research; findings land as a **comment** + follow-up tickets, not a code PR (unless the spike says otherwise). |
| `architecture` | Architecture / boundary design work; usually an epic marker (**parents only**). | Workable as parent/epic: decompose into children, sequence by risk, children land on the epic branch. Never apply to a child. |
| `Concept Idea` | Early-stage idea not yet refined into an actionable ticket. | Do not dispatch a worker; needs refinement first. Kind label counterpart of the `[IDEA]` tag. |
| `Strategy` | New strategy creation or refinement request. | Point the worker at `strategy-iteration-loops` (the canonical strategy workflow); keep target-market-set + backtest-evidence scope in the ticket. |
| `duplicate` | Overlaps another issue/PR. | Do not implement as-is; reconcile against the canonical ticket. |
| `codex` | Tooling marker. | Ignore for planning/prioritization. |
| `Open` | **DEPRECATED status-like label** (see note). | Do not treat as a kind. Vestigial under the board model. |
| `Needs Refinement` | **DEPRECATED status-like label** (see note). | Do not treat as a kind. Vestigial under the board model. |
| `Ignore!` | Will not be worked on. | **Do not work.** Skip entirely. |
| `Unsafe!` | Breaking/unsafe change; human audit required. | **Do not work** without the human gate (§7). If it also carries a workable status, stop and surface; propagate `Unsafe!` to parent epics. |

### `Open` / `Needs Refinement` are DEPRECATED status-like labels

Under the D1 veto, status is owned by the board Status field (§3), so the `Open` and
`Needs Refinement` **labels** are now **fully vestigial.** Their retirement was coupled to
**DW-9 (#678)** and **DW-11 (#680)**: `gh-create-issue` sets the initial board Status
(not these labels) at creation, and the refactored `gh-lead` reads and writes status on
the board (not via these two labels). **Both have landed** — so nothing in the pipeline
sets or reads these labels anymore, and they are being **retired (deleted)**, dropping the
steady-state to **12 kind/marker labels**. (The actual `gh label delete` + redeploy is a
follow-up step performed by the lead after this doc change merges — this file only
records that the labels are vestigial and slated for removal.) **No _new_ status labels
were created**: the 9 pipeline states (`Needs Refinement`, `Backlog`, `Open`, `In
Progress`, `Awaiting Review`, `Reviewed`, `Awaiting Validation`, `In Validation`,
`Validated`) exist **only** as board Status options (§3) — that satisfies #670's "no
status-like labels" clause. Kind labels stay on issues; statuses live on the board.

---

## 3. Status model — the project's Projects v2 board

**Status lives only on the board.** (D1 VETO — see the authority note at the top.) The
board's single-select Status field gives exactly-one-status-per-issue for free (stronger
than the vetoed label invariant). Skills **set** status with `gh project item-edit`;
pollers/sweepers **read** status with `gh project item-list --limit 300 --format json`
(`item-list` defaults to a **30-row page and does not auto-paginate** — always pass
`--limit`, kept above the board's current item count as it grows).

### Board identity (canonical IDs — resolve from the profile; do not re-derive)

The board's name, owner, project number, URL, project node ID
(`<project-node-id>`), Status field node ID (`<status-field-id>`), and the
per-status option IDs (`<option-id:…>`) are **instance values** — they live in
[PROFILE.md](PROFILE.md) and only there. Reference them by placeholder;
re-deriving them via ad-hoc GraphQL is both a budget cost and a drift risk.

When bootstrapping a new project's board, replace the default Status field's
options **in place** (via `updateProjectV2Field`) so the built-in workflows keep
referencing the same field ID, then record the new IDs in that project's
PROFILE.md.

### Status options (pipeline order)

`Needs Refinement → Backlog → Open → In Progress → Awaiting Review → Reviewed →
Awaiting Validation → In Validation → Validated` — exactly these nine, as
single-select options on the board Status field. Their `<option-id:…>` values
are in [PROFILE.md](PROFILE.md).

### Status mechanics (proven; use verbatim)

```sh
# READ — list all board items with their status (poller/sweeper path):
gh project item-list <board-number> --owner <board-owner> --limit 300 --format json
#   -> items[].id            the board item id (PVTI_...)
#      items[].content.number  the issue number
#      items[].status          the current Status option name
#   Resolve an issue's board item id by matching items[].content.number == <issue#>.
#   NOTE: item-list defaults to a 30-row page and does NOT auto-paginate — ALWAYS pass
#   --limit above the board's current item count (raise it as the board grows) or a
#   poller silently misses most rows.

# ADD — put an issue on the board. Pass --format json so the new item id is capturable:
gh project item-add <board-number> --owner <board-owner> --url <issue-url> --format json   # -> .id = PVTI_... item id
#   WITHOUT --format json, non-TTY stdout is empty (TTY prints only "Added item"), so the
#   id is lost — either capture it here, or re-resolve it via item-list (match content.number).

# SET — change an issue's Status (item id from item-add or item-list):
gh project item-edit --id <PVTI_item-id> \
  --project-id <project-node-id> \
  --field-id <status-field-id> \
  --single-select-option-id <option-id:target-status>
```

`<board-number>`, `<board-owner>`, `<project-node-id>`, `<status-field-id>`, and
each `<option-id:…>` resolve from [PROFILE.md](PROFILE.md).

Round-trip proven this session on throwaway issues (`item-add` → `item-edit` to
Needs Refinement → Open, then removed + closed not-planned).

### Getting issues onto the board

- **Required contract (from DW-9, #678): at creation, gh-create-issue must (1) run
  `gh project item-add` to put the issue on the board, AND (2) run `gh project item-edit`
  to set its initial Status to `Needs Refinement`** — so no issue ever lands on the board
  with an unset Status (consistent with the §4 state machine and the §5 ownership table,
  where `Needs Refinement` is set by gh-create-issue at creation). **This landed in DW-9
  (#678):** `gh-create-issue` now runs `item-add` followed by `item-edit` to `Needs
  Refinement` (or the `Backlog` override below) as part of issue creation — this is the
  reliable, script-driven path every skill depends on. DW-2 (#671) has already backfilled
  the existing open backlog onto the board.
- **`Backlog` is a valid initial Status (the override to the `Needs Refinement`
  default).** The default above is not absolute: a bulk/roadmap-generation sweep or the
  operator may seed a **deliberately-iced or far-future** ticket directly as `Backlog`
  (which the sweeper never dispatches — §4) instead of `Needs Refinement`. The roadmap
  generation protocol uses exactly this exception — later-sprint (**Sprint 4+**) tickets
  are seeded `Backlog`, not `Needs Refinement` — and DW-2 (#671) backfilled the
  far-future backlog (Sprints 4–11 and their parallel waves) as `Backlog` accordingly.
- The built-in **"Auto-add to project"** workflow is a **UI-only backstop** (GitHub
  exposes only `deleteProjectV2Workflow` via API/CLI; the auto-add toggle is not
  scriptable). It is tracked as **#785** (a ~1-minute operator UI toggle) and is **not a
  blocker** — auto-add only matters for issues created outside the pipeline. ("Auto-add
  sub-issues to project" is separately already enabled.)

### Board-economy contract (dispatcher resolves the board item map once)

Reading the full board map is a Projects v2 **GraphQL** query (`gh project item-list`
returns every item with its content — hundreds of rows), and the GraphQL primary budget
is only **~5000 points/hour**. During the Sprint-3 pilot, fanning one stage out
**~28-way** with every worker independently running its own `item-list` (300 items ×
full content) drained that budget to zero mid-sprint (`resources.graphql.remaining: 0`),
blocking board writes while REST stayed healthy. This contract removes the redundant
per-worker full-board read: **the dispatcher resolves the map once and injects the id;
the child reuses it.**

- **A dispatcher resolves the board item map ONCE per run and passes ids down.** A
  session that dispatches single-ticket child skills (the lead in Phase 1, or a future
  dispatching sweeper) reads the board **once**, holds the resolved
  `issue# → PVTI item-id` map from that read, and **passes the relevant item-id into
  each child skill's prompt/context** when it dispatches that child.
- **A child skill accepts the injected item-id and MUST NOT re-fetch the full board
  map.** The five single-ticket worker skills — `gh-refine`, `gh-resolve`, `gh-review`,
  `gh-fixer`, `gh-validate` — each use the dispatcher-injected board item-id **directly**
  for their single `gh project item-edit` Status write. A child falls back to resolving
  its own id via `gh project item-list` **only when no id was injected** (a
  standalone/human invocation against one issue number); it **never** re-runs `item-list`
  for a ticket whose id it was already given.
- **Excluded — deliberate full-board scans, not this contract's target.** `gh-merge`
  enumerates *every currently-`Validated` item* for merge-order planning: a
  freshness-sensitive full-board scan it must re-run once per merge pass (reusing a stale
  snapshot there is a correctness risk, not an efficiency win), and it runs once per merge
  event, never fanned out N-way. The **lead's own Phase-1 board read** is itself the
  single per-session resolve-once read this contract is built on, and the report-only
  sweeper already reads the board once per pass (`board_client.read_board_snapshot`, gated
  by a rate-limit self-check). These are the resolve-once side of the contract — they do
  **not** take an injected id and are not swept here.

---

## 4. State machine

Storage is the board Status field (§3) throughout — the diagram below is the FABLE_09 §2
machine with "status label" read as "board Status".

```
[created] --gh-create-issue--> (Needs Refinement)
(Needs Refinement) --gh-refine--> (Open) | (Backlog) | [EPIC]+children | Unsafe! [STOP: human]
(Open) --dispatch (lead or sweeper; claim)--> (In Progress)
(In Progress) --gh-resolve: worktree, implement, PR--> (Awaiting Review)
(Awaiting Review) --gh-review: adversarial passes + reuse-review (Codex addressed if present)-->
      findings --> (Reviewed)      review-stage findings clean/addressed --> (Awaiting Validation)
(Reviewed) --gh-fixer: address every unresolved thread, reply in-thread--> (Awaiting Review)
(Awaiting Validation) --CI green--> --gh-validate: PR branch in isolated worktree,
      behavioral test (UI via preview tools when relevant)--> (In Validation) -->
      pass --> (Validated)               fail --> (Reviewed) + PR comments
(Validated) --gh-merge: merge-order plan, squash, version bump, epic reconcile,
      close ticket, gh-clean--> [closed]
```

### Short-circuit paths

- **`[SPIKE]` / `[IDEA]`:** `(Needs Refinement)` → `(Open)` → research agent → findings as
  issue comments + follow-up tickets via gh-create-issue → close. **No PR pipeline.**
- **`Backlog`:** deliberately iced — either refined-and-ready-but-held, or seeded
  far-future/unrefined at creation (the §3 override). The sweeper never dispatches it;
  it is promoted to `Needs Refinement`/`Open` when its sprint arrives.
- **Kick-backs:** a gh-validate failure returns to `(Reviewed)` (the fixer loop), never
  silently to `(Open)` — the PR and its history stay attached.

---

## 5. Status-ownership table

Same states and owners as FABLE_09 §2; only the storage (board Status field) changed.
"Set by" and "Removed by" name the skill/actor authorized to transition **into** and
**out of** each status.

| Status | Set by | Removed by |
|---|---|---|
| Needs Refinement | gh-create-issue (at creation) or any skill kicking a stale ticket back | gh-refine |
| Backlog / Open | gh-refine, the operator, or a bulk-roadmap-generation seed (§3 — `Backlog` only, for deliberately-iced/far-future tickets) | dispatcher (lead/sweeper) |
| In Progress | dispatcher, with assignee claim | gh-resolve (on PR open) |
| Awaiting Review | gh-resolve, gh-fixer | gh-review |
| Reviewed | gh-review, gh-validate (kick-back) | gh-fixer |
| Awaiting Validation | gh-review | gh-validate |
| In Validation | gh-validate (start) | gh-validate (verdict) |
| Validated | gh-validate | gh-merge (close) |

---

## 6. Refinement block (D4)

Complexity and Blast Radius are **structured body fields** in a `## Refinement` block of
the issue body — **not labels** (avoids a label explosion; keeps the score next to the
evidence that justified it; body blocks stay greppable). gh-refine writes this block.

```markdown
## Refinement

- **Complexity:** <Very Easy | Easy | Medium | Hard | Very Hard>
- **Blast Radius:** <Small | Medium | Large | Huge>
- **Blast-radius file list:** <every file/module the change touches>
- **Rationale:** <the evidence from current code that justifies the two scores>
```

**Epic-conversion trigger:** gh-refine converts a ticket to `[EPIC]` + children when
**Complexity is Hard or Very Hard** **OR** **Blast Radius is Large or Huge**. Children are
authored via gh-create-issue with `[CHILD]` titles reusing the parent's `AREA`.

---

## 7. Human gates (D7) + runaway guards

The pipeline runs unattended end-to-end **only** for tickets that are ≤ Medium complexity
**AND** ≤ Medium blast radius. Human sign-off (an operator comment or the operator moving
the board Status) is **required** at these named gates. FABLE_06's core finding —
*an agent-settable boolean is not a gate* — is why these are human-owned.

| # | Gate | Requirement |
|---|---|---|
| (a) | **Epic-conversion finalization** | Before an epic conversion is finalized (parent + children created), the operator signs off. |
| (b) | **Before `In Progress` for Large/Huge blast** | A ticket scored Large or Huge blast radius may not move to `In Progress` without operator sign-off. |
| (c) | **Always for `Unsafe!`** | Any ticket carrying `Unsafe!` stops for the human, always — no autonomous progression. |
| (d) | **Before merge for high-risk surfaces** | Before merging anything touching **live-order paths**, **`.env` gates**, or the **FABLE_08 track-5 (live-risk) surface**, the operator signs off. |

### Runaway guards (so "auto develop" cannot become agent self-promotion)

- **Sweeper dispatch cap per run** — a hard ceiling on how many tickets one sweeper pass
  may dispatch, so a loop cannot burn the board (or tokens) in one run.
- **Max concurrent workers** — a cap on simultaneously-running worker sessions.
- **Assignee-claim (the cross-dispatch lock)** — the dispatching session sets itself as
  the issue **assignee** at dispatch, and every dispatcher refuses a ticket whose assignee
  list is **non-empty**. This is a repository-wide *claimed vs unclaimed* lock, not a
  session identity: see the hybrid claim protocol below for why a matching login is **not**
  proof of ownership, and why same-login sessions are told apart by the §11 checkpoint's
  active-claim owner session token instead.
- **Sprint-size cap per lead session** — a **soft** default of **~8–10 tickets per lead
  session**, treating session context capacity as a first-class planning constraint and
  counting any ticket flagged likely-multi-cycle (Large blast, `Unsafe!`-adjacent, or
  dual-review-heavy) as **two**. The number is a planning guide tuned from Sprint 3–5
  experience: Sprint 3 session 2 (2026-07-04) landed **15 PRs in one session** and finished
  at the edge of its context window, forcing an unplanned mid-flight handoff — the over-cap
  baseline this bullet exists to avoid. A sprint expected to exceed the cap is **split into
  waves planned as separate sessions at planning time**, with the boundary chosen at a clean
  seam (e.g. after an epic completes, before an integration pass) rather than wherever the
  window happens to die, so each successor session cold-boots from the §11 sprint ledger and
  any handoff is designed, never an emergency. **Operator override:** the operator may direct
  a larger sprint; the extra sessions are still planned up front. The cap **guides, it does
  not block.**

### Hybrid claim protocol (shared-login session ownership)

`gh-lead` and the future sweeper both authenticate as the same GitHub login (the
profile's `<automation-login>`), so the GitHub **assignee** expresses *claimed vs
unclaimed* but cannot identify *which same-account session* holds a claim. The Sprint 12 resolution (#834) is a **hybrid**: the
assignee stays the repository-wide cross-dispatch lock, and the §11 sprint-control
checkpoint's **active-claim owner session token** is the per-session ownership and
concurrency authority. This is the single canonical definition of the protocol — skills
reference it and never restate it. It is fail-closed throughout.

- **Assignee = cross-dispatch lock, never identity.** A **non-empty** assignee list
  refuses every other dispatcher **regardless of login** — a dispatcher must refuse an
  already-assigned issue even when the assignee login equals its own authenticated `gh`
  login. No path treats an `assignee == <automation-login>` match (login equality) as proof
  that the current session owns the issue; ownership is only ever the checkpoint session
  token below.
- **Ownership = the checkpoint's active-claim owner session token.** The §11 in-flight
  entry records, for each claimed issue, the **active-claim owner session token** of the
  session holding it. Two sessions under the one shared `<automation-login>` are distinguished by
  that token, not by login. Only the session whose own token **matches** the recorded
  owner token may advance or release that claim.
- **Per-dispatcher concurrency is token-derived.** A dispatcher computes its own
  active-worker count from the verified checkpoint claims whose owner token equals its
  **own** session token — never from assignee equality, and never from a raw count of all
  assigned in-flight tickets.
- **Inconsistent evidence stops, pending reconciliation.** Missing, duplicate, stale,
  orphaned (an assignee with no checkpoint claim, or a checkpoint claim with no assignee),
  or otherwise contradictory assignee/checkpoint evidence **blocks pending reconciliation**
  (§11) and fails loudly. It is never resolved by login match, by adopting the assignee as
  the owner, or by selecting the most plausible record.
- **Ordered, fail-closed acquisition.** Claim acquisition is a fixed sequence through the
  single §11 checkpoint writer: (1) **cold-boot and reconcile** the checkpoint against
  durable issue/assignee/board evidence; (2) durably **reserve** the active claim in the
  checkpoint under the acquiring session token through the single writer; (3) **verify**
  that reservation by re-reading it; (4) only then add the GitHub assignee and set board
  Status `In Progress`. A partial failure at any step — a failed or concurrent checkpoint
  write, an assignee/checkpoint mismatch, or a reservation that does not read back — leaves
  the claim **blocked until the checkpoint is reconciled**; it is never silently adopted,
  and never retried as a fresh claim over a half-written one.
- **Release/handoff is symmetric.** Only the matching owner token may release a claim,
  clearing the assignee and the checkpoint entry **together** through the single writer.
  A formal session-to-session transfer of an active claim is #869's handoff mechanic and
  is out of scope here (boundary note only).
- **Board-Status transitions are not claim advances (§5 boundary).** "Advance or release
  the claim" above governs the **§11 checkpoint claim record** — the active-claim owner
  entry (reservation and per-session concurrency accounting) — **not** the §5 board-Status
  transitions that `gh-resolve`, `gh-review`, `gh-validate`, and `gh-merge` each perform on
  their own stages (e.g. `gh-resolve` moving `In Progress → Awaiting Review` on PR open):
  those stage transitions are legitimate and need no owner-token match. Until #869's
  session-to-session handoff protocol exists, the claim record is released by the **merge
  owner** (§11's merge-owner session, normally the same accountable owner as the lead):
  `gh-merge` clears the assignee and the checkpoint entry together when it closes the
  ticket.

The report-only sweeper (#760) stays **report-only** under this protocol: it keeps its
existing conservative count of *all* assigned in-flight tickets and performs no claim
writes. Consuming this token-scoped ownership for live sweeper dispatch is a separately
gated follow-up, not enabled here. Ownership-refusal at merge (#868), the handoff-message
schema (#869), and lead-session sizing (#870) reference this protocol but own their own
mechanics — do not implement them here.

---

## 8. Review gate (Claude review stage is the required gate; Codex optional) (D5)

**The required pre-merge review gate is the Claude review stage's own findings** — the
`gh-review` adversarial passes plus `reuse-review` on any `/src` diff. A PR advances
`Awaiting Review → Awaiting Validation` when **that stage's own findings are clean or
fully addressed**, and a merge proceeds from a `Validated` PR — both **independent of
Codex**. A skill references this section; it does not restate it.

> **Codex de-gating (2026-07-15 operator directive — "full Claude").** The dev-workflow
> pipeline is Codex-independent. The `<codex-reviewer>` async automated review
> (`chatgpt-codex-connector[bot]`, PROFILE.md) is **de-gated, not banned**: it is
> addressed **if it posts**, but it is **never required** and **never blocks**. This
> reverses the former hard pre-merge gate (see §10 D5, now marked amended): "a
> still-pending Codex review blocks merge" and "leave at Awaiting Review until Codex
> resolves" are **no longer policy**.

- **The required gate — the Claude review stage's own findings.** `gh-review` runs its
  adversarial passes and `reuse-review`, posts every finding on the PR, and the PR
  advances to `Awaiting Validation` **only** when there are no outstanding
  required-change (`[change-requested]` / BLOCKING) findings — i.e. its own findings are
  clean, or every one has been addressed through the `gh-fixer` loop. This transition
  does **not** wait on Codex in any way.
- **Codex is addressed if present, never required.** If a Codex review **has** posted
  actionable comments (`[change-requested]` or equivalent), treat them like any other
  valid review finding: fix / reply in-thread / resolve them through the normal
  `gh-fixer` loop. But a Codex review that is **pending, absent, or never posted must
  NEVER hold** the `Awaiting Review → Awaiting Validation` transition or the merge — do
  not leave a PR at `Awaiting Review` waiting for Codex to post, and do not block a merge
  on a missing or unresolved Codex review.
- **Recognize Codex so you can address it.** Keep the ability to *recognize* a Codex
  review by its `<codex-reviewer>` author (PROFILE.md) so that, when one is present, its
  actionable comments are picked up and worked. Recognition now serves **addressing**,
  not gating.
- **Deferred finding → tracked follow-up, loudly.** Any review finding — the Claude
  review stage's own, or a Codex comment when one is present — that is deliberately
  deferred rather than fixed becomes a **tracked follow-up issue**, called out loudly (no
  silent scope reduction); never resolve-and-ignore.

### 422 self-review workaround — findings are inline, resolvable threads

The Claude review routine authenticates as the same `<automation-login>` as the PR
author, so only the `APPROVE` / `REQUEST_CHANGES` review **states** are unavailable on
own-account PRs (HTTP **422**). The resolvable-thread mechanism is **not** blocked: post
every finding as an **inline, line-anchored review comment**, which becomes its own
`PullRequestReviewThread` carrying an `isResolved` flag — exactly like the
`<codex-reviewer>` — wrapped in a **COMMENT-event** review (allowed same-account;
verified). Do **not** dump findings into one flat top-level comment body: that leaves no
resolvable thread and defeats the mechanical gate.

- **Each finding = one inline thread, tagged.** Anchor every finding to the exact
  `file:line` and tag it `[change-requested]` (required) or `[minor]` (nit) in the body.
  This is what lets `gh-fixer` reply-and-**resolve** each thread and makes the gate
  mechanically checkable: **the `Awaiting Review → Awaiting Validation` transition and the
  merge require zero unresolved (`isResolved:false`) `[change-requested]` threads authored
  by the review stage (`<automation-login>`).** A top-level review body is only for the
  overall verdict summary, never the sole carrier of a finding. (A `<codex-reviewer>`
  thread is addressed-if-present but never gates — the de-gating above.)
- **Recipe (own-account, verified):** one inline comment via
  `POST /repos/<repo>/pulls/<n>/comments` with `{body, commit_id:<PR head SHA>, path,
  line, side:"RIGHT"}`, or batch them in `POST .../pulls/<n>/reviews` with
  `event:"COMMENT"` and a `comments:[{path, line, body}]` array. Read state back with
  `reviewThreads { nodes { isResolved comments { nodes { author { login } } } } }`.

---

## 9. Version-bump + testing-cadence policy (D6)

Both policies live here and are **referenced, never restated** by the skills.

### Version bump at merge

- The app carries one canonical version — the profile's `<version-file>`, read via
  `<version-read-command>`. It bumps **once per relevant change that merges to `main`**.
- **When:** if the merged PR touched files under the profile's `<bump-paths>`, apply a
  **patch** bump at merge (advance the third semver position, e.g.
  `1.0.29 → 1.0.30`). A minor/major bump is a deliberate, called-out exception. A PR
  touching none of the bump paths (e.g. docs-only) does **not** bump.
- **Who:** **only gh-merge / the lead bumps**, serially at each merge. **Workers never
  touch the version line** (N parallel PRs each bumping would collide on that one line) —
  they note the deferral in the PR.
- **Children are exempt.** Child PRs land on the epic/parent branch, not `main`, so they
  never touch the version. Only the **epic/standalone PR's single merge to `main`** bumps,
  once, for the whole change.

### Testing cadence

This is the **single authoritative** rule for how often tests run; do not restate a
competing cadence elsewhere.

- **During development and review:** run **only the targeted tests** covering the
  files/behavior the change touches — workers iterating, the validator, and the reviewer
  all use targeted runs, never a full-suite re-run per edit or per cycle.
- **Cheap fast gates run freely** — types / file-size / no-artifacts / vulture may run as
  often as useful.
- **One full `pytest -q` per merge-to-`main` boundary,** green before that merge. It does
  **not** run per worker, per review cycle, or per child PR (children land on the epic
  branch on targeted tests only). A standalone PR runs the full suite before its own merge;
  an epic runs it once before its integration merge. In a multi-PR wave of standalones,
  do not rely on a single end-of-wave run — either run the full suite before **each**
  merge-to-`main`, or compose the wave on a shared integration branch and run it once
  before merging that branch to `main`.

---

## 10. Decision record (D1–D10)

The FABLE_09 §1 decisions, with the operator's 2026-07-03 resolutions. **D1 is VETOED**
(superseded by the Projects v2 board); **D5 and D8 are AMENDED** (D5 by the 2026-07-15
Codex de-gating). D2–D4, D6, D7, D9, D10 confirmed.

| # | Decision (as adopted) | Status | Rationale |
|---|---|---|---|
| **D1** | ~~Statuses are exclusive GitHub labels.~~ **Superseded:** statuses live on the "KS Pipeline" Projects v2 board single-select **Status** field (§3) — same 9 states/owners, board storage. **No status labels are ever created.** | **VETOED** | Operator veto 2026-07-03. Single-select gives exactly-one-status for free (stronger than the label invariant); the `project` token scope is granted (`gist, project, read:org, repo, workflow`). Kind labels stay on issues; the D9 dedupe still applies. |
| D2 | **Validation happens BEFORE merge:** `Awaiting Validation` (review clean + CI green) → `In Validation` (validator tests the PR **branch** in an isolated worktree) → `Validated` → merge. | Confirmed | Pre-merge validation keeps `main` clean; post-merge failure would need reverts. Fixes the brainstorm's contradiction. |
| D3 | **One closed title-tag set** `[EPIC] [CHILD] [TASK] [BUG] [CHORE] [SPIKE] [IDEA]`; `[REFACTOR]`/`[DOCS]` retired as tags (remain kind labels). See §1. | Confirmed | Two drifting taxonomies are exactly the duplication debt CLAUDE.md prevents. Reconcile once, here. |
| D4 | **Complexity + Blast Radius are structured `## Refinement` body fields**, not labels; Hard/Very-Hard **or** Large/Huge → `[EPIC]` + children. See §6. | Confirmed | Avoids a label explosion; keeps the score next to its evidence; still greppable. |
| **D5** | ~~Codex hard pre-merge gate survives unchanged.~~ **AMENDED 2026-07-15 (Codex de-gating — "full Claude"):** the required pre-merge gate is the **Claude review stage's own findings** (§8); Codex is **addressed if it posts but never required and never blocks**. The 422 COMMENT-review workaround is retained. See §8. | **AMENDED** | The pipeline went Codex-independent; the former hard Codex gate is no longer required. History kept — the gate existed and was battle-tested before 2026-07-15; it is now de-gated, not deleted. |
| D6 | **gh-merge owns the version bump** at merge-to-`main` (patch when `/src` `/scripts` `/agents` `/tests` touched; children exempt; workers never touch the line). Testing-cadence policy moves here. See §9. | Confirmed | Existing policy, already debugged across sprints (#30/#198). |
| D7 | **Named human gates** (§7) — epic finalization; before `In Progress` for Large/Huge; always `Unsafe!`; before merge for live-order / `.env` / track-5 — plus runaway guards (sweeper dispatch cap, max concurrent workers, assignee-claim). | Confirmed | FABLE_06 §13: an agent-settable boolean is not a gate. Born with the review points the strategy workflow lacked. |
| **D8** | **Automation is phased** (A: manual/lead-dispatched skills → B: one polling sweeper routine, dry-run first → C: optional Actions triggers). **AMENDED:** every follow-up a skill defers — spike findings, validation kick-backs, pilot friction, sweeper phase transitions — becomes **its own ticket**. No untracked TODOs. | **AMENDED** | One poller = one throttle point. The amendment closes the untracked-deferral hole so all deferred effort is a tracked ticket. |
| D9 | **Label cleanup rides DW-1:** `Bug` → `App Error`; `Feature`/`enhancement` → `New Feature`; `priority`/`high-priority`/`new-model` → **deleted** (undescribed, owner-less, only on closed issues). Migrate-then-delete, never delete first. Executed 2026-07-03 — see the migration record below. | Confirmed | The live label list already had undescribed near-duplicates; undescribed labels are what let taxonomy drift start. |
| D10 | **gh-lead survives as the sprint orchestrator** (triage, wave planning, dispatching many tickets), refactored to *delegate* to the new skills. The sweeper is steady-state drip; the lead is for sprints. Both call the same skills; only gh-merge merges. | Confirmed | Preserves the working sprint muscle while removing the monolith's inlined copies of refine/review/merge. |

### D9 migration record (executed 2026-07-03 by gh-lead)

The pre-migration snapshot (full 20-label list + per-label issue numbers) is the rollback
record posted as a comment on **#670** ("D9 label dedupe — pre-migration rollback
record"). Summary of what ran:

- `Bug` → `App Error` (22 issues re-labeled), then `Bug` deleted.
- `Feature` + `enhancement` → `New Feature` (3 issues), then both deleted.
- `priority` / `high-priority` / `new-model` deleted outright — all undescribed,
  owner-less, and present only on closed issues (`#524` merged; the `#553–#562`/`#534`
  closed regime_adaptive family). Prioritization now lives in sprint milestones + the
  board, so deleting them removed no signal from any open issue.
- **Final label set (14):** App Error, Concept Idea, Ignore!, Needs Refinement\*,
  New Feature, Open\*, Refactor, Spike, Strategy, Unsafe!, architecture, codex,
  documentation, duplicate. **No status labels were created.**
- \*`Open` / `Needs Refinement` were the deprecated status-like labels — vestigial at the
  time of this migration (status is board-owned) but **not yet deleted**: at that point
  both were still set/read by the un-refactored `gh-lead`, so their retirement was coupled
  to **DW-9 (#678)** and **DW-11 (#680)**. **Update: both have since landed** (see §2) —
  neither label is set or read anywhere in the pipeline anymore, and they are now being
  retired, dropping the steady-state to **12 labels** (§2). DW-2 (#671) keyed its status
  backfill on **milestone**, not these labels.

**Rollback:** recreate a deleted label (`gh label create <name>`) and re-apply to the
issue numbers listed in the #670 rollback comment (`gh issue edit <#> --add-label <name>`).
`App Error` / `New Feature` were pre-existing and unchanged; only the duplicate source
labels were removed.

---

## 11. Sprint-control ledger contract

Every sprint's GitHub **sprint control issue** is the durable home and identity for the
sprint-wide coordination state that the ticket-local board Status field cannot express.
The issue body references this section. Its comments contain exactly one current
checkpoint, identified by this exact marker on its own line:

```markdown
<!-- ks-sprint-checkpoint:v1 -->
```

That uniquely marked comment is the mutable ledger: edit it in place instead of posting
successor checkpoint comments. GitHub's comment edit history retains history while
readers have one unambiguous current record. Chat, transcripts, pasted handoff prose,
local notes, and agent memory may help locate evidence, but are never ledger authority
and never justify inferring writable state.

### Required compact checkpoint fields

Keep the checkpoint concise, but record all of the following explicitly (use `none`
rather than omitting an empty field):

- sprint identifier and control-issue number;
- monotonically increasing checkpoint revision and UTC update time;
- active lead session identity and merge-owner session identity (normally the same
  single accountable owner, with any deliberate difference stated);
- current canonical app version;
- ordered merge queue, including issue/PR pairs and dependency constraints;
- every in-flight issue, PR, session, and worktree, with its current workflow state,
  and — for each **claimed** issue — the **active-claim owner session token** of the
  session holding it (§7's hybrid-claim ownership authority: the session token, never the
  shared GitHub login, identifies the owner, and per-session concurrency is counted from
  the claims carrying a given token);
- hot-file/collision notes between queued or in-flight changes;
- pending or satisfied §7 (D7) human gates, each with durable sign-off/evidence links;
- deferred follow-up issue numbers (D8 forbids untracked deferred work); and
- one concrete next safe action, including its prerequisites or blocking reason.

### Writer ownership and update cadence

The active lead/merge owner is the **single checkpoint writer**. Workers, reviewers,
validators, and other sessions report durable evidence to that owner; they do not create
or edit competing checkpoint comments. A formal session handoff transfers writer
ownership by one final edit that names the successor and its next safe action; the
successor must cold-boot and reconcile before its first write.

Edit the checkpoint after every state-changing coordination event: dispatch (including
each dispatch wave), PR open, review handoff or return, validation start/verdict, merge,
new block or cleared block, D7 gate request/sign-off, deferred-follow-up creation, and
intentional lead/merge-owner session handoff or end. An event is not durably handed off
until its checkpoint edit is verified.

### Session-to-session handoff message (extends the writer-ownership transfer)

The "one final edit that names the successor" above is not a bare pointer: at a formal
handoff the outgoing writer's final checkpoint edit MUST carry a complete, ungameable
handoff message so the successor can both trust what it inherits and independently
disprove it. This **extends** the required fields above for the handoff moment; it is
**not** a second schema and introduces no competing marker or heading.

- **Successor identity.** Name the incoming writer with the **same session
  identity/token convention** the checkpoint already uses for its *active lead session
  identity and merge-owner session identity* fields — never a second identity scheme, and
  never the shared `<automation-login>` (§7 and §12 identify sessions by that same token).
  The transfer writes the successor's token into the same owner field(s), so a §12
  merge-owner transfer and this writer-ownership transfer name the successor one way.
- **Handoff trigger/reason.** State *why* ownership is moving — e.g. end-of-run PR-only
  session complete, a mid-sprint context-pressure checkpoint (the §7 sprint-size cap), or
  a planned wave boundary — so the reader learns the cause, not merely that a transfer
  happened.
- **Freshly reconciled, not merely present.** Every *Required compact checkpoint field*
  above must be **freshly reconciled against durable evidence as of the handoff edit**,
  not carried forward stale — a handoff is exactly the moment a stale merge-queue, gate,
  version, or in-flight-claim field is most costly. The outgoing writer runs the §11
  reconciliation immediately before writing this final edit.
- **Fail-loud rule for the receiving session — named is necessary, never sufficient.**
  Being named successor authorizes the incoming session to *begin*; it never authorizes a
  first write on trust. Before its first write of any kind (dispatch, merge, gate
  sign-off, or checkpoint edit) the successor MUST independently complete the REST-first
  cold-boot reconciliation below against durable GitHub/Git evidence. **Any mismatch
  between the inherited checkpoint's claims and that independent reconciliation stops the
  successor** — surface it exactly as a stale/inconsistent checkpoint below; it is never
  resolved by trusting the outgoing session's checkpoint content, and never waived because
  this session is the named party.
- **The session-messaging tool is a courtesy nudge, never authority.** When the
  successor's session is addressable via the session-messaging tool, the outgoing session
  may send a low-latency pointer (control-issue number, checkpoint comment URL) so the
  successor starts sooner — but that message is **never** ledger authority: the durable
  checkpoint edit alone is sufficient, and the successor still owes the independent
  reconciliation above regardless of any message it did or did not receive. The checkpoint
  comment already *is* the durable, discoverable handoff record — do not design a second
  one. Broadcasting an ownership change to other concurrent *bystander* sessions (beyond
  the named successor) is out of scope here and tracked separately (#997); those sessions
  learn of the change by re-reading the durable checkpoint on their own next
  reconciliation, not by a push from this edit.

### REST-first discovery, reconciliation, and atomic edits

Routine discovery and writes use GitHub REST issue/comment endpoints first; ledger
access must not add Projects-v2 GraphQL calls. Cold-boot from only the sprint control
issue: read its body and all comments, locate the exact marker, then reconcile the
checkpoint against durable GitHub issue, PR, review, CI, version, board, gate-sign-off,
and worktree evidence before dispatch, merge, or ownership transfer.

- **Missing marker:** stop. Before any parallel dispatch or other sprint mutation, the
  accountable lead may bootstrap one checkpoint only after reconstructing every required
  field from durable evidence; create it once, re-read, and verify uniqueness.
- **Duplicate marker:** stop and surface every conflicting comment URL/id. Never choose
  the newest, highest revision, or most plausible comment automatically; reconcile to one
  current comment explicitly before proceeding.
- **Stale or inconsistent state:** stop and surface the conflicting checkpoint fields and
  durable evidence. Reconcile the whole checkpoint; never patch only the convenient field
  or continue from chat state.

Each edit is a complete atomic checkpoint replacement: read the current comment id,
body, revision, and `updated_at`; build one internally consistent next revision; re-read
immediately before the REST edit and abort if any observed value changed; edit that same
comment; then re-read and verify the marker, revision, required fields, and durable-event
evidence. On any failed write, concurrent change, missing field, duplicate, stale value,
or queue/dependency/owner inconsistency, fail loudly and perform no dispatch, validation
handoff, merge, gate transition, or ownership handoff until reconciled.

This section defines the ledger and its fields only. The #834 claim-identity **mechanics**
live in §7's hybrid claim protocol, which consumes the active-claim owner session token
defined above; the **merge/version-owner** claim, transfer, and release **policy** for the
merge-owner session-identity field lives in §12, enforced once by `gh-merge`'s Step 0. The
#869 handoff-message schema and the #870 sizing policy have both **landed** — #869 as the
handoff-message subsection above, #870 as §7's sprint-size cap — and consume this ledger
with their mechanics owned by those sections, so there is nothing further to implement for
them here. The one genuinely-remaining follow-on is **#997** (broadcasting an ownership
change to bystander sessions beyond the named successor, noted in that subsection above);
it is out of scope here and owns its own mechanics — do not infer or implement #997 here.

---

## 12. Merge/version-owner claim, transfer, and release

Exactly one **merge/version owner** holds the pen to `main` at any time. §11 already
records who that is — the **merge-owner session identity** field in its required
checkpoint fields — so this section adds **no second record and no competing field**
(not a pinned-issue field, not a label, not a new body field): every read and write of
who owns the merge/version line goes through that one §11 checkpoint field, under §11's
marker, its atomic read-reconcile-write discipline, and its REST-first access rules
(reused verbatim, not re-derived). This section defines only the **policy** wrapped
around that field — who may claim it, how it transfers, and when it is released. It is the
acquire/transfer companion to §7's hybrid claim protocol (which owns the per-**ticket**
claim) and to §9 (only the owner bumps the version); `gh-merge` is the single point that
**enforces** it.

- **The value is a session token, not a GitHub login.** Every lead / merge / sweeper
  session authenticates as the one shared `<automation-login>` (§7, #834), so the login
  cannot tell two sessions apart. The merge-owner field therefore names the owning
  **session identity/token**, exactly as §11 frames it — never a `gh` login, which would
  make every same-account session look like the owner.
- **Claiming an unclaimed field.** When the merge-owner field is `none`, it may be claimed
  by **the operator**, or by **a lead at sprint start** (the acquire-side lives in
  `gh-lead`'s cold-boot section). A claim is **one atomic §11 checkpoint edit** that writes
  the acquiring session's token into the merge-owner field — reusing §11's single-writer
  *Writer ownership and update cadence* mechanism, **not** a new transfer mechanism. Only
  one session may hold it; a session that finds the field already held by **another**
  session does not claim it — it goes **PR-only** (opens and hands off PRs, never merges).
- **Transfer is explicit and atomic.** Handing the pen to a successor is the **same
  one-final-edit-names-the-successor** transfer §11 already defines for the checkpoint
  writer, applied to the merge-owner sub-field: the current owner writes the successor's
  session token into the merge-owner field in one atomic checkpoint edit, and the successor
  cold-boots and reconciles (§11) before its first merge. There is no second transfer path.
- **Release is explicit — never inferred.** An owner session that is ending MUST either
  release the field (set it back to `none`) or transfer it (above) in a durable checkpoint
  edit. Ownership is **never** inferred from inactivity, a timeout, silence, or a
  plausible-looking successor: an abandoned, un-released field stays owned by the departed
  token and **blocks** the next merge until the operator reconciles it (§11's
  stop-and-surface discipline). No session self-serves ownership by declaring the previous
  owner gone.
- **`gh-merge` is the sole enforcement point.** The mechanical refusal — that a merge or a
  version bump only proceeds from the recorded owner — lives in **exactly one place**,
  `gh-merge`'s `## Step 0 — Verify merge ownership`, and is deliberately **not** restated
  here (single source of truth, the same rule that keeps §11 the only home of the
  checkpoint-writer transfer). `gh-lead` *references* this policy for the acquire-at-cold-
  boot case and likewise does not restate the enforcement condition.

This section defines the ownership **policy** only. The refusal **condition** that enforces
it lives once in `gh-merge`/SKILL.md (Step 0); the per-ticket claim mechanics live in §7;
the ledger field and its atomic-edit discipline live in §11. The companion follow-ons #869
(handoff-message schema) and #870 (sizing policy) have both **landed** (§11's handoff-message
subsection and §7's sprint-size cap respectively) and reference this policy while owning
their own mechanics there — nothing further to implement for them here.
