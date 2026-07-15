"""Structural contract test for gh-merge's version-bump churn guard (#927).

Encodes the PR #920 incident defense directly against ``agents/gh-merge/SKILL.md``:
the Step 6 version-bump commit must (a) discard full-suite working-tree churn, (b)
stage ONLY ``pyproject.toml``, and (c) verify a one-file commit before pushing — and
the copy-pastable "Worked example — DRY RUN" must not model the ``git commit -am``
command that swept 14 churned fixtures into ``2e44cb75`` (forward-fixed by
``d6e5732c``).

Follows the same read-from-disk structural-contract pattern as
``tests/test_sprint_ledger_contract.py`` and runs as a normal, unmarked part of
``pytest -q`` (no opt-in/skip marker) so it is part of the default gate, not an
inert proxy.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MERGE = _ROOT / "agents" / "gh-merge" / "SKILL.md"

# The incident command, split so THIS test file is not itself an occurrence of the
# substring it forbids (the marker-splitting technique used across the ledger tests).
_FORBIDDEN = "commit" + " -am"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _step6_section(text: str) -> str:
    start = text.index("## Step 6 — Version bump at merge")
    end = text.index("## Step 7")
    return text[start:end]


def _dry_run_example(text: str) -> str:
    start = text.index("## Worked example — DRY RUN")
    end = text.index("## Worked example — Step 0")
    return text[start:end]


def test_no_commit_dash_am_anywhere_in_gh_merge_source_and_mirror() -> None:
    # AC #2 (adversarial): the literal `commit -am` -- the exact PR #920 command --
    # occurs ZERO times in gh-merge. This FAILS on pre-#927 main (2 occurrences, both
    # DRY-RUN bump sites) and passes only once both sites are fixed.
    assert _read(_MERGE).count(_FORBIDDEN) == 0


def test_step6_states_discard_then_scoped_stage_then_single_file_verify() -> None:
    # AC #1: Step 6 states the three-part guard explicitly.
    step6 = _step6_section(_read(_MERGE))
    lowered = " ".join(step6.lower().split())

    # (a) discard working-tree churn AFTER the full suite, BEFORE the bump edit:
    assert "git reset --hard" in step6
    assert "after the step 5 full-suite gate and before the bump edit" in lowered
    # never `git clean` (the .env-wipe hazard the guard must not reintroduce):
    assert "never `git clean`" in lowered
    # (b) stage ONLY the version file with `git commit -m` (never the -a/--all blanket):
    assert "git add <version-file> && git commit -m" in step6
    # (c) verify the commit is exactly one file before pushing:
    assert "git show --stat HEAD" in step6
    assert "exactly one file before pushing" in lowered


def test_step6_guard_is_ordered_discard_stage_verify() -> None:
    # The three steps must appear in sequence (cf. the index-ordering guards in
    # test_sprint_ledger_contract.py): discard -> scoped stage -> single-file verify.
    step6 = _step6_section(_read(_MERGE))
    discard = step6.index("git reset --hard")
    stage = step6.index("git add <version-file> && git commit -m")
    verify = step6.index("git show --stat HEAD")
    assert discard < stage < verify


def test_worked_example_models_the_guard_not_the_incident() -> None:
    # AC #2: the copy-pastable DRY-RUN command list uses the guard sequence at BOTH
    # bump sites (discard -> scoped stage -> verify) and never the `-am` incident cmd.
    example = _dry_run_example(_read(_MERGE))
    assert _FORBIDDEN not in example
    assert example.count("git reset --hard") == 2
    assert example.count("git add <version-file> && git commit -m") == 2
    assert example.count("git show --stat HEAD") == 2

