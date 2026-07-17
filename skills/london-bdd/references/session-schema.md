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
branch: feature/place-order-tmp     # expected working branch
base_branch: feature/place-order-main

# GREENFIELD / FULL_REFACTOR — the outer net is the acceptance test
acceptance_test:
  file: tests/acceptance/place_order_test.cpp
  name: PlaceOrder.ReturnsIdAndPersists
  status: red                       # red | green | absent

# SAFE / FULL_REFACTOR — the outer net is the characterisation suite
characterisation:
  suite: tests/characterisation/pricing/
  status: green                     # must be green before any edit in SAFE
  distil_candidates: []             # ugly tests flagged for later rewrite

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
    status: done                    # pending | red | green | done
  - role: OrderRepository
    status: red
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

- `current_failing_test` is set by `/unit` (or `/acceptance` for the outer
  red) and cleared by the commit step at the end of the cycle. The
  production-edit hook keys off this field.
- `scope.in` / `scope.out` use glob patterns relative to project root.
  The scope hook keys off these in SAFE and FULL_REFACTOR modes.
- `phase` transitions are forward-only within a slice:
  `scope → characterise → scenario → decompose → inner → close → done`
  (GREENFIELD skips scope/characterise). Commands refuse to run out of
  order and say which command is expected next. `done` is terminal for the
  slice; `/commit-merge` is the only command that still acts on it.
  This is hook-enforced, not just documented: `scripts/guard.py`'s Rule D
  validates the target phase on every edit to session.yml — it blocks
  backward moves and moves into a phase whose precondition isn't actually
  met yet (e.g. `close` requires every collaborator `done`), so a step
  can't be skipped by writing the field directly.
- Don't re-derive "what's next" by exploring the repo — it's a lookup,
  not a judgment call. Run `/status` (`scripts/next.py`), which parses
  this file the same way the guard hook does.
- One slice per session file. New slice = archive old file to
  `.bdd/archive/<slice>.yml`, create fresh.
