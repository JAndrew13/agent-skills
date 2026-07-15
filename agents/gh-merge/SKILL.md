---
name: gh-merge
description: Merge Validated pull requests to main — the pipeline's single, tightly-guarded merger. Plans a collision-aware merge order across all open Validated PRs, re-checks the Codex gate at merge time, runs the full-suite gate per the testing-cadence policy, squash-merges to main, applies the version bump, reconciles the parent epic (and triggers its integration-acceptance pass when the last child lands), closes the ticket, sets the board Status, and invokes gh-clean. Use when a Validated PR is ready to land, or when gh-lead / the sweeper delegates a merge. This is the ONLY role that merges.
---

# GH Merge

**Session shape:** spawned subagent (or the merge-owner lead session), one per merge
pass; works from its own dedicated `gh-merge-<session>` worktree — never the
operator's main worktree.
**Conventions scope:** read only §§3, 5, 7, 8, 9, 11, 12 of
`agents/gh-workflow/CONVENTIONS.md` (`grep -n "^## "` it for section offsets and read
just those ranges); open any other section only at the moment a step cites it.

## Overview

You are the pipeline's **sole merger**. A PR reaches you at board Status **`Validated`**
(review clean, Codex resolved, CI green, behavior verified by gh-validate). Your job is the
`(Validated) → gh-merge → [closed]` transition of the state machine: plan a safe merge
order, re-check the gates *at merge time*, squash to `main`, bump the version, reconcile the
epic, close the ticket, set its board Status, and clean up.

**Only gh-merge ever merges.** gh-lead (post-DW-11) and the polling sweeper both **delegate
here** — so there is exactly one merge policy in the codebase. Do not let any other role
merge; if asked to, hand it to this flow.

**Content source (extraction, not new logic):** this skill extracts gh-lead's
**"Cycle and merge"** section (plus its *Testing-cadence policy* and *Operating principles*)
from `agents/gh-lead/SKILL.md`. DW-11 (#680) deletes that inlined prose from gh-lead in the
same phase so the logic lives here once — net prose shrinks.

**Taxonomy, statuses, gates, and the version/cadence policy are defined once in
`agents/gh-workflow/CONVENTIONS.md` — this skill references those sections and never restates
their tables.** Re-inlining a status/version/cadence/gate table here is the duplication debt
CONVENTIONS.md exists to prevent.

The sprint-control-ledger contract lives only in **CONVENTIONS.md §11**. Read and
reconcile that durable checkpoint before merge work, and verify that it records
the active lead/merge owner for this handoff. Reference §11 rather than
restating its marker, fields, discovery rules, or writer policy here.
- **Repo / board:** the profile's `<repo>` and its Projects v2 board. Status IDs (project
  node, Status field node, and every option id) are in PROFILE.md per CONVENTIONS.md §3 —
  reference them there; do not re-derive.

## Non-negotiables (read first)

- **Merge from a dedicated worktree, never the operator's main worktree.** Create your own
  worktree off the **latest** `origin/main` immediately before you start (see *Prepare*).
  Never `git switch` / edit / `git clean` in the operator's main checkout or any other
  session's worktree — that has corrupted refs and wiped `.env` before.
- **Gate on the real state, at merge time — never a proxy.** Codex threads and CI post
  asynchronously; a status that was green at review time can be stale now. Re-query the live
  PR state right before the merge button.
- **Prefer surfacing a stuck gate to the operator over merging on a proxy.** If Codex never
  posts, a thread can't be resolved, CI is stuck, or a D7 gate is unsigned — **stop and
  surface it to the operator.** Do not merge to keep the pipeline moving. "A Codex review
  exists" is not "Codex resolved"; "CI was green earlier" is not "CI is green now."
- **You are the only version-bumper.** Workers leave the profile's `<version-file>` version
  untouched; you apply the bump serially at each merge (CONVENTIONS.md §9).
- **Single merge/version pen when two sessions run.** If a second gh-lead/merge session is
  active, exactly one holds the merge+version pen; the other is PR-only. Confirm you hold it
  before merging (avoids the `<version-file>` version-line race).
