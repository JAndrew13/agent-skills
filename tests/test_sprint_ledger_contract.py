"""Structural contract tests for the canonical sprint control ledger (#867),
plus the #834 hybrid claim-identity protocol (§7) and its ledger claim-owner
field (§11), including the AC-5 adversarial same-login/two-token ownership proof.

Also covers the Follow-up Sprint 12 workflow-control batch:
- #869 — the session-to-session handoff-message subsection that extends §11
  (successor identity, handoff reason, fresh reconciliation, and the fail-loud
  "named is necessary, never sufficient" rule), with an adversarial decoy proof
  that a correctly-named successor still STOPS on an inherited/durable mismatch;
- #870 — the §7 sprint-size cap (canonical figure lives only in CONVENTIONS.md;
  gh-lead references §7 and carries the context-pressure planned-handoff trigger);
- the #996 [minor] guard that gh-merge's Step 0 worked-example heading survives.
The #927 gh-merge bump-churn guard has its own file, test_gh_merge_bump_guard_contract.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CONVENTIONS = _ROOT / "agents" / "gh-workflow" / "CONVENTIONS.md"
_LEAD = _ROOT / "agents" / "gh-lead" / "SKILL.md"
_MERGE = _ROOT / "agents" / "gh-merge" / "SKILL.md"

_TEXT_SUFFIXES = frozenset({".md", ".py", ".rst", ".txt"})
_IGNORED_DIRECTORIES = frozenset(
    {
        ".agents",
        ".codex",
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "logs",
        "node_modules",
        "venv",
    }
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).lower().split())


def _contract_surfaces() -> tuple[Path, ...]:
    surfaces: list[Path] = []
    for directory, directory_names, file_names in os.walk(_ROOT):
        directory_names[:] = sorted(
            name for name in directory_names if name not in _IGNORED_DIRECTORIES
        )
        base = Path(directory)
        surfaces.extend(
            base / name
            for name in sorted(file_names)
            if Path(name).suffix.lower() in _TEXT_SUFFIXES
        )
    return tuple(surfaces)


def _occurrences(needle: str) -> dict[Path, int]:
    found: dict[Path, int] = {}
    for path in _contract_surfaces():
        count = _read(path).count(needle)
        if count:
            found[path.relative_to(_ROOT)] = count
    return found


def test_conventions_is_the_only_ledger_schema_definition() -> None:
    marker = "<!-- ks-sprint-" + "checkpoint:v1 -->"
    schema_heading = "### Required compact " + "checkpoint fields"
    # #869 EXTENDS the one §11 schema with the handoff-message subsection -- its
    # heading is part of the single canonical ledger schema, so it too must live
    # only in CONVENTIONS.md (extend this existing guard, never fork a second one).
    handoff_heading = (
        "### Session-to-session handoff "
        + "message (extends the writer-ownership transfer)"
    )
    canonical = {_CONVENTIONS.relative_to(_ROOT): 1}

    assert _occurrences(marker) == canonical
    assert _occurrences(schema_heading) == canonical
    assert _occurrences(handoff_heading) == canonical


def test_lead_and_merge_reference_the_ledger_section() -> None:
    for source in (_LEAD, _MERGE):
        assert "CONVENTIONS.md §11" in _read(source)


def test_lead_cold_boot_refuses_unsafe_dispatch_and_checkpoints_events() -> None:
    lead = _normalized(_LEAD)
    behavioral_references = (
        "cold-boot from the sprint control issue",
        (
            "reconcile the checkpoint against current durable board, issue, pr, "
            "version, branch/worktree, gate, and follow-up evidence"
        ),
        "refuse dispatch",
        "missing, ambiguous, stale against durable evidence",
        "accountable writer",
        "next safe action",
        "after each dispatch",
        "after each merge",
        "after each d7 human-gate sign-off",
        "before an intentional session end",
    )

    for reference in behavioral_references:
        assert reference in lead, f"gh-lead lacks behavioral reference: {reference}"


def test_merge_checkpoints_before_and_after_cleanup_mutation() -> None:
    merge = _normalized(_MERGE)

    pre_clean = merge.index("checkpoint cleanup intent before mutation")
    cleanup = merge.index("4. **invoke `gh-clean`**")
    post_clean = merge.index("write the final post-clean checkpoint")
    assert pre_clean < cleanup < post_clean

    behavioral_references = (
        "cleanup pending",
        "worktree registry",
        "remove the cleaned worktree and merge session from in-flight state",
        "durable cleaned-worktree/branch/base state",
        "durable merge evidence",
        "resulting app version",
        "queue/dependency movement",
        "next safe action",
        "do not hand off or begin the next merge",
    )
    for reference in behavioral_references:
        assert reference in merge, f"gh-merge lacks behavioral reference: {reference}"


# ---------------------------------------------------------------------------
# #834 — hybrid claim-identity protocol (§7) + ledger claim-owner field (§11)
# ---------------------------------------------------------------------------

# Split so the test file itself is not a second occurrence of the canonical
# marker (mirrors the ledger-marker split above).
_HYBRID_HEADING = "### Hybrid claim " + "protocol (shared-login session ownership)"
_LEDGER_FIELDS_HEADING = "### Required compact " + "checkpoint fields"
_CLAIM_OWNER_FIELD = "active-claim owner session token"


def test_hybrid_claim_protocol_is_defined_only_in_conventions() -> None:
    # AC #1: CONVENTIONS.md is the ONLY definition of the hybrid claim protocol.
    # A second copy in any skill/mirror (the duplication debt CONVENTIONS exists
    # to prevent) fails this test.
    assert _occurrences(_HYBRID_HEADING) == {_CONVENTIONS.relative_to(_ROOT): 1}


def _ledger_fields_section() -> str:
    text = _read(_CONVENTIONS)
    start = text.index(_LEDGER_FIELDS_HEADING)
    end = text.index("\n### ", start + len(_LEDGER_FIELDS_HEADING))
    return text[start:end]


def test_ledger_field_records_the_active_claim_owner_token() -> None:
    # AC #4: the §11 in-flight entry records the active-claim owner session token
    # for each claimed issue -- extended in the existing schema, NOT a second
    # ledger schema. Assert the token field lives inside the §11 field list.
    section = _ledger_fields_section().lower()
    assert _CLAIM_OWNER_FIELD in section
    assert "claimed" in section


def test_lead_dispatch_requires_fail_closed_token_scoped_claim() -> None:
    # AC #2/#3/#4: gh-lead's real dispatch instructions require checkpoint
    # cold-boot/reconciliation and a durably verified active-claim reservation
    # BEFORE assignee/In-Progress mutation; refuse a non-empty assignee
    # regardless of login; derive concurrency from the session token; fail loudly
    # on partial/mismatched evidence.
    lead = _normalized(_LEAD)
    behavioral_references = (
        "reserve the claim, verify it, then mutate",
        "reconcile the §11 checkpoint against durable issue, assignee, and board evidence",
        "refuse the ticket if its assignee list is non-empty",
        "a non-empty assignee is the cross-dispatch lock and blocks you",
        "regardless of login",
        "is not proof this session owns it",
        "durably reserve the active claim in the checkpoint under this session's token",
        "verify it by re-reading",
        "fails loudly and issues no further dispatch mutation",
        "derive your own active-worker count from checkpoint claims owned by this session's token",
        "only the matching owner token may later advance or release the claim",
    )
    for reference in behavioral_references:
        assert reference in lead, f"gh-lead lacks behavioral reference: {reference}"


# --- AC #5 adversarial proof: two session tokens, one shared GitHub login ----
#
# Executable reference model of CONVENTIONS.md §7's hybrid claim protocol. It
# exists ONLY to lock the invariant and drive the adversarial ownership proof
# below (there is no production claim engine — the protocol is prose the agent
# follows and the ledger field it consumes). The two evidence sources are kept
# independent: the GitHub ``assignee_login`` (the cross-dispatch LOCK) and the
# checkpoint ``owner_token`` (OWNERSHIP). ``ownership_by_login`` is the
# deliberately-wrong substitution the proof must reject — deciding ownership by
# shared-login equality instead of the session token, exactly the bug #834
# forbids (cf. the sweeper's ``test_deliberately_broken_variant`` discriminator).

_SHARED_LOGIN = "JAndrew13"  # both sessions authenticate as this one login


class _ClaimBlocked(Exception):
    """The fail-closed protocol refused an action pending §11 reconciliation."""


@dataclass
class _ClaimRecord:
    assignee_login: str | None = None
    owner_token: str | None = None


@dataclass
class _HybridClaimLedger:
    login: str = _SHARED_LOGIN
    ownership_by_login: bool = False
    _claims: dict[int, _ClaimRecord] = field(default_factory=dict)

    def _require_consistent(self, issue: int, record: _ClaimRecord) -> None:
        # Orphan/contradictory evidence (exactly one of assignee/owner present)
        # blocks pending reconciliation -- never silently resolved.
        if (record.assignee_login is None) != (record.owner_token is None):
            raise _ClaimBlocked(f"#{issue}: orphan assignee/checkpoint evidence")

    def _is_owner(self, record: _ClaimRecord, session_token: str) -> bool:
        if self.ownership_by_login:
            return record.assignee_login == self.login  # WRONG: login equality
        return record.owner_token == session_token  # RIGHT: token ownership

    def acquire(self, issue: int, session_token: str) -> None:
        record = self._claims.get(issue)
        if record is not None:
            self._require_consistent(issue, record)
            # A non-empty assignee is the cross-dispatch lock: refuse regardless
            # of login (even when record.assignee_login == self.login).
            if record.assignee_login is not None:
                raise _ClaimBlocked(f"#{issue}: already claimed (assignee lock)")
        # Ordered & fail-closed: reserve the owner token, then add the assignee.
        self._claims[issue] = _ClaimRecord(self.login, session_token)

    def advance(self, issue: int, session_token: str) -> None:
        record = self._claims.get(issue)
        if record is None:
            raise _ClaimBlocked(f"#{issue}: no claim to advance")
        self._require_consistent(issue, record)
        if not self._is_owner(record, session_token):
            raise _ClaimBlocked(f"#{issue}: token does not own this claim")

    def active_count(self, session_token: str) -> int:
        return sum(
            1 for record in self._claims.values() if self._is_owner(record, session_token)
        )

    def drop_assignee_only(self, issue: int) -> None:
        # Partial/mismatched state: assignee cleared, checkpoint owner remains.
        self._claims[issue].assignee_login = None


_TOKEN_A = "sess-A-0001"
_TOKEN_B = "sess-B-0002"  # a DIFFERENT session under the SAME shared login
_ISSUE = 834


def test_two_tokens_same_login_cannot_both_own_or_advance() -> None:
    ledger = _HybridClaimLedger()  # correct: token ownership

    ledger.acquire(_ISSUE, _TOKEN_A)
    # Ownership/concurrency are token-scoped, not login-scoped.
    assert ledger.active_count(_TOKEN_A) == 1
    assert ledger.active_count(_TOKEN_B) == 0

    # token B is refused acquisition -- non-empty assignee lock, regardless of
    # the shared login -- and cannot advance A's claim (token mismatch).
    with pytest.raises(_ClaimBlocked):
        ledger.acquire(_ISSUE, _TOKEN_B)
    with pytest.raises(_ClaimBlocked):
        ledger.advance(_ISSUE, _TOKEN_B)

    # token A owns and may advance its own claim.
    ledger.advance(_ISSUE, _TOKEN_A)

    # Removing ONLY the assignee must not let B steal it: orphan checkpoint
    # evidence blocks pending reconciliation instead of reading as "free".
    ledger.drop_assignee_only(_ISSUE)
    with pytest.raises(_ClaimBlocked):
        ledger.acquire(_ISSUE, _TOKEN_B)
    with pytest.raises(_ClaimBlocked):
        ledger.advance(_ISSUE, _TOKEN_B)


def test_proof_fails_if_login_equality_is_substituted_for_token_ownership() -> None:
    # The discriminating half of AC-5: under a login-equality ownership rule the
    # SAME scenario lets token B steal the claim -- proving the token-ownership
    # test above genuinely depends on token identity, not the shared login.
    broken = _HybridClaimLedger(ownership_by_login=True)
    broken.acquire(_ISSUE, _TOKEN_A)
    # login equality wrongly counts B as an owner and lets B advance A's claim.
    assert broken.active_count(_TOKEN_B) == 1  # the bug #834 forbids
    broken.advance(_ISSUE, _TOKEN_B)  # would raise under correct token ownership

    # The correct token-ownership model refuses that very same advance.
    correct = _HybridClaimLedger(ownership_by_login=False)
    correct.acquire(_ISSUE, _TOKEN_A)
    with pytest.raises(_ClaimBlocked):
        correct.advance(_ISSUE, _TOKEN_B)


# ---------------------------------------------------------------------------
# #868 — merge/version-owner refusal gate (gh-merge Step 0) + §12 policy
# ---------------------------------------------------------------------------
#
# Split the count-checked needles so THIS test file is not itself an occurrence
# (mirrors the marker/heading splits above). The refusal CONDITION is the single
# canonical statement that must live only in gh-merge + its mirror; the old soft
# placeholder that name-dropped #868 must be gone entirely.
_REFUSAL_CONDITION = (
    "create no merge worktree, run no gate, " + "invoke no merge, and edit no version line"
)
_SUPERSEDED_PLACEHOLDER = "does not add the broader " + "ownership-refusal policy"


def test_step0_precedes_prepare_in_gh_merge() -> None:
    # Index-ordering (cf. test_merge_checkpoints_before_and_after_cleanup_mutation):
    # the Step 0 ownership gate must precede *any* other step, incl. Prepare.
    merge = _read(_MERGE)
    step0 = merge.index("## Step 0 — Verify merge ownership")
    prepare = merge.index("## Prepare")
    assert step0 < prepare, "Step 0 must come before Prepare in gh-merge"


def test_refusal_condition_is_canonical_only_in_gh_merge() -> None:
    # Occurrences-count (cf. test_conventions_is_the_only_ledger_schema_definition,
    # reusing _occurrences): the refusal CONDITION is stated exactly once repo-wide,
    # in the gh-merge source, and NOWHERE else (not CONVENTIONS.md §12, not gh-lead).
    found = _occurrences(_REFUSAL_CONDITION)
    assert found == {_MERGE.relative_to(_ROOT): 1}, found
    assert _CONVENTIONS.relative_to(_ROOT) not in found
    assert _LEAD.relative_to(_ROOT) not in found


def test_superseded_ownership_refusal_placeholder_is_gone() -> None:
    # The old soft Non-negotiable that name-dropped #868 as "tracked separately"
    # is removed/rewritten -- the refusal rule is stated exactly once (Step 0),
    # never left as a stale contradiction anywhere in the repo.
    assert _occurrences(_SUPERSEDED_PLACEHOLDER) == {}


def test_conventions_section_12_defines_merge_owner_policy() -> None:
    # §12 exists immediately after §11, names gh-merge as the sole enforcement
    # point, keeps ownership a session token, and does NOT restate the refusal
    # condition or re-declare §11's ledger schema (single-schema invariant).
    text = _read(_CONVENTIONS)
    s11 = text.index("## 11. Sprint-control ledger contract")
    s12 = text.index("## 12. Merge/version-owner claim, transfer, and release")
    assert s11 < s12, "§12 must come immediately after §11"
    section12 = text[s12:]
    lowered = section12.lower()
    assert "gh-merge" in lowered and "step 0" in lowered  # names the enforcement point
    assert "session token" in lowered  # value stays a token, not a gh login (#834)
    assert _REFUSAL_CONDITION not in section12  # policy names, never restates, the condition
    # single ledger schema preserved: §12 does not re-declare §11's field heading.
    assert "### required compact checkpoint fields" not in lowered


def test_lead_cold_boot_acquires_or_confirms_merge_owner() -> None:
    # Behavioral-reference (cf. test_lead_cold_boot_refuses_unsafe_dispatch...):
    # gh-lead's cold-boot section carries the acquire/confirm-PR-only language and
    # references §12, without restating gh-merge's refusal condition.
    lead = _normalized(_LEAD)
    behavioral_references = (
        "acquire the merge/version pen at cold boot",
        "read the checkpoint's merge-owner session identity field",
        "if the merge-owner field is unclaimed the lead claims it in one atomic checkpoint edit",
        "already held by another session the lead confirms that and goes pr-only for merges",
        "never dispatching gh-merge itself",
    )
    for reference in behavioral_references:
        assert reference in lead, f"gh-lead lacks behavioral reference: {reference}"
    assert _REFUSAL_CONDITION not in _read(_LEAD)  # references the policy, not the condition


# --- #868 ungameable negative proof: a non-owner token is REFUSED by Step 0 ----
#
# Executable reference model of gh-merge's Step 0 ownership gate (there is no
# production merge engine -- Step 0 is prose the agent follows against the §11
# merge-owner field). Mirrors the AC-5 hybrid-claim proof above: the CORRECT
# model refuses a non-owner token; the deliberately-BROKEN variant (enforcement
# removed -- the pre-#868 verify-and-surface-but-don't-refuse placeholder) admits
# the non-owner -- exactly the gap #868 closes -- so the negative test genuinely
# depends on the refusal, not on incidental structure.


class _MergeRefused(Exception):
    """Step 0 refused a merge/version bump from a non-owner session (fail-closed)."""


@dataclass
class _MergeOwnershipGate:
    recorded_owner_token: str | None  # §11 merge-owner session identity field
    enforce: bool = True  # False models the pre-#868 soft "surface, don't refuse"

    def step0_merge(self, session_token: str) -> str:
        # Step 0.3 refusal condition: a session whose token is not the recorded
        # owner creates no worktree, runs no gate, invokes no merge, edits no
        # version line. An unclaimed field is never self-appointed mid-merge (§12).
        if self.enforce and session_token != self.recorded_owner_token:
            raise _MergeRefused(
                f"not the recorded merge-owner ({self.recorded_owner_token})"
            )
        if self.recorded_owner_token is None:
            raise _MergeRefused("merge-owner field unclaimed; operator/lead must claim it")
        return "merged"  # only the recorded owner reaches Prepare..Step 8


def test_step0_refuses_non_owner_and_admits_recorded_owner() -> None:
    gate = _MergeOwnershipGate(recorded_owner_token=_TOKEN_A)
    # positive control: the recorded owner proceeds past Step 0.
    assert gate.step0_merge(_TOKEN_A) == "merged"
    # negative proof: a DIFFERENT session token (same shared login) is refused --
    # no merge, no version bump.
    with pytest.raises(_MergeRefused):
        gate.step0_merge(_TOKEN_B)
    # an unclaimed field is not self-appointed into a merge.
    with pytest.raises(_MergeRefused):
        _MergeOwnershipGate(recorded_owner_token=None).step0_merge(_TOKEN_B)


def test_proof_fails_if_step0_refusal_is_removed() -> None:
    # The discriminating half: with enforcement removed (the pre-#868 soft
    # placeholder that only *surfaced* a mismatch), the SAME non-owner token is
    # wrongly admitted -- proving the test above depends on the Step 0 refusal.
    soft = _MergeOwnershipGate(recorded_owner_token=_TOKEN_A, enforce=False)
    assert soft.step0_merge(_TOKEN_B) == "merged"  # the gap #868 closes
    strict = _MergeOwnershipGate(recorded_owner_token=_TOKEN_A, enforce=True)
    with pytest.raises(_MergeRefused):
        strict.step0_merge(_TOKEN_B)


# ---------------------------------------------------------------------------
# #869 — session-to-session handoff-message subsection (extends §11)
# ---------------------------------------------------------------------------
#
# The single-source guard for the handoff heading is folded into
# test_conventions_is_the_only_ledger_schema_definition above (extend, don't fork).
# Here: structural placement + required content, and the adversarial decoy proof.

_HANDOFF_HEADING = (
    "### Session-to-session handoff "
    + "message (extends the writer-ownership transfer)"
)


def test_handoff_subsection_is_nested_in_section_11_with_required_content() -> None:
    # The subsection sits INSIDE §11 (after "Writer ownership", before "REST-first",
    # ahead of §12) and carries the four normative pieces plus the courtesy-nudge rule.
    text = _read(_CONVENTIONS)
    s11 = text.index("## 11. Sprint-control ledger contract")
    s12 = text.index("## 12. Merge/version-owner claim, transfer, and release")
    writer = text.index("### Writer ownership and update cadence")
    handoff = text.index(_HANDOFF_HEADING)
    restfirst = text.index("### REST-first discovery, reconciliation, and atomic edits")
    assert s11 < writer < handoff < restfirst < s12

    section = " ".join(text[handoff:restfirst].lower().split())
    required = (
        "successor identity",  # names the incoming writer
        "same session identity/token convention",  # reuse, not a second scheme
        "handoff trigger/reason",  # why ownership moved
        "freshly reconciled against durable evidence as of the handoff edit",
        "named is necessary, never sufficient",  # the fail-loud headline
        (
            "any mismatch between the inherited checkpoint's claims and that "
            "independent reconciliation stops the successor"
        ),
        "the session-messaging tool is a courtesy nudge, never authority",
    )
    for needle in required:
        assert needle in section, f"§11 handoff subsection lacks: {needle}"


def test_lead_references_handoff_message_and_fail_loud_on_mismatch() -> None:
    # gh-lead REFERENCES the new §11 subsection (never restates it) and carries the
    # named!=sufficient / refuse-on-mismatch / messaging-non-authoritative behavior.
    lead = _normalized(_LEAD)
    behavioral_references = (
        "session-to-session handoff message",
        "a named-successor role owes the same refuse-on-mismatch behavior",
        "being named successor is necessary but never sufficient",
        (
            "the session-messaging tool may carry a low-latency pointer to the "
            "successor, but it is never authoritative"
        ),
    )
    for reference in behavioral_references:
        assert reference in lead, f"gh-lead lacks behavioral reference: {reference}"


# --- #869 adversarial decoy: a correctly-named successor STILL stops on mismatch --
#
# Executable reference model of the §11 fail-loud handoff rule (there is no
# production handoff engine -- the rule is prose the agent follows). Mirrors the
# #834/#868 proofs: the CORRECT model reconciles the inherited checkpoint against
# durable evidence before the first write and refuses on any mismatch even when the
# successor is correctly named; the deliberately-BROKEN variant treats "I was named"
# as sufficient and skips verification -- exactly the loophole #869 closes.


class _HandoffRefused(Exception):
    """The named successor refused: inherited checkpoint disagrees with durable evidence."""


@dataclass(frozen=True)
class _CheckpointState:
    named_successor: str
    merge_queue: tuple[int, ...]
    gate_state: str
    app_version: str


@dataclass
class _SuccessorFirstWrite:
    # False models the loophole: "I was named successor, so I can skip verification".
    reconcile_before_first_write: bool = True

    def first_write(
        self,
        my_token: str,
        inherited: _CheckpointState,
        durable: _CheckpointState,
    ) -> str:
        # Named-successor check is NECESSARY...
        if my_token != inherited.named_successor:
            raise _HandoffRefused("this session is not the named successor")
        # ...but NEVER sufficient: independently reconcile inherited claims vs the
        # durable board/PR/issue/version evidence, and stop on any mismatch.
        if self.reconcile_before_first_write:
            mismatch = (
                inherited.merge_queue != durable.merge_queue
                or inherited.gate_state != durable.gate_state
                or inherited.app_version != durable.app_version
            )
            if mismatch:
                raise _HandoffRefused(
                    "inherited checkpoint disagrees with durable evidence"
                )
        return "proceed"


_DURABLE = _CheckpointState("sess-C-0003", (901, 902), "green", "1.0.183")
# Syntactically valid inherited checkpoint: successor CORRECTLY named, but its
# merge-queue/gate/version fields deliberately disagree with the durable state.
_INHERITED_MISMATCH = _CheckpointState("sess-C-0003", (999,), "red", "1.0.181")


def test_named_successor_still_stops_on_evidence_mismatch() -> None:
    successor = _SuccessorFirstWrite()  # correct: reconcile before first write

    # positive control: named party + matching evidence -> proceeds.
    assert successor.first_write("sess-C-0003", _DURABLE, _DURABLE) == "proceed"
    # the point of #869: named party but MISMATCHED inherited fields -> STOP.
    with pytest.raises(_HandoffRefused):
        successor.first_write("sess-C-0003", _INHERITED_MISMATCH, _DURABLE)
    # not the named party -> refused regardless.
    with pytest.raises(_HandoffRefused):
        successor.first_write("sess-Z-9999", _DURABLE, _DURABLE)


def test_proof_fails_if_named_successor_skips_verification() -> None:
    # Discriminating half: the loophole #869 closes -- treating "I was named" as
    # SUFFICIENT (skip reconciliation) wrongly admits the mismatched handoff.
    loophole = _SuccessorFirstWrite(reconcile_before_first_write=False)
    assert (
        loophole.first_write("sess-C-0003", _INHERITED_MISMATCH, _DURABLE) == "proceed"
    )  # the bug
    correct = _SuccessorFirstWrite(reconcile_before_first_write=True)
    with pytest.raises(_HandoffRefused):
        correct.first_write("sess-C-0003", _INHERITED_MISMATCH, _DURABLE)


# ---------------------------------------------------------------------------
# #870 — sprint-size cap (§7 Runaway guards) + gh-lead trigger
# ---------------------------------------------------------------------------

# Split (en-dash via –) so THIS file is not itself an occurrence of the figure.
_SPRINT_CAP_FIGURE = "~8" + "–10 tickets"


def test_sprint_size_cap_figure_is_canonical_only_in_conventions() -> None:
    # #870 AC: the cap number is ONE canonical statement in CONVENTIONS.md §7;
    # gh-lead + its mirror reference §7, never restate the figure (same property
    # test_conventions_is_the_only_ledger_schema_definition enforces for the marker).
    assert _occurrences(_SPRINT_CAP_FIGURE) == {_CONVENTIONS.relative_to(_ROOT): 1}


def test_sprint_size_cap_bullet_lives_in_section_7_runaway_guards() -> None:
    text = _read(_CONVENTIONS)
    guards = text.index("### Runaway guards")
    hybrid = text.index("### Hybrid claim protocol")
    cap = text.index(_SPRINT_CAP_FIGURE)
    assert guards < cap < hybrid  # the cap bullet sits inside §7 Runaway guards

    bullet = " ".join(text[guards:hybrid].lower().split())
    required = (
        "soft",
        "per lead session",
        "likely-multi-cycle",
        "15 prs in one session",  # Sprint-3-session-2 (2026-07-04) citation
        "split into waves planned as separate sessions at planning time",
        "operator override",
        "guides, it does not block",
    )
    for needle in required:
        assert needle in bullet, f"§7 sprint-cap bullet lacks: {needle}"


def test_lead_applies_sprint_cap_and_plans_context_pressure_handoff() -> None:
    # gh-lead references §7 for the cap (never restates the figure) and states the
    # mid-sprint planned-handoff rule as BEHAVIOR: trigger -> checkpoint -> merge-lock
    # release/transfer (§12) -> successor cold-boot instruction.
    assert _SPRINT_CAP_FIGURE not in _read(_LEAD)  # references §7, never restates it
    lead = _normalized(_LEAD)
    behavioral_references = (
        "apply the §7 sprint-size cap",
        "size the sprint to one lead session with margin",
        "split an over-cap sprint into waves planned as separate sessions at planning time",
        "when the lead notices context pressure",
        "handoff at the next merge boundary",
        "write the §11 sprint checkpoint, freshly reconciled",
        "release or transfer the merge/version pen per",
        "instruct the successor to cold-boot from the sprint control issue",
    )
    for reference in behavioral_references:
        assert reference in lead, f"gh-lead lacks behavioral reference: {reference}"


# ---------------------------------------------------------------------------
# #996 [minor] — guard the gh-merge Step 0 worked-example heading
# ---------------------------------------------------------------------------


def test_gh_merge_step0_worked_example_heading_present() -> None:
    # A future edit must not silently delete the Step 0 merge-ownership worked
    # example (its refusal + positive-case demo). Present in source and mirror.
    heading = "## Worked example — Step 0 merge-ownership refusal"
    assert heading in _read(_MERGE)