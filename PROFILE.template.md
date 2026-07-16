# GH Workflow Project Profile — TEMPLATE

> Copy this file into the target repository as `agents/gh-workflow/PROFILE.md`
> and replace every `FILL-ME`. Value shapes (ids, commands, paths) follow the
> comments in each section.

**THE per-project instance data for the gh-* pipeline.** The skills
(`agents/gh-*/SKILL.md`) and the process authority
(`agents/gh-workflow/CONVENTIONS.md`) are **project-agnostic**: wherever they
say a `<key-name>` placeholder, the value lives here and only here. Porting the
pipeline to another repository means writing a new PROFILE.md — no skill or
conventions edit. When the skills are installed outside a repo (user-level
deploy), resolve this file inside the **target repository being operated on**
at `agents/gh-workflow/PROFILE.md`; if it is missing, stop and ask the operator
to create it — never guess instance values.

## Identity

| Key | Value |
|---|---|
| `<repo>` | `**FILL-ME**` |
| `<automation-login>` | **FILL-ME** — the one shared GitHub login every lead/worker/sweeper session authenticates as (why ownership is session-token-based; CONVENTIONS.md §7/§12) |
| `<codex-reviewer>` | **FILL-ME** — the async automated PR reviewer; addressed if it posts, but **NOT a required gate** (de-gated 2026-07-15, CONVENTIONS.md §8). All review-gate requirements are on the Claude review routine; this value only lets a skill RECOGNIZE a Codex review so its findings can be addressed when present. |

## Board (Projects v2)

| Key | Value |
|---|---|
| `<board-name>` | **FILL-ME** |
| `<board-owner>` | **FILL-ME** |
| `<board-number>` | **FILL-ME** |
| `<board-url>` | **FILL-ME** |
| `<project-node-id>` | **FILL-ME** |
| `<status-field-id>` | **FILL-ME** (single-select Status) |

### Status option IDs (`<option-id:…>`)

| Status | Option ID |
|---|---|
| Needs Refinement | **FILL-ME** |
| Backlog | **FILL-ME** |
| Open | **FILL-ME** |
| In Progress | **FILL-ME** |
| Awaiting Review | **FILL-ME** |
| Reviewed | **FILL-ME** |
| Awaiting Validation | **FILL-ME** |
| In Validation | **FILL-ME** |
| Validated | **FILL-ME** |

## Checkouts, worktrees, branches

| Key | Value |
|---|---|
| `<operator-main-checkout>` | **FILL-ME** — the operator's primary working copy; **never** mutated, cleaned, or branch-switched by any pipeline session |
| `<worktree-root>` | **FILL-ME** — pipeline worker worktrees live at `<worktree-root>/<repo-name>-<issue>` (e.g. `C:/tmp/<repo-name>-123`) |
| `<work-branch-convention>` | `codex/<issue>-<slug>` |
| `<merge-worktree-convention>` | `gh-merge-<session>` (scratch worktree + branch, no PR) |

## Version

| Key | Value |
|---|---|
| `<version-file>` | **FILL-ME** |
| `<version-read-command>` | **FILL-ME** |
| `<bump-paths>` | **FILL-ME** — directories whose merged changes trigger the patch bump at merge (CONVENTIONS.md §9), e.g. `/src`, `/tests` |

## Gates (commands run verbatim from the repo root / merge worktree)

| Key | Value |
|---|---|
| `<fast-gates>` | **FILL-ME** — the cheap always-runnable checks (types, lint, size, artifacts) |
| `<full-suite>` | **FILL-ME** |
| `<artifacts-gate>` | **FILL-ME** |
| `<contribution-standard>` | **FILL-ME** — the repo contribution/reuse standard reviewers apply |

## Merge planning (gh-merge Step 2 inputs)

- `<hot-files>` — **FILL-ME**: known repeat-offender files where any shared
  touch between two PRs is a hard serialize signal (always include
  `<version-file>`).
- `<serialize-rules>` — **FILL-ME**: project-specific always-serialize rules
  (e.g. "any PR that regenerates snapshot X conflicts with any other such PR —
  at most one in flight").

## Validation notes (gh-validate project specifics)

- `<project-cli>` — **FILL-ME** (the module/command gh-validate drives, plus the
  venv it runs under; note any PYTHONPATH the worktree needs so validation
  doesn't silently test the main checkout's code).
- `<project-mcp-server>` — **FILL-ME** (if the project ships an MCP server).
  Note whether it is MAIN-ROOTED (resolves its project root from its own
  process/env, so servers it launches run against the main checkout — never use
  such tools to validate a PR worktree) and which env var re-roots it.
- Note any gitignored credential files (e.g. `.env`) that must be copied into a
  worktree for the app to run; `git clean` there destroys them (gh-clean
  non-negotiable #2).