- **Verify — and enforce — the recorded merge owner (Step 0).** Reconcile the §11
  checkpoint's recorded merge-owner session token against the current durable handoff
  evidence **before any other step**. This is no longer advisory: `## Step 0 — Verify merge
  ownership` below is a hard, fail-closed refusal gate — a session that is not the recorded
  owner does not merge or bump the version. The refusal condition itself is stated exactly
  once, in Step 0 (the sole enforcement point named in CONVENTIONS.md §12).

## Step 0 — Verify merge ownership (before anything else)

**This is the first thing you do — before *Prepare*, before any worktree, before any read
of the mergeable set.** The version-bump policy (§9) says only the merge/version owner
bumps, serially; with multiple same-login sessions all *able* to run this skill, that serial
guarantee is real only if a non-owner session **mechanically refuses** to merge. That
refusal is enforced here and **only** here — CONVENTIONS.md §12 names `gh-merge`'s Step 0 as
the sole enforcement point and does not restate the condition, so this is its one home.

1. **Read the recorded owner.** Cold-boot and reconcile the sprint-control checkpoint
   (CONVENTIONS.md §11) and read its **merge-owner session identity** field — the single
   record of who holds the merge/version pen (§12). Ownership is a **session token**, not a
   `gh` login: every session shares the one `<automation-login>` (§7 / #834), so a matching
   assignee login is **never** proof you are the owner.
2. **Compare it to your own session token.**
3. **Refusal condition — stated in this one place.** If the invoking session's own token
   does **not** match the recorded merge-owner session token, **STOP and surface**. The
   refusal is absolute —
   **create no merge worktree, run no gate, invoke no merge, and edit no version line**.
   Hand any `Validated` PRs to the recorded owner's queue and stay PR-only. There is **no**
   self-service override — only the operator, or the current owner via the §12 transfer
   protocol, may change who the owner is; a session may **not** declare itself owner because
   the previous owner looks idle (§12 forbids inferring ownership from inactivity).
4. **Unclaimed field.** If the merge-owner field is `none`, do **not** self-appoint mid-
   merge: surface it so the operator or the sprint lead claims it via the §12 acquire path
   (`gh-lead`'s cold-boot) before any merge proceeds.
5. **Fail loud and specific.** The surfaced message names **who** the recorded owner is and
   **where** the record lives — the §11 checkpoint comment URL and its marker — so the
   operator can act on the mismatch immediately.

Only once your token **is** the recorded merge owner do you proceed to *Prepare*.

## Prepare — a dedicated merge worktree off latest main

```sh
git -C <operator-main-repo> fetch origin
git -C <operator-main-repo> worktree add --detach <merge-worktree> origin/main
cd <merge-worktree> && git checkout -b gh-merge-<session>
```

Operate only inside `<merge-worktree>`. When done, gh-clean removes it (never the operator's
main). Set `PYTHONPATH=<merge-worktree>/src` and copy the gitignored `.env` in before any
run that needs `Settings()` — a fresh worktree resolves imports to main's `src` via the
editable `.pth` and lacks `.env` (shared-venv / missing-`.env` traps).

## Step 1 — Collect the mergeable set (Validated PRs)

Read the board for every issue at Status **`Validated`** and resolve its PR (CONVENTIONS.md
§3 gives the `item-list` read path — always pass `--limit` above the board's item count; it
does not auto-paginate). A PR is a merge *candidate* only if it is `Validated`; anything
earlier in the state machine is not yours to merge.

Split candidates by target branch — this drives whether you touch the version and run the
full suite (CONVENTIONS.md §9):

- **Standalone `[TASK]`/`[BUG]`/`[CHORE]` PRs → `main`.** Each is a `main`-merge boundary.
- **`[CHILD]` PRs → the epic/parent branch (not `main`).** Children land on targeted tests,
  never bump the version, and never trigger a full suite (they don't touch `main`). Only the
  epic's single integration merge to `main` bumps and runs the full suite.

## Step 2 — Merge-order & collision planning (across all open Validated PRs)

Never merge blindly in ready-time order. Plan an order that keeps `main` mergeable and each
PR still valid after the ones before it land.

1. **Build each PR's touched-file set** from the actual diff, not the blast-radius list in the
   ticket:

   ```sh
   gh pr diff <pr> --name-only
   ```

2. **Detect file overlap — pairwise, on the full touched-file sets.** Two Validated PRs that
   touch **any** common file collide; they must be **serialized**, not merged back-to-back
   without a rebase. Disjoint-file PRs may merge in either relative order.

   - **The whole-file-staging hazard (encode this — a file-level check alone misses it):**
     `git add <file>` stages the file's *entire current content*, so if two PRs each edited
     *different regions* of the same file, the second still conflicts (or, worse, silently
     carries the first's hunk if it was built in a shared tree). A "no overlap" verdict from
     comparing *ticket* file lists is not enough — compare the **actual diff file sets**, and
     for any shared file confirm the second PR's diff is still clean after the first lands
     (`git diff --cached <file>` shows exactly the hunks about to commit). This bit #178/#183.
   - **Known repeat-offender hot files** (a shared touch here is a hard serialize signal):
     the profile's `<hot-files>` list, plus its project-specific always-serialize
     `<serialize-rules>` (PROFILE.md — e.g. this project's "at most one ConfigField PR in
     flight" snapshot-regeneration rule).
   - **`<version-file>` is a special case, not a serialize trigger.** *Every* code PR "touches"
     the version line, but the version rule (Step 5) handles that: workers leave the line
     alone and you bump serially, so PRs don't actually collide on it. Ignore `<version-file>`
     when scoring overlap *unless* a PR changed it for a non-version reason (deps, metadata) —
     that is a real overlap.

3. **Choose a defensible order** and write down the rationale:
   - Prerequisites / dependency edges first (a PR whose base or premise depends on another).
   - Among independents, prefer the **smaller-blast / fewer-file** PR first so a later rebase
     is cheaper.
   - Sequence colliding PRs; never interleave two that share a real file.

4. **Rebase & re-verify after each merge that changed a follow-on PR's files.** When a merge
   lands changes to files a later Validated PR also touches, that later PR is now behind:

   ```sh
   git -C <its-worktree> fetch origin
   git -C <its-worktree> rebase origin/main    # or origin/<epic-branch> for a child
   ```

   Resolve conflicts, re-run its **targeted** tests (CONVENTIONS.md §9 — targeted during dev,
   not a full suite per PR), and re-confirm its Codex/CI state (Step 3) before it becomes the
   next merge. If a rebase materially changes the diff, the PR may need to re-enter validation
   (kick back to `Reviewed` per the state machine) rather than merge on stale approval.

## Step 3 — Re-check the Codex gate at merge time (D5)

Apply the **Codex pre-merge gate exactly as defined in CONVENTIONS.md §8** — do not restate
it here. Re-run the check **now**, against the live PR, because Codex reviews and threads post
**asynchronously** and may have appeared or changed since gh-review ran:

- Confirm Codex has **posted** its automated review (a still-pending review blocks merge just
  as an unresolved thread does), and that **zero** Codex review threads remain unresolved
  (query the PR's review threads via `gh` / the GitHub tools).
- If a Codex comment was deferred rather than fixed, confirm a **tracked follow-up issue**
  exists and was called out loudly (no silent scope reduction) — per §8; else stop.
- **Stuck-gate rule:** if Codex never posts, or a thread genuinely cannot be resolved, **do
  not merge** — surface it to the operator. Merging on "a review exists" is the proxy §8
  forbids. (The 422 self-review workaround for own-account PRs is in §8 — COMMENT-type reviews
  tagged `[change-requested]`/`[minor]`.)

## Step 4 — D7 human gate for high-risk surfaces (before merge)

Before merging **anything touching live-order paths, `.env` gates, or the FABLE_08 track-5
(live-risk) surface**, the **operator must have signed off** — gate (d) in CONVENTIONS.md §7.
A human sign-off is an operator comment or the operator moving the board Status; **an
agent-settable boolean is not a gate** (FABLE_06). Inspect the PR's touched files (Step 2) for
those surfaces; if any is present and there is no operator sign-off, **stop and surface** — do
not merge on a proxy. (Also respect the other §7 stops: anything carrying `Unsafe!` never
progresses autonomously; Large/Huge-blast tickets needed sign-off before `In Progress`.)

## Step 5 — Full-suite gate, then squash-merge

Run the gates in order; each `main`-merge boundary gets exactly one full suite.

0. **Gate the PR's ACTUAL to-be-merged code — not clean `main`.** The merge worktree was cut
   from `origin/main` (Prepare) and does **not** yet contain this PR's changes, so running the
   gates as-is would test `main`, letting a PR that only fails **after** it is applied still
   merge. Before the gates, materialize the merged result inside the merge worktree by applying
   the candidate onto the current base:

   ```sh
   git fetch origin
   git checkout -B gh-merge-<session> origin/main   # or origin/<epic-branch> for a child
   gh pr checkout <pr>            # OR: git merge --no-ff origin/<pr-head-branch>
   git rebase origin/main         # if you checked the branch out, land it on the current base
   ```

   Equivalently, run the gates against the **PR head after it has been rebased onto the current
   base** — the point is the tree you test is byte-for-byte what the squash will ship. If the
   rebase/merge conflicts or materially changes the diff, kick the PR back to `Reviewed`
   (Step 2.4) rather than merge on stale approval.
1. **Fast gates** (may run freely — CONVENTIONS.md §9), run **on that merged tree**:
   the profile's `<fast-gates>` commands (PROFILE.md).
2. **Full suite once per `main`-merge boundary, green before the merge — per CONVENTIONS.md
   §9** (referenced, not restated), run **on that same merged tree**: the profile's
   `<full-suite>` command. It runs for
   a **standalone PR before its own merge**, and for an **epic once before its integration
   merge**; it does **not** run per child PR (children land on the epic branch on targeted
   tests). In a multi-PR wave of standalones, run it before **each** merge-to-`main` — do not
   rely on one end-of-wave run — or compose the wave on a shared integration branch and run it
   once before that branch merges to `main`.
3. **Squash-merge to the target branch** once the order (Step 2), Codex (Step 3), D7 (Step 4),
   and the suite **on the merged tree** are all satisfied:

   ```sh
   gh pr merge <pr> --squash --delete-branch
   ```

   Squash is the repo convention. Merge standalones/epics to `main`; merge children to the
   epic branch.

## Step 6 — Version bump at merge (D6)

Apply the **version-bump policy from CONVENTIONS.md §9** — referenced, not restated. In short,
as the owner of the version pen:

- If the merged PR touched files under the profile's **`<bump-paths>`**, apply a
  **patch** bump to the `<version-file>` version as part of the merge (the source
  `<version-read-command>` reads). A PR touching none of those (e.g. docs-only) does not bump.
- **Children are exempt** — they land on the epic branch, never `main`; only the epic's single
  merge to `main` bumps once for the whole change. Workers never touched the line, so apply
  the bump yourself, **serially**, as you merge each PR (`1.0.29 → 1.0.30 → …`) so parallel
  merges never collide on that line.

**Discard churn, stage only the version line, verify one file (the #920 guard).** The Step 5
full suite runs inside the merge worktree and can **churn tracked fixtures** as a side effect
(e.g. `reports/ledger/trials.jsonl` and files under `tests/data/backtest_corpus/**`, which are
**tracked**, not gitignored). A blanket `git commit -a` / `--all` (which stages every modified
tracked file) would sweep that churn into the version-bump commit — exactly the PR #920 incident
(`2e44cb75` committed `pyproject.toml` **plus 14 churned fixtures**; forward-fixed by
`d6e5732c`). Defend it mechanically, in this order, **after the
Step 5 full-suite gate and before the bump edit** — do not depend on noticing a multi-file
commit stat:

1. **Discard all working-tree churn** the full suite left behind: `git reset --hard`
   (preferred — it clears both the index and the working tree back to `HEAD`; `git checkout
   -- .` only restores the working tree from the index). **Never `git clean` / `git clean
   -fdx`** here: *Prepare* copies a gitignored `.env` into this worktree, and `git clean` would
   wipe it (that is exactly why `gh-clean`'s non-negotiable #2 exists — a prior `git clean`
   destroyed an operator `.env`). `git reset --hard` / `git checkout -- .` only touch
   already-tracked files, so the copied-in `.env` stays safe — keep it that way. Make any
   *intentional* edit the merge legitimately needs **after** this discard, so it is preserved.
2. **Edit `<version-file>` to the new version, then stage ONLY that file:**
   `git add <version-file> && git commit -m "chore: bump version 1.0.NN -> 1.0.(NN+1)"`.
   **Never stage the bump with `git commit -a` / `--all`** — it stages every modified tracked
   file and is the exact flag that caused #920.
3. **Verify the bump commit is exactly one file before pushing:** `git show --stat HEAD` (or
   `git diff-tree --no-commit-id --name-only -r HEAD`) must list **only** `<version-file>`. If
   anything else appears, **stop — do not push**; discard and redo the bump.

Squash-merge lands the **remote PR head** as-is, so pick one of these two placements — a
local-only bump commit never lands and the merge would ship without the mandated patch bump:

- **On the PR branch, before merge — then PUSH it to the PR head first.** Make the scoped
  `git add <version-file> && git commit -m …` bump (above) on the PR branch and `git push` it
  to the PR's head branch **before** `gh pr merge`, so the commit is part of the remote head
  GitHub squashes. A bump committed only in your local merge worktree (never pushed to the PR
  head) is invisible to the squash and is silently dropped.
- **On `main`, immediately after merge.** Make the same scoped bump commit directly on `main`
  right after the squash-merge and push it. Use this when you cannot push to the PR branch
  (e.g. a fork).

Either way: discard-then-scoped-stage-then-verify, one patch increment per qualifying `main`
merge. Keep the single-pen rule (a second session is PR-only) so serial bumps never collide on
the version line.

## Step 7 — Reconcile the epic

When a **child** PR lands on its epic branch:

- **Update the parent's checklist immediately:** check off this child's item in the epic
  body/task-list. Locate the parent **unambiguously** via the child's `Parent: #N` /
  tracked-by reference or the epic's child checklist that names this issue — never guess.
- **When all children have landed, trigger the epic's integration-acceptance pass.** Re-verify
  **each** epic-level integration acceptance criterion against the **composed whole**,
  adversarially, defaulting to "unmet" when unsure (a child passing in isolation is not the
  epic passing). Only after that pass: run the full suite (Step 5.2) on the epic branch, merge
  the epic to `main` (Step 5.3), bump once (Step 6), and close the epic.

## Step 8 — Close the ticket and checkpoint cleanup

1. **Retire the board item on close.** The board Status options end at **`Validated`**
   (CONVENTIONS.md §3) — there is **no** `Closed`/`Done` option, so do **not** pass a
   fabricated closed option id to `gh project item-edit` (it would fail on an unknown option).
   The GitHub **issue close** (item 2) is the authoritative "done" signal; the state-machine
   `[closed]` node is that closed issue, not a board Status. So on close, do exactly one of:
   - **(a) Leave the item at `Validated`** — the terminal pipeline Status. The closed issue is
     the done signal; the item simply stops advancing. Simplest; keeps the merged PR's history
     visible on the board.
   - **(b) Remove the item from the board** — archive or delete it so the active board shows
     only in-flight work:
     `gh project item-archive --id <PVTI-item-id> --owner <board-owner> <board-number>`
     (or `item-delete`). Use `gh project item-edit --id <PVTI-item-id> --project-id <§3>
     --field-id <§3> --clear` only to *clear the Status field value*, never to invent a closed
     state.

   Mechanics + the project/field/option IDs are in CONVENTIONS.md §3 — reference them; never
   use labels for status, per the D1 veto. Pick one behavior consistently for the pipeline;
   (a) is the low-friction default.
2. **Close the issue — but only when the work is *verified done*** (merged **and** its
   acceptance criteria met). Do **not** close a ticket whose ACs are unmet or whose deferrals
   are untracked: file the tracked follow-up first (no silent scope reduction), then close.
   Leaving verified-done work open corrupts the triage signal; closing unverified work hides
   gaps. Close the epic only after its integration-acceptance pass (Step 7).
3. **Checkpoint cleanup intent before mutation.** Following **CONVENTIONS.md §11**,
   atomically edit the sprint's unique current checkpoint with the merged issue/PR and durable
   merge evidence, resulting app version, completed queue movement and dependency release, and
   next safe action with its accountable actor. Record this merge worktree/session and scratch
   branch as **cleanup pending**; the next safe action is to invoke `gh-clean`. Reconcile against
   current durable evidence immediately before writing and stop on an ambiguous checkpoint,
   concurrent revision, or evidence mismatch. This pre-clean intent checkpoint must be durable
   before `gh-clean` mutates the Git worktree registry or deletes a branch; do not represent
   cleanup as completed yet.
4. **Invoke `gh-clean`** to remove this pipeline's own worktrees / stale branches / temp
   artifacts. gh-clean refuses to touch the operator's main worktree and never `git clean`s
   where a `.env` lives, and runs the profile's `<artifacts-gate>` before finishing (DW-8). Sync the base
   branch (`git fetch origin`) so the next merge plans against fresh `main`. Verify the cleanup
   report against durable Git evidence: the removed worktree no longer appears in
   `git worktree list`, the scratch branch is retired as reported, and the base ref is synced to
   the expected merged commit. If cleanup refuses or only partially completes, leave the
   checkpoint at cleanup pending and surface the retained state; do not hand off or continue.
5. **Write the final post-clean checkpoint before handoff.** From a surviving lead/merge control
   context outside the removed worktree, reconcile again and atomically edit the §11 checkpoint:
   remove the cleaned worktree and merge session from in-flight state, record the cleaned or
   retained branch result, synchronized base branch, durable merge evidence and resulting app
   version, preserve the queue/dependency movement, and name the next safe action and accountable
   actor. This is the durable cleaned-worktree/branch/base state after the `gh-clean` worktree-
   registry mutation. Re-read and verify the completed edit. Do not hand off or begin the next
   merge until this final checkpoint is durable.

## Operating principles

- **One merge policy, one merger.** gh-lead and the sweeper delegate here; there is no second
  merge path. If you ever find merge logic inlined elsewhere, route it through this skill.
- **Live state over cached state.** Re-query Codex threads, CI, and the board Status at merge
  time — asynchronous posts make review-time snapshots stale.
- **Surface, don't override.** A stuck Codex gate, an unsigned D7 surface, an `Unsafe!` label,
  or a rebase that invalidates a validation — stop and surface to the operator. Never merge to
  keep momentum.
- **Isolation.** All git ops run in your dedicated merge worktree; nothing touches the
  operator's main or another session's worktree. gh-clean tears it down.
- **No silent scope reduction.** Any deferral (a Codex comment, a follow-up, a partial
  integration) is a tracked issue, called out loudly — never resolve-and-ignore.

## Worked example — DRY RUN on a two-PR fixture (no execution)

**Purpose:** demonstrate the merge-order/collision plan, the Codex re-check, and the D7 gate
producing an *exact command list* **without executing** anything. This is a hand-run of the
F09 acceptance fixture: two open **`Validated`** standalone PRs whose diffs overlap on one
file. A dry run **plans and prints** — it never calls `gh pr merge`. (The fixture file paths
and gate commands below are THIS project's PROFILE.md instance values; substitute your
profile's.)

**Fixture (both at board Status `Validated`, both target `main`):**

| PR | Issue | `gh pr diff --name-only` | Codex | Touches live-order/`.env`/track-5? |
|---|---|---|---|---|
| #901 | #801 `[TASK] CONFIG - add vol-floor entry gate` | `src/server/config_loader.py`, `tests/data/config_loader_snapshot.json`, `tests/test_config_fields.py`, `pyproject.toml`(version untouched) | posted, **0 unresolved** | no |
| #902 | #802 `[TASK] CONFIG - widen vol-floor validation` | `src/server/config_loader.py`, `tests/test_config_validation.py`, `pyproject.toml`(version untouched) | posted, **0 unresolved** | no |

**Collision analysis (Step 2):** the diff file-sets intersect on
`src/server/config_loader.py` → **real overlap → serialize** (never merge #902 straight after
#901 without a rebase). Both are **ConfigField** PRs, so each regenerates
`config_loader_snapshot.json` — the "one ConfigField in flight" rule reinforces serialize.
`pyproject.toml` appears in both but the version line is worker-untouched, so it is **not** an
overlap trigger (Step 2.3). No `[CHILD]` PRs → no epic reconcile; both are `main` boundaries.

**Order rationale (Step 2.3):** #901 first — it is the smaller-blast change and it owns the
snapshot regeneration (it edits the snapshot file directly), so landing it first makes #902's
rebase the cheap direction. #902 second, **after a rebase** onto the new `main` (its
`config_loader.py` region must re-apply cleanly on top of #901's; if the rebase materially
changes #902's diff, kick #902 back to `Reviewed` rather than merge on stale validation).

**Exact command list the dry run WOULD run (printed, not executed):**

```sh
# --- prepare: dedicated merge worktree off latest main (never operator main) ---
git -C <operator-main-repo> fetch origin
git -C <operator-main-repo> worktree add --detach <merge-worktree> origin/main
cd <merge-worktree> && git checkout -b gh-merge-<session>

# --- verify the collision on ACTUAL diffs (not ticket file lists) ---
gh pr diff 901 --name-only     # -> includes src/server/config_loader.py
gh pr diff 902 --name-only     # -> includes src/server/config_loader.py  => OVERLAP => serialize

# ============ PR #901 (first: smaller blast, owns the snapshot) ============
# Step 3 re-check Codex at merge time (CONVENTIONS.md §8):
gh pr view 901 --json reviews,reviewDecision
gh api graphql -f query='{ repository(owner:"<repo-owner>",name:"<repo-name>"){ pullRequest(number:901){ reviewThreads(first:100){ nodes{ isResolved } } } } }'
#   require: Codex review posted AND every thread isResolved==true ; else STOP + surface
# Step 4 D7 (CONVENTIONS.md §7d): #901 touches no live-order/.env/track-5 surface -> no human gate
# Step 5.0 materialize the MERGED tree in the worktree (gate the code, NOT clean main):
gh pr checkout 901 && git rebase origin/main        # tree under test == what the squash ships
# Step 5.1 fast gates + 5.2 full suite ON THAT MERGED TREE (this IS a main boundary, once before THIS merge):
<fast-gates>                                        # the profile's fast-gate commands
<full-suite>                                        # the profile's full-suite command
# Step 6 version bump (touched bump-paths -> patch bump; worker left the line; I apply it):
git reset --hard                                    # discard full-suite fixture churn FIRST (never `git clean`: .env lives here)
#   edit <version-file> version  1.0.NN -> 1.0.(NN+1)  on the PR branch, then stage ONLY that file:
git add <version-file> && git commit -m "chore: bump version 1.0.NN -> 1.0.(NN+1)"
git show --stat HEAD                                # VERIFY exactly one file (<version-file>) -> else STOP, discard, redo
git push origin HEAD:<pr901-head-branch>            # MUST push to the PR head; squash lands the REMOTE head
# Step 5.3 squash-merge to main (lands the pushed head, bump included):
gh pr merge 901 --squash --delete-branch
# Step 8 close the issue (the authoritative "done" signal), then retire the board item:
gh issue close 801
#   board has NO closed Status option -> either leave item at Validated (default), or remove it:
gh project item-archive --id <PVTI-item-id-for-801> --owner <board-owner> <board-number>   # option (b); or leave at Validated
#   (invoke gh-clean to drop the worktree; the profile's artifacts gate green)

# ============ PR #902 (second: REQUIRES rebase onto new main first) ============
git -C <pr902-worktree> fetch origin
git -C <pr902-worktree> rebase origin/main          # re-apply config_loader.py region on top of #901
#   resolve conflicts; re-run TARGETED tests only (not full suite yet):
#   pytest -q tests/test_config_validation.py
#   if the rebase materially changed #902's diff -> kick back to Reviewed (do NOT merge stale)
# Step 3 re-check Codex again (threads post async; re-query AFTER the rebase push):
gh pr view 902 --json reviews,reviewDecision
gh api graphql -f query='{ repository(owner:"<repo-owner>",name:"<repo-name>"){ pullRequest(number:902){ reviewThreads(first:100){ nodes{ isResolved } } } } }'
# Step 4 D7: #902 touches no high-risk surface -> no human gate
# Step 5.0/5.1/5.2 the rebase above already put the MERGED tree in the worktree; gate it (not clean main):
<fast-gates>                                        # the profile's fast-gate commands
<full-suite>                                        # second main boundary — do NOT rely on #901's run
# Step 6 version bump SERIALLY (1.0.(NN+1) -> 1.0.(NN+2)) so the two merges never collide on the line:
git reset --hard                                    # discard full-suite fixture churn FIRST (never `git clean`: .env lives here)
#   edit <version-file> version 1.0.(NN+1) -> 1.0.(NN+2), then stage ONLY that file:
git add <version-file> && git commit -m "chore: bump version 1.0.(NN+1) -> 1.0.(NN+2)"
git show --stat HEAD                                # VERIFY exactly one file (<version-file>) -> else STOP, discard, redo
git push origin HEAD:<pr902-head-branch>            # push to the PR head BEFORE merge, else the squash drops it
# Step 5.3 squash-merge:
gh pr merge 902 --squash --delete-branch
# Step 8 close the issue, then retire the board item (no closed Status option — leave at Validated or remove):
gh issue close 802
gh project item-archive --id <PVTI-item-id-for-802> --owner <board-owner> <board-number>   # option (b); or leave at Validated
```

**Dry-run verdict (what it prints, having executed nothing):** order = **#901 then #902**;
reason = real `config_loader.py` overlap + dual snapshot regeneration force serialize, #901
first as the smaller/snapshot-owning change, #902 rebased onto the new `main`; both pass the
Codex re-check with zero unresolved threads and neither trips the D7 surface gate; two
`main`-boundary full-suite runs (one per merge, not one shared); two **serial** patch bumps.
No `gh pr merge` (or any mutating command) is executed in a dry run — it stops here with the
plan above for the operator to approve.

## Worked example — Step 0 merge-ownership refusal (and the positive case)

**Purpose:** demonstrate the Step 0 gate as an *exact command list* that **stops after
Step 0** for a non-owner session, and — as the positive control — proceeds for the recorded
owner. Like the DRY RUN above this executes nothing; it shows precisely where the sequence
halts and what never runs.

**Fixture:** the §11 sprint-control checkpoint records `merge-owner session identity:
sess-A-0001`. One `Validated` PR (#903) is ready to land. Two sessions — `sess-A-0001` (the
recorded owner) and `sess-B-0002` (a *different* session under the *same* shared
`<automation-login>`) — could each invoke gh-merge.

### Case 1 — a NON-OWNER session (`sess-B-0002`) invokes gh-merge

```sh
# Step 0.1 read the recorded owner from the §11 checkpoint (REST-first, §11): locate the §11
#   marker, read the "merge-owner session identity" field from that one comment — NOT by login:
gh api repos/<repo>/issues/<sprint-control#>/comments --jq '<select §11 marker>'
#   -> checkpoint "merge-owner session identity" = sess-A-0001
# Step 0.2 compare to my own session token: sess-B-0002
# Step 0.3 sess-B-0002 != sess-A-0001  => REFUSE per the Step 0.3 refusal condition
#   (no worktree, no gate, no merge, no version-line edit — stated once in Step 0 above):
#   >>> STOP HERE. No `git worktree add`. No `gh pr merge`. No `<version-file>` edit. <<<
#   Surface (fail loud + specific, Step 0.5):
#   "Refusing to merge #903: this session (sess-B-0002) is not the recorded merge-owner
#    (sess-A-0001). Record: <§11 checkpoint comment URL> (its §11 checkpoint marker).
#    Handing #903 to sess-A-0001's queue; staying PR-only."
```

**What did NOT run:** no *Prepare* worktree (`git worktree add` never issued), no Step 1
board read, no Step 2 collision plan, no Step 3 Codex re-check, no Step 5 fast gates /
`pytest`, no Step 6 version bump — the sequence never reaches them. That is the coordination
lock working: a second same-login session cannot race the `<version-file>` version line. The
non-owner does **not** self-appoint; ownership changes only via the operator or the §12
transfer protocol.

### Case 2 — the RECORDED OWNER (`sess-A-0001`) invokes gh-merge

```sh
# Step 0.1 read: "merge-owner session identity" = sess-A-0001
# Step 0.2 compare to my own session token: sess-A-0001
# Step 0.3 sess-A-0001 == sess-A-0001  => OWNER: proceed past Step 0 to Prepare.
git -C <operator-main-repo> fetch origin
git -C <operator-main-repo> worktree add --detach <merge-worktree> origin/main
cd <merge-worktree> && git checkout -b gh-merge-sess-A-0001
#   ... then Step 1..8 exactly as the DRY RUN example above (collision plan, Codex re-check,
#   D7, full-suite gate on the merged tree, squash-merge, serial version bump, epic
#   reconcile, close + checkpoint cleanup) ...
```

**Verdict:** ownership is the **first** gate, before any worktree exists. A non-owner halts
at Step 0.3 with a specific, actionable surface and mutates nothing; only the recorded
owner's token proceeds into *Prepare*. Who the owner is changes solely through the operator
or the §12 transfer protocol — never by a self-service override inside gh-merge.
