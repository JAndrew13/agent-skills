"""Structural contract test for the #800 board-economy / injected-item-id sweep.

CONVENTIONS.md §3 defines the *board-economy contract*: a dispatcher resolves the
Projects v2 board item map ONCE per run and injects each ticket's item-id into the
single-ticket child skills it dispatches; a child uses the injected id directly for
its one ``gh project item-edit`` Status write and falls back to ``gh project
item-list`` ONLY when no id was injected -- never re-fetching the full board map
under sprint concurrency, which drained the GraphQL budget in the Sprint-3 pilot.

This test proves the contract STRUCTURALLY, following the
``tests/test_sprint_ledger_contract.py`` precedent (there is no executable board
client for these prose skills -- the protocol is text the agent follows, so a
live "N-concurrent-dispatch drains less GraphQL" check is not reproducible offline;
AC #5). It asserts:

* the contract heading lives in CONVENTIONS.md exactly once and is never re-inlined
  into a skill (the DW-11 grep-AC discipline that keeps CONVENTIONS the single home);
* each of the five single-ticket worker skills (gh-refine / gh-resolve / gh-review /
  gh-fixer / gh-validate) carries the injected-id branch AND a *visibly gated*
  ``item-list`` fallback -- the gate phrase must immediately precede the full-board
  call, so an unconditional call fails. This catches the gameable move of adding an
  unrelated "we support injected ids" sentence while leaving ``item-list`` uncalled;
* gh-lead threads the Phase-1-resolved id into its Phase 3 (gh-resolve) and Phase 4
  (gh-review / gh-fixer / gh-validate) dispatches;
* gh-merge is deliberately EXCLUDED -- it keeps its unconditional full-board
  ``Validated``-set scan and takes no injected id, so the carve-out is enforced.

Every positive assertion below is ABSENT on pre-#800 ``main`` (no skill mentioned an
injected id; every worker called ``item-list`` unconditionally), so this test fails
on ``main`` and passes only once the sweep lands -- the negative-first proof the
quality bar requires.
"""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS = _ROOT / "agents"
_CONVENTIONS = _AGENTS / "gh-workflow" / "CONVENTIONS.md"
_LEAD = _AGENTS / "gh-lead" / "SKILL.md"
_MERGE = _AGENTS / "gh-merge" / "SKILL.md"

# The five single-ticket worker skills the board-economy contract sweeps.
_WORKER_SKILLS = {
    name: _AGENTS / name / "SKILL.md"
    for name in ("gh-refine", "gh-resolve", "gh-review", "gh-fixer", "gh-validate")
}

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

# Canonical contract phrases. The repo-wide-counted heading is split so THIS file is
# not itself a false occurrence (mirrors the sprint-ledger test's marker split). The
# rest are per-file ``in`` checks, so a literal here is harmless.
_CONTRACT_HEADING = (
    "### Board-economy contract " + "(dispatcher resolves the board item map once)"
)
_INJECTED_BRANCH = "use the board item-id the dispatcher injected"
_FALLBACK_GATE = "only if no item-id was injected"
_FULL_BOARD_CALL = (
    "gh project item-list <board-number> --owner <board-owner> --limit 300 --format json"
)
# The gate phrase must sit immediately before the gated full-board call; an
# unconditional call has no gate within this window and fails.
_MAX_GATE_TO_CALL = 300


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).lower().split())


def _all_occurrences(haystack: str, needle: str) -> list[int]:
    """Start offsets of EVERY occurrence of ``needle`` in ``haystack`` (left to right)."""
    starts: list[int] = []
    start = haystack.find(needle)
    while start != -1:
        starts.append(start)
        start = haystack.find(needle, start + 1)
    return starts


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


def test_board_economy_contract_defined_once_in_conventions() -> None:
    # AC #1: the contract heading lives in CONVENTIONS.md exactly once and is NOT
    # re-inlined into any skill/mirror (the duplication debt CONVENTIONS prevents).
    assert _occurrences(_CONTRACT_HEADING) == {_CONVENTIONS.relative_to(_ROOT): 1}


def test_conventions_states_budget_concurrency_and_exclusions() -> None:
    # The §3 subsection carries the GraphQL-budget + ~28-way concurrency note and the
    # explicit gh-merge / lead-Phase-1 full-board-scan carve-out (AC #1).
    section = _normalized(_CONVENTIONS)
    for needle in (
        "5000 points/hour",
        "~28-way",
        "excluded",
        "gh-merge",
        "phase-1 board read",
    ):
        assert needle in section, f"§3 board-economy subsection lacks: {needle}"


def test_each_worker_skill_has_conditioned_injected_id_branch() -> None:
    # AC #2: every single-ticket worker skill uses the injected id AND gates its
    # item-list fallback. The gate phrase must immediately precede the full-board
    # call -- an unconditional call has no gate before it and fails, catching the
    # gameable "unrelated sentence, unconditional call" move.
    #
    # Scan EVERY occurrence, not just the first: a skill that keeps its first
    # full-board call properly gated but appends a SECOND, unconditional
    # ``item-list`` call later must still fail. Each occurrence needs its own
    # fallback-gate phrase within the preceding window.
    for name, path in _WORKER_SKILLS.items():
        text = _normalized(path)
        assert _INJECTED_BRANCH in text, f"{name}: missing injected-id branch"
        assert _FALLBACK_GATE in text, f"{name}: missing item-list fallback gate"
        assert _FULL_BOARD_CALL in text, f"{name}: missing full-board fallback call"
        gate_positions = _all_occurrences(text, _FALLBACK_GATE)
        call_positions = _all_occurrences(text, _FULL_BOARD_CALL)
        for call in call_positions:
            gated = any(
                gate < call and call - gate <= _MAX_GATE_TO_CALL
                for gate in gate_positions
            )
            assert gated, (
                f"{name}: the item-list call at offset {call} is not visibly gated "
                f"by an injected-id fallback condition (every full-board call must be "
                f"preceded by the '{_FALLBACK_GATE}' gate within {_MAX_GATE_TO_CALL} chars)"
            )


def test_gh_lead_threads_resolved_id_into_dispatches() -> None:
    # AC #3: the dispatcher side actually threads the Phase-1-resolved id into ALL
    # three dispatch phases -- Phase 2 (gh-refine), Phase 3 (gh-resolve), and Phase 4
    # (gh-review / gh-fixer / gh-validate). The Phase-2 needle guards the #800 incident
    # path itself (the refine stage fanning out ~28-way) so gh-refine's injected-id
    # branch always has a production caller and cannot regress to the fallback.
    lead = _normalized(_LEAD)
    for needle in (
        "board-economy contract",
        "thread the phase-1-resolved board item-id into each gh-refine dispatch",
        "thread the phase-1-resolved board item-id into the gh-resolve dispatch prompt",
        (
            "pass each pr's already-resolved item-id into every stage dispatch "
            "(gh-review, gh-fixer, and gh-validate)"
        ),
    ):
        assert needle in lead, f"gh-lead lacks board-economy threading: {needle}"


def test_gh_merge_is_excluded_and_keeps_unconditional_board_scan() -> None:
    # AC #2 (exclusion half): gh-merge is NOT swept -- it takes no injected id and
    # keeps its once-per-merge full-board Validated-set scan (a freshness scan, a
    # different correct case). Enforced here, not just asserted in prose.
    merge = _normalized(_MERGE)
    assert _INJECTED_BRANCH not in merge, "gh-merge must not carry the injected-id branch"
    assert _FALLBACK_GATE not in merge, "gh-merge must not carry the injected-id fallback"
    assert "item-list" in merge, "gh-merge must keep its full-board Validated-set scan"
