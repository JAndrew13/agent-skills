# Routine: gh-clean

**Trigger:** Pull request: Closed.
**Attach to:** the target repository (routines bind to one repo; paste this
prompt unchanged into each repo's routine — PROFILE.md carries the per-repo
values).

---

A pull request in this repository was just closed. Run the pipeline's cleanup
stage in its routine variant: you have a fresh cloud clone only, so the
local-worktree teardown steps of the skill DO NOT APPLY — never attempt to
manage worktrees or files on the operator's machine.

Your instructions live OUTSIDE this repository. Fetch from
https://github.com/JAndrew13/agent-skills (raw main branch):
- agents/gh-clean/SKILL.md — adopt its posture and its "Routine trigger" scope:
  conservative by default; anything ambiguous is reported, never deleted. It
  needs no CONVENTIONS.md sections.
Read the per-project instance values from THIS repo's clone:
agents/gh-workflow/PROFILE.md (branch conventions, artifacts-gate command). If
PROFILE.md is missing, stop and report.

1. Confirm the triggering PR's final state: merged, or closed without merge.
2. If MERGED: delete its remote head branch if it still exists (the merger
   usually auto-deletes — a no-op is success, not an error). Before deleting,
   confirm no other open PR uses that branch as head or base.
3. If CLOSED WITHOUT MERGE: leave the branch in place and report it — it may
   hold recoverable work.
4. Never delete: the default branch, any branch with an open PR, or any branch
   that doesn't match the profile's <work-branch-convention>. Never force (-D)
   past a refusal.
5. Run the profile's <artifacts-gate> command — it must exit clean. If it
   reports a tracked artifact, report the violation; do not delete anything to
   silence it.
6. Post a short summary comment on the PR: what was removed, what was left in
   place and why, and the artifacts-gate result. Take no other action — no
   board edits, no issue closing, no code changes (those belong to gh-merge).
