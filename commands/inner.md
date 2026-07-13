---
name: inner
description: Run one full inner-loop cycle for the next collaborator — failing unit test (with the user), minimum implementation (implementer agent, Haiku), review and refactor (reviewer agent, Sonnet), one commit on feature/<slice>-tmp. Repeat until the collaborator queue is empty.
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

### 1 — RED (you + user, main session)
Follow `/unit` for the head-of-queue collaborator. Ends with
`current_failing_test` set and `🔴 UT` announced.

### 2 — GREEN (implementer agent — Haiku)
Dispatch the `london-bdd:implementer` agent. Context to pass — nothing
more:
- The failing test file content
- The interface/port definitions it references
- The language notes reference relevant to the stack
The agent writes the minimum production code, runs the tests, reports.
- Tests green → announce `🟢 UT: <class> — <behaviour>`.
- Still red after the agent's turns → bring the failure back to the main
  session; you and the user diagnose. Do not loop the agent blindly.

### 3 — REVIEW + REFACTOR (reviewer agent — Sonnet)
Dispatch `london-bdd:reviewer` with the diff of this cycle. It critiques
(sentence heuristic, naming vs ubiquitous language, duplication, mock
smells, boundary violations, over-implementation beyond the test) and
**proposes** refactors. Present the proposals to the user; apply only the
accepted ones. All tests must stay green. Announce `🔵 Refactor`.

### 4 — COMMIT (once per cycle, feature/<slice>-tmp only)
- Verify branch again (belt and braces — the hook also checks).
- Clear `current_failing_test`, set collaborator `status: done`,
  increment `cycle`, update `last_commit` in session.yml.
- Commit test + impl + refactor + session.yml together:
  `cycle <n>: <collaborator> — <behaviour>`

### 5 — NEXT
Queue non-empty → tell the user `/inner` again for the next collaborator.
Queue empty → set `phase: close`; tell the user next command is `/review`
for the slice gate, then close the outer loop (wire the composition root,
run the AT / characterisation verification).

## Hard rules

- One failing test at a time. Never start a new red with one open.
- The implementer agent NEVER edits test files or session.yml.
- Squash-merging onto feature/<slice>-main happens via `/commit-merge`,
  after `/review` sets `phase: done` — manual by default, or agent-run in
  `--auto` mode with fresh per-invocation authorization. Never merge
  directly here.
