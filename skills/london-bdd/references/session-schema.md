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
autonomy: assisted                  # assisted (default) | autonomous
implementer:                        # GREEN-step executor (optional block;
  backend: agent                    #   absent = agent, same as today)
  model: null                        # backend: agent (default) | codex —
                                    # model: optional override; agent: an
                                    # Agent-tool alias (haiku|sonnet|opus),
                                    # codex: passed as --model
                                    # (see references/implementer-backends.md)
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

- `autonomy` gates whether `/decompose` and `/inner` pause for the user at
  each step. `assisted` (the default — assumed when the field is absent,
  so existing session files behave exactly as before) keeps every
  checkpoint described in those commands. `autonomous` lets the agent
  drive role naming and cycle selection unattended. It is set once, at
  slice start (`/scenario` or `/refactor-scope`), never defaulted to, and
  never silently upgraded mid-slice — switching requires the same explicit
  checkpoint as a mode switch. It governs `/decompose` and `/inner` only:
  `/scenario`, `/acceptance`, `/refactor-scope`, `/review`, and
  `/commit-merge` are always human-paced regardless of this field (note
  `/commit-merge --auto` is a separate, per-invocation authorization —
  `autonomy: autonomous` does not imply it). Three things escalate to the
  human even in `autonomous` mode: a `reviewer` finding of severity
  `block`, an implementer that doesn't reach green within its turns, and
  any hook rejection (Rules A–D) — see `commands/inner.md`. This field
  also changes what `scripts/guard.py` does at the point it would
  otherwise stay silent: `assisted` sessions fall through to Claude Code's
  normal interactive approval prompt on every Edit/Write/Bash call (the
  guard has always only ever blocked or said nothing); `autonomous`
  sessions get an explicit PreToolUse `allow` decision instead, once an
  action has already survived Rules A–D — so a licensed unattended run
  isn't still stopped for a human to click "approve" on every single
  change. Rules A–D are never relaxed by this; it only removes the prompt
  for what they already license.
- `implementer.backend` selects the GREEN-step executor `/inner` dispatches:
  `agent` (the default — absent behaves exactly as before this field
  existed) runs the `london-bdd:implementer` Haiku subagent; `codex` shells
  out to `scripts/codex_implementer.py`, which runs `codex exec` (OpenAI's
  Codex CLI) non-interactively and verifies the result itself — see
  `references/implementer-backends.md` for exactly how it checks Codex
  didn't touch tests or `.bdd/`, and re-runs the test command rather than
  trusting Codex's own claim. `implementer.model` is passed straight
  through as `codex exec --model <value>` when set (`backend: codex`), or
  as the Agent tool's `model` override (`backend: agent`, an alias such as
  `sonnet`); leave it unset for the backend's default (Haiku for `agent`,
  Codex's own config for `codex`). `backend` itself follows the same discipline as `autonomy`:
  set once at slice start (`/scenario` or `/refactor-scope`), never
  silently upgraded — switching backends mid-slice is an explicit
  checkpoint with the user. The `codex` backend requires the `codex` CLI
  on `PATH` and already authenticated; `/inner` stops and asks rather than
  silently falling back to `agent` if it's missing.
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
  met yet (e.g. `close` requires every collaborator `done`), so a step
  can't be skipped by writing the field directly.
- Don't re-derive "what's next" by exploring the repo — it's a lookup,
  not a judgment call. Run `/status` (`scripts/next.py`), which parses
  this file the same way the guard hook does.
- One slice per session file. New slice = archive old file to
  `.bdd/archive/<slice>.yml`, create fresh.
