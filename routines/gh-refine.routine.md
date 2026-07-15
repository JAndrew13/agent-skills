# Routine: gh-refine

**Trigger:** Issue: Opened.
**Attach to:** the target repository (routines bind to one repo; paste this
prompt unchanged into each repo's routine — PROFILE.md carries the per-repo
values).

---

An issue was just opened in this repository. Act as the dev-workflow pipeline's
refinement stage for exactly this one issue.

Skip guards (check FIRST, exit without acting if any apply):
- the issue body already contains a "## Refinement" block;
- the title starts with [CHILD] (pipeline-authored children are refined by
  their epic's conversion);
- the issue carries the Ignore! label, or is already closed.

Your instructions live OUTSIDE this repository. Fetch from
https://github.com/JAndrew13/agent-skills (raw main branch):
- agents/gh-refine/SKILL.md — the refinement contract; follow it, including its
  Session shape, Conventions scope, and Routine trigger lines.
- agents/gh-workflow/CONVENTIONS.md — load ONLY the sections the skill's
  Conventions scope declares (§§1–10).
Then read the per-project instance values from THIS repo's clone:
agents/gh-workflow/PROFILE.md (board ids, status option ids). If PROFILE.md is
missing, stop and report.

Then, per the skill:
1. Validate the ticket's premises against the current code in this clone before
   scoring — course-correct stale assumptions in the body.
2. Write the ## Refinement block (Complexity, Blast Radius, blast-radius file
   list, rationale grounded in the code you actually read).
3. HUMAN GATE: if Complexity is Hard/Very Hard or Blast Radius is Large/Huge,
   the ticket qualifies for epic conversion — propose the conversion in an
   issue comment (suggested children, sequencing) and STOP. Never create the
   epic or children without operator sign-off (CONVENTIONS.md §7 gate (a)).
   Any Unsafe! label: stop and surface, always (gate (c)).
4. Otherwise set the board Status via gh project item-edit using the PROFILE.md
   ids: workable now → Open; deliberately future/iced → Backlog; premises
   unresolvably stale → hold at Needs Refinement and say why in a comment. No
   injected item-id exists in a routine invocation, so resolve the board item
   id yourself via the skill's documented item-list fallback.
5. Never dispatch, never implement, never edit code. Refinement ends at the
   status write plus your comment.
