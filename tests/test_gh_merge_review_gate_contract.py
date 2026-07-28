"""Structural contract test for gh-merge's completed-review gate (#1155).

Encodes the PR #1150 incident defense directly against ``agents/gh-merge/SKILL.md``
and ``agents/gh-workflow/CONVENTIONS.md``.

The defect: §8 defined the review gate as *zero unresolved ``[change-requested]``
threads*, which is trivially true **before any review exists** — so it could not tell
*reviewed-and-clean* apart from *not-yet-reviewed*. PR #1150 (epic #935, the live kill
path) merged 8 minutes after opening, mid-review; at merge time it had zero threads, so
the gate passed **vacuously**. All nine findings — two P1s on the live kill path —
landed after the merge and stayed unresolved. Epic integration squashes additionally
receive zero CI check-runs, so no second signal existed.

The fix makes the rule mechanical at **one** enforcement point, gh-merge **Step 3.1**:
a merge requires positive evidence of a *completed* review naming the PR's *current*
head SHA. Never-run, still-queued/running, and failed-run all produce the same single
observation (no review-stage review names this head SHA), so one check covers all three;
only the wait-vs-surface disposition differs.

Explicitly guarded **failure condition**: this must not be implemented as a reinstated
Codex gate — the 2026-07-15 "full Claude" de-gating stays intact (Codex addressed if it
posts, never required, never blocking).

Follows the same read-from-disk structural-contract pattern as
``tests/test_gh_merge_bump_guard_contract.py`` and
``tests/test_sprint_ledger_contract.py``, and runs as a normal, unmarked part of
``pytest -q`` (no opt-in/skip marker) so it is part of the default gate.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS = _ROOT / "agents"
_MERGE = _AGENTS / "gh-merge" / "SKILL.md"
_REVIEW = _AGENTS / "gh-review" / "SKILL.md"
_CONVENTIONS = _AGENTS / "gh-workflow" / "CONVENTIONS.md"
_REVIEW_ROUTINE = _ROOT / "routines" / "gh-review.routine.md"
_GH_LEAD = _AGENTS / "gh-lead" / "SKILL.md"

# The definition #1155 supersedes. Split so this file is not itself an occurrence.
_SUPERSEDED_GATE_DEFINITION = "the review gate — the PR reached " + "`Validated`"

# Step 3.1's ACTUAL input contract: the WRITER-side obligation that the review stage emits
# the SHA in its terminal verdict-summary body. Everything the gate reads depends on this
# one sentence, so it is pinned verbatim and bound to the reader that consumes it.
_WRITER_OBLIGATION = "State the head SHA you reviewed."
_WRITER_OBLIGATION_CONTEXT = "A top-level body is only for the overall verdict summary."

# The canonical refusal MECHANIC. Split so THIS test file is not itself an occurrence
# of the substring it counts (the marker-splitting technique used across the ledger
# tests). Unlike the requirement *statement* -- which §8 is supposed to state -- the
# mechanic must live in exactly one place: gh-merge Step 3.1.
_REFUSAL_MECHANIC = "review-stage verdict summary names " + "the PR's current head SHA"

# The head-SHA lookup, reused from gh-review's routine idempotency guard rather than
# invented a second time.
_HEAD_SHA_READ = "gh pr view <pr> --json headRefOid"
_REVIEWS_READ = "gh api repos/<repo>/pulls/<pr>/reviews"

# gh-review's existing precedent sentence, cross-checked for consistency: Step 3.1 is
# only reusable if the review stage still guards on (and therefore states) the head SHA.
_REVIEW_PRECEDENT = "review comment for this " + "exact head SHA already exists"

_STEP3_HEADING = "## Step 3 — Confirm the review gate at merge time (D5)"
_STEP31_HEADING = "### Step 3.1 — Require a completed review of the PR's *current* head SHA"
_WORKED_EXAMPLE_HEADING = "## Worked example — Step 3.1 unreviewed-head-SHA refusal"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _flat(text: str) -> str:
    """Collapse whitespace so a needle still matches across a markdown line wrap."""
    return " ".join(text.split())


def _step3_section(text: str) -> str:
    start = text.index(_STEP3_HEADING)
    end = text.index("## Step 4 —")
    return text[start:end]


def _section8(text: str) -> str:
    start = text.index("## 8. Review gate")
    end = text.index("## 9. Version-bump")
    return text[start:end]


def _worked_example(text: str) -> str:
    return text[text.index(_WORKED_EXAMPLE_HEADING) :]


def _occurrences(needle: str) -> dict[Path, int]:
    found: dict[Path, int] = {}
    flat_needle = _flat(needle)
    for path in sorted(_ROOT.rglob("*.md")):
        count = _flat(_read(path)).count(flat_needle)
        if count:
            found[path.relative_to(_ROOT)] = count
    return found


# ---------------------------------------------------------------------------
# AC #1 -- a PR whose head SHA has no completed review is refused at Step 3
# ---------------------------------------------------------------------------


def test_step3_requires_a_completed_review_of_the_current_head_sha() -> None:
    step3 = _flat(_step3_section(_read(_MERGE)))
    lowered = step3.lower()

    # The requirement itself, and that it is POSITIVE evidence (not an absence check).
    assert _REFUSAL_MECHANIC in step3, "Step 3 must state the head-SHA refusal mechanic"
    assert "absence of a review is a block, not a pass" in lowered
    assert "necessary but not sufficient" in lowered  # zero threads alone is not enough
    assert "vacuous" in lowered  # names the failure mode being closed

    # The refusal is a real stop: nothing downstream runs.
    assert "do not merge it" in lowered
    assert "no `gh pr merge`" in step3.lower()


def test_completion_discriminator_is_the_body_never_the_inline_count() -> None:
    """The body is the discriminator; author, state and inline-count are all unreliable.

    Empirically settled on kalshi-boy PR #1179 (lead-supplied measurement, head
    ``72fd2286``): sequential inline POSTs DO create review objects -- ``state: COMMENTED``,
    not ``PENDING`` -- carrying the current head SHA with an EMPTY body, 3m53s before the
    genuine verdict existed. Worse, on that PR the empty-bodied objects were minted by
    **gh-fixer replying in-thread**, under the same automation login the reviewer uses. So:

    * ``user.login`` cannot discriminate (review and fix stages share the account);
    * ``state != "PENDING"`` cannot discriminate (the phantoms are COMMENTED);
    * ``inline == 0`` MUST NOT be used -- §8's batched recipe legitimately posts a verdict
      body together with inline comments (same PR, 13:25:15Z: body 1889, inline 1).

    Only a non-empty body naming the head SHA separates the verdict from the phantoms.
    """
    step3 = _flat(_step3_section(_read(_MERGE)))
    lowered = step3.lower()

    # The measured evidence is cited, not assumed.
    assert "measured, not assumed" in lowered
    assert "#1179" in step3

    # The gh-fixer vector is named explicitly -- the fix must survive a fixer's replies,
    # which is strictly harder than surviving a reviewer's posting sequence.
    assert "manufactured by `gh-fixer`" in step3 or "manufactured by gh-fixer" in lowered
    assert "author identity does not discriminate" in lowered
    assert "same" in lowered and "<automation-login>" in step3

    # state != PENDING is explicitly disqualified as a discriminator.
    assert "not** `pending`" in lowered or "not `pending`" in lowered

    # The inline-count trap is called out and forbidden, with the batched-recipe reason.
    assert "never on the inline-comment count" in lowered
    assert "do not" in lowered and "inline == 0" in step3
    assert "b607aa52" in step3, "the batched verdict+inline counter-example must be cited"

    # The false-negative branch is answered by observation, not asserted away.
    assert "the converse failure does not occur" in lowered
    assert "livelock" in lowered


def test_step3_input_contract_is_the_review_routines_writer_obligation() -> None:
    """Pin the WRITER-side obligation Step 3.1 consumes, and bind the reader to it (F3).

    ``_REVIEW_PRECEDENT`` (below) pins gh-review's *reader-side* idempotency guard -- that
    is gh-review checking ITSELF before it acts, which Step 3.1 does not consume. What
    Step 3.1 actually consumes is the obligation that the review stage **emits** the SHA,
    in ``routines/gh-review.routine.md`` step 4. Before this test, no test in this file
    referenced that file at all: deleting that one sentence would silently remove the new
    gate's only input with the whole suite still green.

    Two halves, deliberately: (a) preservation -- the routine keeps the obligation; (b)
    forward-looking -- gh-merge names that file as its input contract, so the reader and
    the writer cannot drift apart unnoticed. (b) is what makes this fail on unpatched main.
    """
    routine = _read(_REVIEW_ROUTINE)
    flat_routine = _flat(routine)

    # (a) The writer obligation survives -- and stays attached to the VERDICT SUMMARY,
    #     which is what Step 3.1 matches on (see the F2 criterion above).
    assert _WRITER_OBLIGATION in flat_routine, (
        "routines/gh-review.routine.md must keep 'State the head SHA you reviewed.' -- "
        "it is the entire input contract for gh-merge Step 3.1"
    )
    assert _WRITER_OBLIGATION_CONTEXT in flat_routine, (
        "the head-SHA obligation must stay bound to the top-level verdict summary"
    )
    # The obligation must sit in the SAME step as the verdict-summary sentence, not drift
    # into an unrelated part of the routine.
    assert flat_routine.index(_WRITER_OBLIGATION) - flat_routine.index(
        _WRITER_OBLIGATION_CONTEXT
    ) < 200, "the two sentences must remain adjacent (same routine step)"

    # (b) gh-merge Step 3.1 names that file as the source of its input, and quotes the
    #     obligation verbatim -- so a future edit to either side breaks this test.
    step3 = _flat(_step3_section(_read(_MERGE)))
    assert "routines/gh-review.routine.md" in step3, (
        "Step 3.1 must cite the writer-side obligation it depends on"
    )
    assert "writer-side obligation this gate consumes" in step3.lower()
    assert _WRITER_OBLIGATION in step3, "Step 3.1 quotes the obligation verbatim"
    assert _WRITER_OBLIGATION_CONTEXT in step3


def test_completed_means_the_verdict_summary_body_not_any_review_object() -> None:
    """*Completed* is the terminal verdict summary, not a bare inline-comment object (F2).

    §8's 422 recipe permits N sequential ``POST .../pulls/<n>/comments`` calls. Where that
    path creates a review object per comment, each carries ``commit_id == headRefOid`` and
    an EMPTY body -- so a ``commit_id``-only criterion lets the FIRST inline comment of an
    in-progress review satisfy the gate while the blocking finding is still unposted:
    #1150's vacuous-clean at ~1 minute instead of 8. The non-empty top-level body is the
    only artifact that separates a finished review from a partial one.
    """
    step3 = _flat(_step3_section(_read(_MERGE)))
    lowered = step3.lower()

    # The primary criterion is the verdict-summary BODY naming this head SHA.
    assert "verdict summary" in lowered
    assert "non-empty top-level body" in lowered
    assert "this is the primary criterion" in lowered
    # ...and commit_id is explicitly demoted to corroboration.
    assert "corroborating" in lowered and "not sufficient on its own" in lowered

    # Bare inline-comment review objects are explicitly excluded.
    assert "bare inline-comment review objects do not count" in lowered
    assert "empty body" in lowered
    # The lookup itself filters to non-empty bodies -- the criterion is mechanical, not prose.
    assert 'select(.body != "")' in step3

    # The false-negative half of the ambiguity is closed too: inline-only, no summary =>
    # surface a contract violation, never merge.
    assert "is **not** a completed review" in step3 or "not a completed review" in lowered


def test_step3_names_the_lookup_and_reuses_gh_reviews_head_sha_precedent() -> None:
    step3 = _flat(_step3_section(_read(_MERGE)))
    lowered = step3.lower()

    # One `gh pr view` for the current head SHA + one reviews read for what was reviewed.
    assert _HEAD_SHA_READ in step3
    assert _REVIEWS_READ in step3
    assert "commit_id" in step3  # the review object's own reviewed-SHA field

    # Reuse, not reinvention -- Step 3 says so, and gh-review still carries the pattern.
    assert "do not invent a second mechanism" in lowered
    assert "idempotency guard" in lowered
    assert _REVIEW_PRECEDENT in _flat(_read(_REVIEW)), (
        "gh-review must keep its head-SHA guard -- Step 3.1 reuses that precedent"
    )


# ---------------------------------------------------------------------------
# AC #2 -- a failed run, an in-flight run, and a never-started run all refuse
# ---------------------------------------------------------------------------


def test_step3_collapses_never_run_in_flight_and_failed_into_one_check() -> None:
    step3 = _step3_section(_read(_MERGE))
    lowered = " ".join(step3.lower().split())

    # All three absence-causes are named, and named as ONE observation.
    assert "never started" in lowered
    assert "queued or running" in lowered
    assert "failed" in lowered
    assert "one check, three absence-causes" in lowered

    # In-flight -> WAIT (the #1150 race), using the observed review latency window.
    assert "wait and re-poll" in lowered
    assert "7–16 min" in step3, "the observed review latency window must be stated"

    # Failed -> treated as unreviewed AND surfaced, because a failed run is silent.
    assert "stop and surface" in lowered
    assert "silent" in lowered
    assert "nothing alerts" in lowered


def test_merge_is_pinned_to_the_step31_validated_sha() -> None:
    """The gate must hold across its OWN enforcement window (the F1 TOCTOU finding).

    Step 3.1 validates a head SHA, then Step 4 (D7), 5.0, 5.1 and 5.2's full suite (a 7-8
    min baseline) all run before ``gh pr merge``. If the merge re-reads "the current head"
    it lands code Step 3.1 never saw and the full suite never covered -- the #1150 race
    narrowed, not closed. The binding is ``--match-head-commit`` carrying Step 3.1's SHA.
    """
    merge = _read(_MERGE)
    step3 = _flat(_step3_section(merge))
    lowered = step3.lower()

    # (a) Step 3.1 carries the SHA forward rather than dropping it, and says why.
    assert "carry the validated sha forward to the merge" in lowered
    assert "--match-head-commit" in step3
    assert "time-of-check/time-of-use" in lowered
    assert "never re-read it" in lowered or "never re-read" in lowered

    # (b) NO executable merge invocation anywhere in the file may be unpinned -- an
    #     unpinned `gh pr merge <n> --squash` IS the hole, so the count must be zero.
    invocations = re.findall(r"^\s*gh pr merge \S+ --squash[^\n]*", merge, re.MULTILINE)
    assert invocations, "the merge command must appear in the skill"
    unpinned = [i.strip() for i in invocations if "--match-head-commit" not in i]
    assert not unpinned, f"every `gh pr merge` must pin the reviewed SHA: {unpinned}"

    # (c) Step 5.3 states the flag is mandatory and that a refusal is NOT to be forced past.
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())
    assert "not optional" in lowered5
    assert "do not force it through" in lowered5
    # The one legitimate head movement (this procedure's own bump commit) is PROVED, not assumed.
    assert "git rev-parse head^" in lowered5


def test_dry_run_example_pins_both_merge_sites_to_the_reviewed_sha() -> None:
    # Wiring honesty: the copy-pastable DRY-RUN list is what an agent actually follows, so
    # both of its merges must carry the pin and the parent proof -- not just the prose.
    merge = _read(_MERGE)
    example = merge[
        merge.index("## Worked example — DRY RUN") : merge.index("## Worked example — Step 0")
    ]
    assert example.count("--match-head-commit") == 2
    assert example.count('git rev-parse HEAD^') == 2, "each merge site proves its parent"
    # The validated SHA is captured into a variable and reused, never re-read at merge time.
    assert "SHA901=$(gh pr view 901 --json headRefOid" in example
    assert "SHA902=$(gh pr view 902 --json headRefOid" in example


def test_disposition_rows_are_disjoint_with_stated_precedence() -> None:
    """The wait/surface rows must not overlap, or a failed run becomes a silent stall (F6).

    The original row 1 fired on "or a review exists for an EARLIER SHA on this PR" with no
    age qualifier. A PR reviewed at X, pushed to Y, whose re-review run for Y failed hours
    ago satisfies BOTH rows; read top-down an agent waits and re-polls forever on a run
    that will never post. Neither disposition merges unsafely -- so this is a stall, not a
    gate hole -- but it is the same invisibility class the ticket exists to close.
    """
    step3 = _flat(_step3_section(_read(_MERGE)))
    lowered = step3.lower()

    assert "the rows are disjoint" in lowered
    # The age test decides, and the surface row wins the overlap explicitly.
    assert "row 2 wins regardless of what exists for earlier shas" in lowered
    assert "takes precedence" in lowered
    # Row 1's earlier-SHA clause is conjunctive with the age test, not a bare `or`.
    assert "younger than that latency **and**" in step3
    # Waiting is bounded -- a re-poll that finds nothing escalates rather than looping.
    assert "moves the pr to row 2" in lowered
    assert "silent *stall*" in step3 or "silent\n*stall*" in _read(_MERGE)


def test_step3_head_sha_match_is_exact_so_a_new_push_invalidates_the_review() -> None:
    lowered = " ".join(_step3_section(_read(_MERGE)).lower().split())
    assert "a review of an earlier commit does not carry" in lowered
    assert "rebase" in lowered  # Step 2.4 rebase invalidates the prior pass too


def test_step3_names_the_epic_squash_zero_ci_case() -> None:
    # #1150 was an epic integration squash: zero CI check-runs, so green CI could not
    # have served as a second signal. Step 3.1 must say why it is load-bearing there.
    lowered = " ".join(_step3_section(_read(_MERGE)).lower().split())
    assert "zero ci check-runs" in lowered


# ---------------------------------------------------------------------------
# AC #4 + explicit failure condition -- Codex is NOT reinstated as a gate
# ---------------------------------------------------------------------------


def test_codex_de_gating_survives_verbatim_in_step3() -> None:
    step3 = _step3_section(_read(_MERGE))
    lowered = " ".join(step3.lower().split())

    # The pre-existing de-gating clauses must still be there, unweakened.
    assert "do not re-check or wait on codex as a gate" in lowered
    assert "pending, absent, or never posted must not block the merge" in lowered
    assert "do not treat \"zero unresolved codex threads\" as a merge precondition" in lowered
    # ...and a present Codex review is still addressed (de-gated, not banned).
    assert "addressed" in lowered and "gh-fixer" in lowered


def test_new_gate_explicitly_disclaims_being_a_codex_gate() -> None:
    merge = _read(_MERGE)
    lowered = " ".join(merge.lower().split())
    # Stated at the enforcement point...
    step3_lowered = " ".join(_step3_section(merge).lower().split())
    assert "not a reinstated codex gate" in step3_lowered
    assert "claude review stage's own completion" in step3_lowered
    # ...and the new check must not have added any wait-on-Codex language anywhere.
    assert "wait for codex" not in lowered
    assert "codex review is required" not in lowered
    assert "requires a codex" not in lowered
    # §8's statement of the requirement carries the same disclaimer.
    assert "does **not** re-gate codex" in " ".join(_section8(_read(_CONVENTIONS)).lower().split())


def test_conventions_section_8_keeps_codex_de_gated() -> None:
    # Pure preservation guard: passes on pre-#1155 main and must keep passing after.
    lowered = " ".join(_section8(_read(_CONVENTIONS)).lower().split())
    assert "codex is addressed if present, never required" in lowered
    assert "never required" in lowered and "never blocks" in lowered
    assert "de-gated, not banned" in lowered


# ---------------------------------------------------------------------------
# AC #6 -- §8 states the requirement and POINTS AT Step 3 (single enforcement)
# ---------------------------------------------------------------------------


def test_conventions_section_8_states_requirement_and_points_at_step_3() -> None:
    section8 = _section8(_read(_CONVENTIONS))
    lowered = " ".join(section8.lower().split())

    assert "absence of a review is a block, not a pass" in lowered
    assert "current head sha" in lowered
    assert "enforced **exactly once**" in lowered
    assert "`gh-merge`'s **step 3**" in lowered


def test_conventions_section_8_does_not_restate_the_step_3_mechanics() -> None:
    """§8 names the requirement; the mechanics AND the reasoning live only at Step 3 (F4).

    Rebuilt after review: the original needle list covered only *commands* (`headRefOid`,
    the two reads, `7-16`, `wait and re-poll`) -- which §8 never had -- so it passed by
    construction, and passed on unpatched `main` too, carrying no information either way.
    It certified AC6's "without restating" half while being unable to detect the three
    things §8 had in fact grown a second copy of: the absence-cause taxonomy, the
    failed-run-is-silent rationale, and the #1150 incident narrative.

    Fixed two ways: a positive anchor (so the test fails when §8's requirement is absent,
    i.e. on unpatched main -- it can no longer pass vacuously), and a needle list widened
    to the REASONING, not just the commands.
    """
    section8 = _flat(_section8(_read(_CONVENTIONS)))

    # Positive anchor FIRST. Without this the assertions below are vacuously true whenever
    # §8 says nothing at all -- exactly the vacuous-pass defect this whole PR exists to fix.
    assert "enforced **exactly once**" in section8, (
        "§8 must state the requirement before this guard can constrain how it states it"
    )

    mechanics = (
        # --- commands / lookup (original list) ---
        _REFUSAL_MECHANIC,
        _HEAD_SHA_READ,
        _REVIEWS_READ,
        "headRefOid",
        "7–16",
        "wait and re-poll",
        "--match-head-commit",
        # --- reasoning that belongs ONLY at the enforcement point (added after review) ---
        "never started",  # (1) the three-absence-causes collapse
        "queued/running",
        "queued or running",
        "nothing alerts",  # (2) the failed-run-is-silent rationale
        "silently — nothing",
        "check-runs",  # (3) the #1150 narrative + the zero-CI detail
        "after opening, mid-review",
        "nine threads",
        "8 minutes",
        "stop and surface",
    )
    # NB: "verdict summary" is deliberately NOT a needle here -- §8's pre-existing 422
    # recipe uses that phrase ("the overall verdict summary, never the sole carrier of a
    # finding") and that block is byte-identical base-vs-head. Step 3.1 reuses §8's own
    # vocabulary for the completion criterion; it does not duplicate §8's text.
    for mechanic in mechanics:
        assert mechanic not in section8, f"§8 must not restate Step 3's mechanics: {mechanic}"


def test_step3_reasoning_is_canonical_only_in_gh_merge() -> None:
    """Occurrence-count guard for the REASONING, mirroring the refusal-mechanic test (F4).

    A §8-scoped negative assertion cannot fail on a tree where the feature is absent. These
    can: each needle must exist in gh-merge AND nowhere else, so an empty result set (the
    unpatched-main case) fails just as loudly as a duplicated one.
    """
    for needle in (
        "One check, three absence-causes",
        "nothing alerts on it",
        "after opening, mid-review",
    ):
        found = _occurrences(needle)
        assert set(found) == {_MERGE.relative_to(_ROOT)}, (
            f"{needle!r} must be stated exactly once, at the enforcement point: {found}"
        )


def test_no_file_carries_the_superseded_review_gate_definition() -> None:
    """The old definition must not survive anywhere, least of all in a binding block (F5).

    *"the review gate -- the PR reached `Validated`"* is precisely what #1155 kills:
    reaching `Validated` is exactly what #1150 had done, and its gate still read clean.
    The stale-by-omission fix was applied at gh-lead:377 but missed 58 lines below at
    :435 -- inside the **non-negotiables** block, the more binding of the two statements.
    Repo-wide occurrence count so a third copy cannot appear elsewhere later.
    """
    found = _occurrences(_SUPERSEDED_GATE_DEFINITION)
    assert not found, (
        f"superseded review-gate definition ('reached Validated' AS the gate) survives: {found}"
    )

    # ...and the non-negotiables block carries the corrected one, not merely the absence.
    principles = _flat(_read(_GH_LEAD)[_read(_GH_LEAD).index("## Operating principles") :])
    assert "**completed** review of the PR's current head SHA" in principles
    assert "absence of a review is a block, not a pass" in principles
    assert "Reaching `Validated` alone is **not** the gate" in principles


def test_refusal_mechanic_is_canonical_only_in_gh_merge() -> None:
    # Occurrences-count (the test_refusal_condition_is_canonical_only_in_gh_merge
    # pattern): the refusal MECHANIC is stated repo-wide only in gh-merge.
    found = _occurrences(_REFUSAL_MECHANIC)
    assert set(found) == {_MERGE.relative_to(_ROOT)}, found
    assert _CONVENTIONS.relative_to(_ROOT) not in found


# ---------------------------------------------------------------------------
# AC #3 -- no regression on the healthy path; no existing gate weakened
# ---------------------------------------------------------------------------


def test_existing_zero_unresolved_thread_gate_is_not_weakened() -> None:
    lowered = " ".join(_section8(_read(_CONVENTIONS)).lower().split())
    assert (
        "the merge require zero unresolved (`isresolved:false`) `[change-requested]` "
        "threads authored by the review stage" in lowered
    ), "the pre-existing thread gate must survive -- Step 3.1 adds to it, never replaces it"


def test_step3_still_requires_validated_and_no_new_findings() -> None:
    lowered = " ".join(_step3_section(_read(_MERGE)).lower().split())
    assert "confirm the pr is genuinely `validated`" in lowered
    assert "no **new** required-change" in lowered


def test_step3_ordering_positive_evidence_then_findings_then_codex() -> None:
    merge = _read(_MERGE)
    step3 = merge.index(_STEP3_HEADING)
    step31 = merge.index(_STEP31_HEADING)
    step32 = merge.index("### Step 3.2 — Confirm the review's findings are clean")
    step33 = merge.index("### Step 3.3 — Codex is never re-checked")
    step4 = merge.index("## Step 4 —")
    step5 = merge.index("## Step 5 — Full-suite gate, then squash-merge")
    assert step3 < step31 < step32 < step33 < step4 < step5, (
        "the completed-review check must precede the findings check, the Codex note, "
        "the D7 gate, and the merge itself"
    )


# ---------------------------------------------------------------------------
# AC #5 -- the #1150 scenario is a worked-example regression fixture
# ---------------------------------------------------------------------------


def test_1150_worked_example_exists_after_the_step0_example() -> None:
    merge = _read(_MERGE)
    assert _WORKED_EXAMPLE_HEADING in merge
    # Placement matters: the #927 bump-guard test slices the DRY-RUN example as
    # [DRY RUN heading, Step 0 heading), so a new example must land AFTER the Step 0
    # one or it would silently redefine that slice.
    dry_run = merge.index("## Worked example — DRY RUN")
    step0_example = merge.index("## Worked example — Step 0 merge-ownership refusal")
    new_example = merge.index(_WORKED_EXAMPLE_HEADING)
    assert dry_run < step0_example < new_example


def test_1150_worked_example_models_refusal_of_the_8_minute_merge() -> None:
    example = _worked_example(_read(_MERGE))
    lowered = " ".join(example.lower().split())

    assert "#1150" in example
    assert "8 minutes" in lowered or "8 min" in lowered
    assert "mid-review" in lowered
    assert "zero" in lowered and "threads" in lowered  # the vacuous-clean observation
    # It refuses -- the example must NOT model a merge of #1150.
    assert "gh pr merge 1150" not in example
    assert "stop here" in lowered
    # And it covers the silent-failed-run counter-case off the same single check.
    assert "failed" in lowered and "#1118" in example


def test_1150_worked_example_carries_the_healthy_path_positive_control() -> None:
    example = _worked_example(_read(_MERGE))
    lowered = " ".join(example.lower().split())
    # AC #3 replayed as a fixture: #1149 and #1144 are reviewed + clean and still merge.
    assert "#1149" in example and "#1144" in example
    assert "step 3.1 passes" in lowered
    assert "no existing gate is relaxed" in lowered
    # AC #4 replayed: Codex posted on none of the three and gated none of them.
    assert "codex" in lowered and "not a gate" in lowered


def test_1150_worked_example_is_a_dry_run_like_the_others() -> None:
    # The file's established worked-example contract: they execute nothing.
    lowered = " ".join(_worked_example(_read(_MERGE)).lower().split())
    assert "executes nothing" in lowered


def test_dry_run_example_models_the_new_check_at_both_merge_sites() -> None:
    # Wiring honesty (the #927 `count == 2` pattern): the copy-pastable DRY-RUN command
    # list is what an agent actually follows, so it must perform the Step 3.1 head-SHA
    # check before BOTH merges -- otherwise the gate is prose the example silently skips.
    merge = _read(_MERGE)
    example = merge[
        merge.index("## Worked example — DRY RUN") : merge.index("## Worked example — Step 0")
    ]
    assert example.count("--json headRefOid --jq .headRefOid") == 2
    assert example.count('select(.user.login=="<automation-login>")') == 2
    # The login filter ALONE is not the check -- F2 demoted commit_id/login-only matching and
    # made the non-empty verdict-summary body the primary criterion. Counting only the login
    # filter let a DRY-RUN with the discriminator stripped out still pass this guard.
    assert example.count('select(.body != "")') == 2, (
        "both merge sites must carry the F2 body discriminator, not just the login filter"
    )
    lowered = " ".join(example.lower().split())
    # The second site re-checks because a PUSH can move the head inside the first merge's
    # window -- NOT because gh-merge's own rebase moves it. It does not: that rebase is a
    # local test tree that is never published, which is exactly what keeps the Step 5.3
    # parentage proof satisfiable on the healthy path (see the F1-round-2 tests below).
    assert "local test tree only" in lowered
    assert "never pushed" in lowered
    assert "voids its review" in lowered


# --------------------------------------------------------------------------------------
# Round 2 — F1 was fail-closed but UNSATISFIABLE, and the F2 discriminator was applied
# inconsistently. The tests below pin the corrected rules.
# --------------------------------------------------------------------------------------


def test_step5_rebase_is_local_only_and_is_never_published() -> None:
    """The whole F1 round-2 fix rests on one fact: gh-merge never publishes a rebase.

    Round 1 proved the bump's parentage with ``HEAD^ == <reviewed-sha>``. But Step 5.0
    rebases onto ``origin/main``, which REWRITES the PR's commits -- so on the healthy,
    no-attacker path the bump lands on the *rebased* tip, ``HEAD^`` is that tip, and the
    assertion ``exit 1``s. Reproduced in a bare repo: reviewed ``4c01da80`` vs post-rebase
    tip ``c3af1deb``. The push fails too: a rebased branch cannot fast-forward onto the PR
    head, and ``--force`` is forbidden. gh-merge would have refused every PR it rebased.

    The resolution is not a bigger assertion -- it is keeping the rebase LOCAL. ``gh pr
    merge --squash`` re-derives the merged tree server-side from the PR's own commits, so
    the rebased tip never needs to reach the remote; it exists only to gate the right tree.
    Keep it local and the head SHA does not move, which makes every other proof hold.
    """
    merge = _read(_MERGE)
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())

    # (a) The rebase is declared a throwaway local artifact that is never published.
    assert "local test tree only" in lowered5
    assert "throwaway test artifact" in lowered5
    assert "gh-merge never publishes it" in lowered5
    # (b) ...and the REASON is stated, so a later editor cannot "helpfully" push it.
    assert "re-derives that tree server-side" in lowered5
    assert "head sha" in lowered5 and "unmoved" in lowered5
    # (c) A rebase that MUST be published (conflicts) leaves gh-merge entirely.
    assert "kick the pr back to `reviewed`" in lowered5
    assert "does **not** resolve conflicts and publish" in step5.lower()


def test_bump_is_authored_on_the_reviewed_sha_not_the_rebased_tip() -> None:
    """``HEAD^ == <reviewed-sha>`` must hold BY CONSTRUCTION, not by luck (F1 round 2).

    The assertion is only satisfiable if the bump commit's parent really is the reviewed
    commit. That is guaranteed by returning to ``<reviewed-sha>`` before committing the
    bump, rather than committing on whatever ``gh pr checkout`` + ``git rebase`` left in
    the worktree. Without this, the assertion is unsatisfiable on the rebase path -- which
    is exactly the round-1 defect.
    """
    merge = _read(_MERGE)
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())

    assert "author the bump on `<reviewed-sha>`, never on the rebased tip" in lowered5
    assert "git checkout -B gh-merge-bump-<pr> <reviewed-sha>" in step5
    assert "by construction" in lowered5

    # Both DRY-RUN merge sites must actually DO it -- prose alone is what round 1 shipped.
    example = merge[
        merge.index("## Worked example — DRY RUN") : merge.index("## Worked example — Step 0")
    ]
    assert example.count('git checkout -B gh-merge-bump-901 "$SHA901"') == 1
    assert example.count('git checkout -B gh-merge-bump-902 "$SHA902"') == 1
    # ...and the parent proof still guards both of them.
    assert example.count("git rev-parse HEAD^") == 2


def test_head_movement_proof_covers_all_four_cases() -> None:
    """Plain, bump-only, rebase-only and rebase+bump must ALL be reachable (F1 round 2).

    Round 1 handled bump-only and left rebase-only and rebase+bump unsatisfiable. The
    case table is the artifact that makes the omission of a case visible, so pin all four
    rows plus the single-legitimate-movement rule they instantiate.
    """
    merge = _read(_MERGE)
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())

    assert "which head movements are legitimate — exactly one" in lowered5
    for case in ("plain (no rebase, no bump)", "bump only", "rebase only", "rebase + bump"):
        assert f"| {case} |" in step5, f"the head-movement case table must cover: {case}"
    # The two no-bump rows push nothing and pin the reviewed SHA directly.
    assert step5.count("`<reviewed-sha>` directly") >= 2
    # The rebase-only row must say the head is UNCHANGED -- that is the round-1 blind spot.
    assert "**unchanged** — the rebase is local" in step5


def test_no_gh_merge_push_is_ever_non_fast_forward() -> None:
    """The non-``--force`` rule (`:419-421`) must stay satisfiable, not just mandated.

    Round 1 mandated a plain push while Step 5.0 produced a rebased branch that cannot
    fast-forward onto the PR head -- so the rule forbade the only thing that could have
    published it. With the rebase kept local, the only object gh-merge ever pushes is one
    commit authored on top of the current remote head, so a rejection ALWAYS means a
    foreign commit landed. That is what makes "never force" a real refusal rather than a
    dead end.
    """
    merge = _read(_MERGE)
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())

    assert "no push gh-merge makes is ever non-fast-forward" in lowered5
    assert "never needed and never permitted" in lowered5
    assert "a rejection therefore always means a foreign commit landed" in lowered5

    # Nothing anywhere in the skill may push with --force.
    forced = [
        line.strip()
        for line in merge.splitlines()
        if re.search(r"^\s*git push\b", line) and "--force" in line
    ]
    assert not forced, f"gh-merge must never force-push: {forced}"


def test_local_head_proof_is_bound_to_the_pushed_head_by_a_stated_ordering() -> None:
    """Close the local-``HEAD^`` vs pushed-head gap the re-review flagged (F1 round 2).

    The prose described the assertion as being on "the pushed head's parent" while the
    command reads the LOCAL ``HEAD^``. Those coincide only because the bump is authored
    locally and published by a plain push that can only succeed onto the reviewed head --
    an ordering that was never marked load-bearing. If any step re-synced local from
    remote between the bump and the merge, the proof would degrade to "parentage is not
    authorship" (a foreign commit spliced in below ``HEAD^``).
    """
    merge = _read(_MERGE)
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())

    assert "load-bearing, not incidental" in lowered5
    assert "after a successful push the remote head **is** the local `head`" in lowered5
    assert "never re-sync local from remote between the bump and the merge" in lowered5
    assert "parentage is not authorship" in lowered5


def test_foreign_commit_is_refused_at_two_independent_points() -> None:
    """The concurrent-commit race must stay closed under the new ordering (F1 round 2).

    The re-review confirmed round 1 closed it; the fix must not lose that. A foreign
    commit ``C`` lands either before the Step 5.0 checkout (the new checkout assertion, or
    Step 3.1 itself if ``C`` predates its read) or after it (the plain push is rejected
    non-fast-forward). Both catches must be named, and the checkout assertion must exist
    at both DRY-RUN sites -- not only in the prose.
    """
    merge = _read(_MERGE)
    step5 = merge[merge.index("## Step 5 — Full-suite gate, then squash-merge") : merge.index("## Step 6 —")]
    lowered5 = " ".join(step5.lower().split())

    assert "two independent catches, neither forceable" in lowered5
    assert "the checkout assertion is the first of two foreign-commit catches" in lowered5
    assert "rejected non-fast-forward" in lowered5

    example = merge[
        merge.index("## Worked example — DRY RUN") : merge.index("## Worked example — Step 0")
    ]
    assert example.count('[ "$(git rev-parse HEAD)" = "$SHA901" ] || exit 1') == 1
    # #902 starts its local rebase FROM the reviewed commit, which is the same binding.
    assert 'checkout -B gh-merge-tree-902 "$SHA902"' in example


def test_headrefoid_is_documented_as_a_remote_read() -> None:
    """``--json headRefOid`` cannot observe a local rebase (F1 round 2, second thread).

    Round 1's #902 block captured ``$SHA902`` from ``headRefOid`` after a local rebase and
    called it "the POST-rebase SHA". It is not -- it is the PRE-rebase remote head, i.e.
    the exact SHA the comment two lines above had just declared void. The post-rebase
    re-check was therefore satisfied by precisely the stale review it existed to reject.
    """
    example = _read(_MERGE)[
        _read(_MERGE).index("## Worked example — DRY RUN") : _read(_MERGE).index(
            "## Worked example — Step 0"
        )
    ]
    lowered = " ".join(example.lower().split())
    assert "observes the remote, never a local rebase" in lowered
    # And the stale characterisation must be gone.
    assert "post-rebase sha" not in lowered
    assert "the current remote head" in lowered


def test_positive_control_passes_on_the_body_not_on_commit_id_alone() -> None:
    """The healthy-path fixture must model the criterion F2 kept, not the one it demoted.

    Step 3.1 makes the non-empty verdict-summary body the PRIMARY criterion and demotes
    ``commit_id`` to "corroborating, not sufficient on its own". But the worked example's
    positive control still concluded ``Step 3.1 PASSES`` from ``commit_id == def1149`` and
    nothing else, and the fixture table's pass column held only ``commit_id`` values. An
    agent copying that case passes a PR on ``commit_id`` -- which is exactly the #1179
    phantom vector, since those empty-bodied objects carry ``commit_id == <head>`` too.
    """
    example = _worked_example(_read(_MERGE))
    lowered = " ".join(example.lower().split())

    # (a) The table's pass column is the body; commit_id is labelled as corroboration.
    assert "review-stage **verdict-summary body** naming that sha" in lowered
    assert "`commit_id` appears only as the corroborating field it is" in lowered
    assert lowered.count("corroborates") >= 2

    # (b) The positive control passes BECAUSE of the body, and says commit_id is not why.
    assert "a completed verdict summary exists => step 3.1 passes" in lowered
    assert "only corroborates (criterion 2); it is not why this passes" in lowered
    # (c) ...and it states what happens when the body is removed -- the phantom shape.
    assert "strip the body and the same lookup returns [] => refused" in lowered
    assert "which is the #1179 phantom shape" in lowered


def test_every_operative_reviews_lookup_carries_the_body_filter() -> None:
    """Mechanical half of F2 round 2: 5 of 8 instantiated lookups omitted the filter.

    Step 3.1's canonical lookup carries ``select(.body != "")``, but the DRY-RUN sites and
    the #1150 fixture's lookups mostly did not -- so the worked examples, which are what an
    agent actually copies, taught the superseded ``commit_id``/login-only criterion. Every
    lookup in the file must carry the filter, with exactly ONE documented exception: the
    counter-case that deliberately omits it to SHOW what the filter rejects.
    """
    merge = _read(_MERGE)
    lines = merge.splitlines()
    login = 'select(.user.login=="<automation-login>")'

    hits = [i for i, line in enumerate(lines) if login in line]
    assert len(hits) >= 8, f"expected the full set of review lookups, found {len(hits)}"

    missing: list[int] = []
    for i in hits:
        # The filter may wrap onto the following line of the same jq program.
        window = " ".join(lines[i : i + 2])
        if 'select(.body != "")' not in window:
            missing.append(i)

    assert len(missing) == 1, (
        "exactly one lookup may omit the body filter (the demonstration counter-case); "
        f"unfiltered lookups at lines {[i + 1 for i in missing]}"
    )
    # ...and that one must be labelled as deliberate, immediately above it.
    preamble = " ".join(lines[max(0, missing[0] - 3) : missing[0]]).lower()
    assert "deliberately unfiltered" in preamble, (
        "the one unfiltered lookup must be explicitly marked as a demonstration"
    )
    assert "every lookup gh-merge actually performs carries the filter" in preamble
