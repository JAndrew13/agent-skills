# agent-skills

The **gh-\* dev-workflow pipeline**: nine project-agnostic Claude agent skills
plus their process authority doc, extracted from the repo they were built in so
they can be installed at the Claude application level and drive any repository.

## The pipeline

| Skill | Stage | Session shape |
|---|---|---|
| [gh-lead](agents/gh-lead/SKILL.md) | Sprint orchestrator — triage, wave planning, dispatch | resident session |
| [gh-create-issue](agents/gh-create-issue/SKILL.md) | Author tickets at the quality bar | inline sub-skill |
| [gh-refine](agents/gh-refine/SKILL.md) | Validate premises, score, harden ACs | spawned, no worktree |
| [gh-resolve](agents/gh-resolve/SKILL.md) | Implement → open PR | spawned, own worktree |
| [gh-review](agents/gh-review/SKILL.md) | Adversarial review, advisory only | spawned, read-only git |
| [gh-fixer](agents/gh-fixer/SKILL.md) | Address every review thread | spawned, own worktree |
| [gh-validate](agents/gh-validate/SKILL.md) | Behavioral pre-merge validation | spawned, isolated worktree |
| [gh-merge](agents/gh-merge/SKILL.md) | The ONLY merger — gates, squash, version bump | spawned, merge worktree |
| [gh-clean](agents/gh-clean/SKILL.md) | Tear down pipeline debris, safely | inline within gh-merge |

**[agents/gh-workflow/CONVENTIONS.md](agents/gh-workflow/CONVENTIONS.md)** is the
single source for the taxonomy, board Status model, state machine, human gates,
review gate (Codex-independent — the Claude review stage is the required gate; Codex
is addressed if present but never required), and version/testing-cadence policy.
Skills reference its sections and never restate them; each skill's **Conventions
scope** line declares exactly which §§ it loads (nothing loads the whole doc except
gh-lead).

## The profile contract (per-project instance data)

The skills and CONVENTIONS.md contain **no project-specific values**. Every
`<key-name>` placeholder (repo slug, board/project node IDs, status option IDs,
gate commands, version file, checkout paths, hot files) resolves to a
**PROFILE.md inside the target repository** at `agents/gh-workflow/PROFILE.md`.

- Onboarding a repo = copy [PROFILE.template.md](PROFILE.template.md) into the
  target repo as `agents/gh-workflow/PROFILE.md` and fill in its values.
- If a target repo has no PROFILE.md, skills stop and ask the operator — they
  never guess instance values.

## Cloud routines (optional event-triggered stages)

Three stages can also run as Claude cloud routines triggered by GitHub events,
taking them off the interactive session's critical path:

- **gh-review** — Pull request: Opened / Ready for review / Commits pushed
- **gh-clean** — Pull request: Closed (remote-branch scope only)
- **gh-refine** — Issue: Opened

Each skill carries a **Routine trigger** note with its idempotency/skip guards,
and gh-lead checks durable evidence before dispatching a stage a routine may
already have run.

Routines bind to ONE repository, so **each onboarded repo gets its own set of
three routines** — but the prompts are repo-agnostic bootstrap shims (they
fetch skill text from this repo and read PROFILE.md from the triggering repo's
clone), so the canonical prompt texts in [routines/](routines/) are pasted
unchanged into every repo's routines. Behavior changes land in the SKILL.md
files here and propagate to all attached repos without touching any routine.

## Installing

Deploy the `agents/<name>/` folders to your Claude application skills directory
(e.g. `~/.claude/skills/<name>/`), keeping `gh-workflow/CONVENTIONS.md` deployed
alongside them so the skills' relative references resolve. Repos with their own
installer (e.g. a `claude install` command that recursively copies
`agents/<name>/`) can consume this repo as the source tree directly.

## Guard tests

`tests/` carries the structural contract tests that keep the pipeline's
invariants intact — the #800 board-economy contract (injected item-ids, gated
`item-list` fallback), the #834/#868/#869/#870 sprint-ledger + merge-ownership
contracts, the #927 version-bump churn guard, and the conventions-scope /
session-shape honesty guard. Run them with:

```sh
python -m pytest tests/ -q
```
