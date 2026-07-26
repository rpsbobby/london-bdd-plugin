---
name: inner
description: Run one full inner-loop cycle for the next collaborator — failing unit test, minimum implementation (implementer backend — Haiku agent by default, or an external model via implementer.backend), review and refactor (reviewer agent, Sonnet), one commit on feature/<slice>-tmp. Repeat until the collaborator queue is empty. Paced by session.yml's autonomy field — assisted (default) pauses at each step with the user; autonomous drives the whole queue unattended except for its escalation triggers.
---

# /inner — One Cycle: Red → Green → Refactor → Commit

The orchestrator. Read the `london-bdd` skill first.

## Preconditions — verify ALL before starting

1. `.bdd/session.yml` exists, `phase: inner`, collaborator queue non-empty.
2. **Branch check:** `git branch --show-current` equals session `branch`
   (a `feature/*-tmp`).
   - On the slice's feature/<slice>-main → offer: "Inner loop runs on
     feature/<slice>-tmp only. Create/checkout `<branch>` from here? [y/n]".
     Never proceed on feature/<slice>-main.
   - Anywhere else / detached / dirty → STOP, explain, let the human fix.
     Never auto-stash, never auto-commit rescue work.
3. Outer net intact: AT red-for-the-right-reason (greenfield) or
   characterisation green (SAFE/FULL_REFACTOR).

## The cycle

Read `autonomy` from session.yml first (absent = `assisted`).

### 1 — RED (main session)
Follow `/unit` for the head-of-queue collaborator — `assisted`: with the
user, as `/unit` describes. `autonomous`: unattended, per `/unit`'s
autonomous branch. Either way it ends with `current_failing_test` set
and `🔴 UT` announced.

### 2 — GREEN (implementer backend)
Read `implementer.backend` from session.yml (absent = `agent`). Both
backends satisfy the same contract — see
`skills/london-bdd/references/implementer-backends.md`. Context to pass
— nothing more, regardless of backend:
- The failing test file content
- The interface/port definitions it references
- The language notes reference relevant to the stack

**`backend: agent` (default) — Haiku subagent.** Dispatch the
`london-bdd:implementer` agent with the context above. It writes the
minimum production code, runs the tests, reports.

**`backend: openai` — external model.** Confirm `OPENAI_API_KEY` is set
in the environment first — if it's not, stop and tell the user rather
than silently falling back to `agent`. Run
`scripts/openai_implementer.py` via Bash, piping the context as JSON on
stdin (test file + name, interface file paths, language notes, a
`test_command` that runs just this test, `implementer.model` from
session.yml, `cwd`). Read its JSON report from stdout the same way as
the agent's final message.

Either way:
- Tests green → announce `🟢 UT: <class> — <behaviour>`.
- Still red after the backend's honest attempts (or the script exits 1 —
  a config/protocol error, not a red test) → bring the failure back to
  the main session; you and the user diagnose. Do not loop the backend
  blindly.

### 3 — REVIEW + REFACTOR (reviewer agent — Sonnet)
Dispatch `london-bdd:reviewer` with the diff of this cycle. It critiques
(sentence heuristic, naming vs ubiquitous language, duplication, mock
smells, boundary violations, over-implementation beyond the test) and
**proposes** refactors.
- `assisted`: present the proposals to the user; apply only the accepted
  ones.
- `autonomous`: apply `should`/`consider` proposals directly, keeping all
  tests green. A `block` finding is an escalation trigger (see below) —
  stop the loop, present it to the user, and wait. Do not apply a fix to
  a `block` finding on your own judgment.

Announce `🔵 Refactor`.

### 4 — COMMIT (once per cycle, feature/<slice>-tmp only)
- Verify branch again (belt and braces — the hook also checks).
- Clear `current_failing_test`, set collaborator `status: done`,
  increment `cycle`, update `last_commit` in session.yml.
- Commit test + impl + refactor + session.yml together:
  `cycle <n>: <collaborator> — <behaviour>`

### 5 — NEXT
- `assisted`: queue non-empty → tell the user `/inner` again for the next
  collaborator. Queue empty → set `phase: close`; tell the user next
  command is `/review`.
- `autonomous`: queue non-empty and no escalation triggered → loop back
  to step 1 for the next collaborator in the same turn, no waiting for
  the user to re-invoke `/inner`. Queue empty → set `phase: close`,
  summarize all cycles run, and tell the user `/review` is next — this
  gate is unconditional, autonomous or not.

## Escalation triggers — override autonomy, always

Any of these stop an `autonomous` run immediately and hand back to the
human, exactly as they would interrupt an `assisted` one:

- The GREEN-step backend stays red after honest attempts within its turns
  (never loop it blindly, never widen its context to "help" it pass), or
  an external backend exits with a protocol error (e.g. missing
  `OPENAI_API_KEY`).
- The reviewer emits a `block`-severity finding.
- A hook rejects an action (Rules A–D) — this means the loop's own model
  of state has drifted from the guard's; don't retry blindly.
- Git state is unexpected (wrong branch, dirty tree, detached HEAD).

## Hard rules

- One failing test at a time. Never start a new red with one open.
- The GREEN-step backend NEVER edits test files or session.yml — the
  `agent` backend by instruction (`agents/implementer.md`), the `openai`
  backend by its own path guard (`scripts/openai_implementer.py`).
- Squash-merging onto feature/<slice>-main happens via `/commit-merge`,
  after `/review` sets `phase: done` — manual by default, or agent-run in
  `--auto` mode with fresh per-invocation authorization. Never merge
  directly here. `autonomy: autonomous` governs `/decompose` and `/inner`
  only and never reaches this step.
