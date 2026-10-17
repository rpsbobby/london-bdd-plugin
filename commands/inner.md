---
name: inner
description: Work the slice's test list through the inner loop. batch (default) — one Sonnet builder subagent builds every planned test (red, green, refactor, commit per test) and proposes missing UT/AT behaviour; the driver (main session) reviews the result and the proposals with the user. granular — the human-paced per-test cycle with the Haiku implementer and Sonnet reviewer. Mode comes from session.yml's inner field.
---

# /inner — Build the Test List

The orchestrator. Read the `london-bdd` skill first.

## Preconditions — verify ALL before starting

1. `.bdd/session.yml` exists, `phase: inner`, with at least one `tests:`
   item not `done`, or discovery decisions still to make. (A SAFE slice
   that skipped `/decompose` has no list. It refactors under its green
   net and doesn't use this command's build steps.)
2. **Branch check:** `git branch --show-current` equals session `branch`
   (a `feature/*-tmp`).
   - On the slice's feature/<slice>-main → offer: "Inner loop runs on
     feature/<slice>-tmp only. Create/checkout `<branch>` from here? [y/n]".
     Never proceed on feature/<slice>-main.
   - Anywhere else / detached / dirty → STOP, explain, let the human fix.
     Never auto-stash, never auto-commit rescue work.
3. Outer net intact: AT red for the right reason (greenfield) or net
   green (SAFE/FULL_REFACTOR).

Read `inner` from session.yml (absent = `batch`).

## Batch mode (default)

### 1 — BUILD (builder subagent, Sonnet)
Dispatch `london-bdd:builder` once with the repo root, slice name,
`.bdd/session.yml` path, and `round: 1` (or `2`, see step 4). It reads
everything else itself, builds every open test, and, in round 1 only,
ends with discovery proposals. Do not run the cycle inline; isolating it
keeps every test's diff off the driver's context.

Escalated report → present it verbatim and stop. The report names the
next step. Never re-dispatch blindly.

### 2 — DRIVER REVIEW (main session, with the user)
You are the reviewer now. Read `agents/reviewer.md` and apply its
checklist yourself to the builder's diff
(`git diff <sha before dispatch>..HEAD`), with the test list beside it.
Present, together:
- **Findings**, `block | should | consider`, as `reviewer.md` defines.
  Production code is unlicensed now (no failing test is open), so don't
  apply refactors here. Write accepted `should`/`consider` findings to
  `.bdd/review-<slice>.md`. `/review` applies them under phase `close`.
  A `block` for code without a covering test becomes a UT proposal.
- **Discovery proposals** from the builder's report, UT and AT.

Walk them with the user. They decide every item.

### 3 — RECORD DECISIONS
Follow "Recording decisions" in
`skills/london-bdd/references/test-discovery.md`:
- approved UTs → `tests:` with `origin: discovered`, `status: pending`
- approved AT `this-slice` → `/acceptance` (recorded red), then its UTs
  → `tests:` as discovered, approved with the user
- AT `other-slice` → `docs/backlog.md`
- rejected → drop, or `/debt`

Commit: `docs: discovery decisions — <slice>`.

### 4 — ROUND 2 OR CLOSE
New open tests → dispatch the builder again with `round: 2`. It builds
them and does not discover. Review its diff as in step 2 (findings only,
no proposals), then continue below.

No open tests → set `phase: close` (the guard checks every test is
`done`). Tell the user the next command is `/review`.

## Granular mode (`inner: granular`)

The human-paced cycle, one test per `/inner` call.

### 1 — RED (main session)
Follow `/unit` for the head open test in `tests:`. It ends with
`current_failing_test` set and `🔴 UT` announced.

### 2 — GREEN (implementer agent, Haiku)
Dispatch `london-bdd:implementer` with only: the failing test file, the
interface/port definitions it references, and the relevant language notes.
- Green → set the test's `status: green` (keep `current_failing_test`:
  it licenses the refactor), commit test + impl + session.yml as
  `cycle <n>: <collaborator> — <behaviour> (green)`, and announce
  `🟢 UT: <class> — <behaviour>`.
- Still red after its honest attempts → bring the failure back; you and
  the user diagnose. Don't loop it blindly.

### 3 — REVIEW + REFACTOR (reviewer agent, Sonnet)
Dispatch `london-bdd:reviewer` with this cycle's diff. Present its
proposals. Apply only the ones the user accepts, keeping everything
green. Announce `🔵 Refactor`.

### 4 — COMMIT
- Verify the branch again (the hook also checks).
- Clear `current_failing_test`, set the test `status: done`, set the
  collaborator `status: done` if all its tests are done, increment
  `cycle`, update `last_commit`.
- Commit the refactor + session.yml:
  `cycle <n>: <collaborator> — <behaviour> (refactor)`. With nothing to
  refactor, the commit carries just the bookkeeping.

Both commits run the commit checks (guard Rule E): the repo's git hooks
and the tests in scope. A refused commit is feedback, not an escalation.
Re-add files a hook rewrote, fix what it reports, and fix production code
(never tests) when a test in scope fails. Never skip the hooks.

### 5 — NEXT
Open tests left → tell the user to run `/inner` again.
None left and `discovery_rounds: 0` → run discovery yourself per
`references/test-discovery.md` (UT + AT), set `discovery_rounds: 1`, then
batch steps 3 and 4 (recording, close). Granular never dispatches the
builder. Newly approved tests run through `/inner` cycles.

## Escalation — always hand back to the human

- The builder or implementer stays red after honest attempts.
- The builder reports a `design-question`.
- A `block`-severity finding.
- A commit is still refused by its checks after three fixes (the
  builder reports `checks-failing`).
- A hook rejects an action (Rules A–E) for any other reason. The loop's
  model of state has drifted from the guard's, so don't retry blindly.
- Git state is unexpected (wrong branch, dirty tree, detached HEAD).

## Hard rules

- One failing test at a time. Never start a new red with one open.
- The builder and implementer never edit tests to make them pass.
- Discovery proposes. Only the human approves a test into the list.
- At most one automatic discovery round per slice in the inner loop.
- Squash-merging onto feature/<slice>-main happens only via
  `/commit-merge`, after `/review` sets `phase: done`.
