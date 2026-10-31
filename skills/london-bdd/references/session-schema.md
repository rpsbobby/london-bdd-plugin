# Session State — `.bdd/session.yml`

Every command reads this file first and updates it last. It is the single
source of truth for where we are in the workflow. It lives in the project
root under `.bdd/` and is committed to `feature/<slice>-tmp` (it documents
the slice), but excluded from the squash onto `feature/<slice>-main`.

If the file is missing, no slice is active — only `/scenario` or
`/refactor-scope` may create it.

## Schema

```yaml
# .bdd/session.yml
slice: place-order                  # kebab-case slice name
mode: GREENFIELD                    # GREENFIELD | SAFE | FULL_REFACTOR
phase: inner                        # scope | characterise | scenario |
                                    # decompose | inner | close | done
inner: batch                        # batch (default) | granular
checks:                             # run by the guard on every slice commit
  tests: uv run pytest {files}      # {files} = the tests in scope (Rule E)
branch: feature/place-order-tmp     # expected working branch
base_branch: feature/place-order-main

# GREENFIELD / FULL_REFACTOR — the outer net is the acceptance test
acceptance_test:
  file: tests/acceptance/place_order_test.cpp
  name: PlaceOrder.ReturnsIdAndPersists
  status: red                       # red | green | absent

# SAFE / FULL_REFACTOR — the outer net. The NET is the license to change
# code; characterisation is only one way to build one. If the scope is
# already covered by trusted behavioural tests (e.g. code built through
# the double loop), the human declares them the net at /refactor-scope
# and /characterise is skipped entirely.
net:
  kind: characterisation            # existing | characterisation
  suites:                           # what constitutes the net
    - tests/characterisation/pricing/
  status: green                     # must be green before any edit in SAFE
  distil_candidates: []             # ugly tests flagged for later rewrite
                                    # (characterisation kind only)

# Refactor scope (SAFE and FULL_REFACTOR only) — see scope-template.md
scope:
  in:
    - src/pricing/LegacyPricer.cpp
    - src/pricing/LegacyPricer.h
  out:
    - src/pricing/TaxTable.cpp      # explicitly untouched, even if ugly
  seams:
    - "LegacyPricer::calculate — parameterise config"

# Inner loop bookkeeping
collaborators:
  - role: OrderService
    status: done                    # pending | red | done
  - role: OrderRepository
    status: red
tests:                              # the build list, in order — written by
  - name: should_place_order_and_return_id   # /decompose, extended by
    collaborator: OrderService      #   approved discovery proposals
    origin: planned                 # planned | discovered | review
    status: done                    # pending | red | green | done
  - name: should_save_order_and_return_id
    collaborator: OrderRepository
    origin: planned
    status: red
  - name: should_reject_duplicate_order_id
    collaborator: OrderRepository
    origin: discovered
    status: pending
discovery_rounds: 1                 # inner-loop discovery rounds run (0|1)
current_failing_test:
  file: tests/unit/OrderRepository_test.cpp
  name: OrderRepository.SavesAndReturnsId
  # non-null => production edits permitted (hook rule A)

cycle: 3                            # increments per completed t+i+r cycle
last_commit: "cycle 3: OrderService delegates to OrderRepository"
```

