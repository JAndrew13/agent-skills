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

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS = _ROOT / "agents"
_MERGE = _AGENTS / "gh-merge" / "SKILL.md"
_REVIEW = _AGENTS / "gh-review" / "SKILL.md"
_CONVENTIONS = _AGENTS / "gh-workflow" / "CONVENTIONS.md"

# The canonical refusal MECHANIC. Split so THIS test file is not itself an occurrence
# of the substring it counts (the marker-splitting technique used across the ledger
# tests). Unlike the requirement *statement* -- which §8 is supposed to state -- the
# mechanic must live in exactly one place: gh-merge Step 3.1.
_REFUSAL_MECHANIC = "review-stage review names " + "the PR's current head SHA"

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
    # The exact duplication debt CONVENTIONS.md exists to prevent (cf. §12 vs Step 0):
    # §8 names the requirement; the lookup, refusal, and disposition live only in Step 3.
    section8 = _flat(_section8(_read(_CONVENTIONS)))
    mechanics = (
        _REFUSAL_MECHANIC,
        _HEAD_SHA_READ,
        _REVIEWS_READ,
        "headRefOid",
        "7–16",
        "wait and re-poll",
    )
    for mechanic in mechanics:
        assert mechanic not in section8, f"§8 must not restate Step 3's mechanics: {mechanic}"


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
    # ...including after the rebase, which moves the head SHA and voids the prior review.
    lowered = " ".join(example.lower().split())
    assert "the rebase moved the head sha" in lowered
