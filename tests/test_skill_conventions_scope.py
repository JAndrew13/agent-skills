"""Structural contract test for the conventions read-scope + session-shape sweep.

The gh-lead sprint skill-load audit (2026-07-15) measured a 9-ticket sprint spawning
~60 agent sessions that each re-read the whole 705-line CONVENTIONS.md while citing
29-89% of it — roughly 400k tokens/sprint of never-cited sections, concentrated in
the review/fix loop. The fix follows the audit's own alternative (and the §3
board-economy resolve-once shape, applied to instructions instead of GraphQL):
every gh-* skill declares a **Conventions scope** line naming the §§ it needs, and
an executing agent loads only those sections. A **Session shape** line pins each
stage's spawn primitive (resident / spawned / inline), closing the audit's "no
SKILL.md states how it runs" finding so a sprint's session count is predictable.

A physical split of CONVENTIONS.md was deliberately NOT done: the #800 board-economy
contract test and the #834/#870 sprint-ledger contract tests pin canonical headings
and figures to agents/gh-workflow/CONVENTIONS.md exactly once at that exact path.
Scoped reads deliver the same token outcome without touching those guards.

This test proves the sweep structurally (the
``tests/test_board_item_id_propagation_contract.py`` precedent):

* every gh-* skill carries exactly one Session shape line and exactly one
  Conventions scope line, placed before its Overview;
* each declared scope is honest — every §N the skill's own body cites is inside the
  scope it tells its agent to read (a citation outside the declared scope means the
  agent would follow a reference into a section it never loaded);
* CONVENTIONS.md itself states the read-scope rule, so the per-skill declaration is
  load-bearing from the document's side too.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS = _ROOT / "agents"
_CONVENTIONS = _AGENTS / "gh-workflow" / "CONVENTIONS.md"

_ALL_SECTIONS = frozenset(range(1, 13))

# Every skill in the dev-workflow pipeline that fronts CONVENTIONS.md.
_PIPELINE_SKILLS = (
    "gh-lead",
    "gh-refine",
    "gh-resolve",
    "gh-review",
    "gh-fixer",
    "gh-validate",
    "gh-merge",
    "gh-clean",
    "gh-create-issue",
)

_SESSION_SHAPE_MARKER = "**Session shape:**"
_SCOPE_MARKER = "**Conventions scope:**"


def _read(name: str) -> str:
    return (_AGENTS / name / "SKILL.md").read_text(encoding="utf-8", errors="replace")


def _scope_paragraph(text: str, name: str) -> str:
    start = text.index(_SCOPE_MARKER)
    end = text.find("\n\n", start)
    assert end != -1, f"{name}: Conventions scope paragraph is unterminated"
    return text[start:end]


def _declared_sections(paragraph: str, name: str) -> frozenset[int]:
    if "whole document" in paragraph:
        return _ALL_SECTIONS
    if "none" in paragraph.split("§")[0]:
        return frozenset()
    run = re.search(r"§§([\d,\s]+)", paragraph)
    assert run is not None, f"{name}: cannot parse the declared §§ list"
    declared = frozenset(int(n) for n in re.findall(r"\d+", run.group(1)))
    assert declared, f"{name}: declared scope is empty but not marked 'none'"
    assert declared <= _ALL_SECTIONS, f"{name}: declares a nonexistent section"
    return declared


def test_every_pipeline_skill_declares_shape_and_scope_once() -> None:
    for name in _PIPELINE_SKILLS:
        text = _read(name)
        assert text.count(_SESSION_SHAPE_MARKER) == 1, (
            f"{name}: expected exactly one '{_SESSION_SHAPE_MARKER}' line"
        )
        assert text.count(_SCOPE_MARKER) == 1, (
            f"{name}: expected exactly one '{_SCOPE_MARKER}' line"
        )
        overview = text.index("## Overview")
        assert text.index(_SESSION_SHAPE_MARKER) < overview, (
            f"{name}: Session shape must precede the Overview"
        )
        assert text.index(_SCOPE_MARKER) < overview, (
            f"{name}: Conventions scope must precede the Overview"
        )


def test_declared_scope_covers_every_section_the_skill_cites() -> None:
    # Honesty check: a skill's body may only cite §§ inside its declared scope —
    # otherwise the executing agent is sent into a section it was told not to load.
    for name in _PIPELINE_SKILLS:
        text = _read(name)
        paragraph = _scope_paragraph(text, name)
        declared = _declared_sections(paragraph, name)
        body = text.replace(paragraph, "")
        cited = frozenset(int(n) for n in re.findall(r"§(\d+)", body))
        assert cited <= _ALL_SECTIONS, f"{name}: cites a nonexistent section"
        undeclared = cited - declared
        assert not undeclared, (
            f"{name}: body cites §§{sorted(undeclared)} outside its declared scope "
            f"{sorted(declared) if declared else 'none'} — widen the Conventions "
            f"scope line or drop the citation"
        )


def test_conventions_states_the_read_scope_rule() -> None:
    text = _CONVENTIONS.read_text(encoding="utf-8", errors="replace")
    assert "**Read scope:**" in text, (
        "CONVENTIONS.md must state the per-skill read-scope rule so the skill "
        "declarations are load-bearing from the document's side"
    )