`/commit-merge --auto` authorizes its squash-merge through a *separate*,
untracked `.bdd/.merge-authorized` marker file — never a session.yml
field. `git checkout feature/<slice>-main` removes session.yml from the
working tree (it's tracked only on the tmp branch), so nothing in
session.yml can carry state across that checkout. See `/commit-merge` and
`scripts/guard.py` for the marker's exact format and lifecycle.

## Field rules

- `inner` picks how `/inner` works the test list. `batch` (the default,
  assumed when the field is absent) dispatches the `london-bdd:builder`
  Sonnet subagent to build every open test unattended (red, green,
  refactor, commit per test), then the driver (main session) reviews the
  result and the builder's discovery proposals with the human.
  `granular` is the human-paced cycle: one test per `/inner` call, the
  Haiku `implementer` for GREEN and the Sonnet `reviewer` per cycle. Both
  modes share `/decompose`'s single approval of the test list, and both
  stop for the human on a `block` finding, a test that stays red, or a
  hook rejection. `inner` is set once at slice start (`/scenario` or
  `/refactor-scope`) and switching mid-slice is an explicit checkpoint
  with the user. It governs `/inner` only: `/scenario`, `/acceptance`,
  `/decompose`, `/review`, and `/commit-merge` are human-paced in both
  modes (`/commit-merge --auto` is a separate, per-invocation
  authorization). It also changes what `scripts/guard.py` does when it
  would otherwise stay silent. `granular` sessions fall through to
  Claude Code's normal interactive approval prompt on every
  Edit/Write/Bash call. `batch` sessions get an explicit PreToolUse
  `allow` once an action has survived Rules A–E, so the unattended
  builder isn't stopped for a click on every change. Rules A–E are never
  relaxed by this. It only removes the prompt for what they already
  license.
- `checks.tests` is the command template the guard runs on every agent
  commit in the slice (Rule E). `{files}` is replaced with the tests in
  scope, or they're appended when the placeholder is missing. In scope:
  test files (by name: `test_*`, `*_test.*`, `*.test.*`, `*.spec.*`,
  `*Test.*`) changed since `base_branch`, untracked ones included; the
  acceptance test only from phase `close` on, since it's red on purpose
  before that; and in SAFE/FULL_REFACTOR, every path in `net.suites`. A
  failure blocks the commit with the output. Absent = no test run, but
  the repo's git hooks are still protected from being skipped. Set at
  slice start (`/scenario`, `/refactor-scope`). The red step never
  commits, because its new test would fail the checks.
- `tests` is the build list. `/decompose` writes it (`origin: planned`)
  after the human approves the whole map. Approved discovery proposals
  are appended (`origin: discovered`), as are behaviour findings accepted
  at `/review` (`origin: review`). Nothing else adds to it: discovery
  and review only propose. The head non-`done` item is the next test, in both modes.
  A collaborator is `done` when all its tests are.
- `discovery_rounds` counts inner-loop discovery rounds. The builder (or,
  in granular mode, the driver) runs discovery only while it is 0, then
  sets it to 1. A second round happens only when the human asks. See
  `references/test-discovery.md`.
- AT candidates for other slices go to `docs/backlog.md`, never to
  session.yml. That file is excluded from the squash and archived per
  slice, while the backlog has to outlive both.
- `current_failing_test` is set by `/unit` (or `/acceptance` for the outer
  red) and cleared by the commit step at the end of the cycle. The
  production-edit hook keys off this field.
- `scope.in` / `scope.out` use glob patterns relative to project root.
  The scope hook keys off these in SAFE and FULL_REFACTOR modes.
- `net.kind: existing` records the human's declaration (made at
  `/refactor-scope`, after a real green run) that the scope is already
  covered by trusted suites. `net.kind: characterisation` means
  `/characterise` built the net. The guard checks `net.status` only —
  the kind is a recorded human judgment, never re-derived. A legacy
  `characterisation:` block (pre-`net:` schema) is still honoured by
  the guard as a characterisation-kind net.
- `phase` transitions are forward-only within a slice:
  `scope → characterise → scenario → decompose → inner → close → done`
  (GREENFIELD skips scope/characterise; SAFE/FULL_REFACTOR skips
  characterise when the net is a declared existing suite). Commands
  refuse to run out of
  order and say which command is expected next. `done` is terminal for the
  slice; `/commit-merge` is the only command that still acts on it.
  This is hook-enforced, not just documented: `scripts/guard.py`'s Rule D
  validates the target phase on every edit to session.yml — it blocks
  backward moves and moves into a phase whose precondition isn't actually
  met yet (e.g. `close` requires every collaborator and every test `done`; GREENFIELD `inner` requires a non-empty `tests:` list), so a step
  can't be skipped by writing the field directly. One backward move is
  allowed: `close → inner`, while a `tests:` entry with `origin: review`
  is open, so `/review` can send an accepted behaviour finding back
  through a failing test first (the GREENFIELD red-acceptance check is
  waived on that re-entry, since wiring may have turned it green). The
  forward exception: a
  SAFE/FULL_REFACTOR slice with `net.kind: existing`, `net.status: green`
  and an empty `tests:` list may enter `close` with no collaborators,
  since it refactors under its green net and builds nothing new.
- Don't re-derive "what's next" by exploring the repo — it's a lookup,
  not a judgment call. Run `/status` (`scripts/next.py`), which parses
  this file the same way the guard hook does.
- One slice per session file. New slice = archive old file to
  `.bdd/archive/<slice>.yml`, create fresh.
