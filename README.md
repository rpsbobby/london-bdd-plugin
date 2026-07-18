# london-bdd — London School BDD Double Loop for Claude Code

Outside-in BDD and net-first refactoring of existing code as one
enforced workflow: model-routed agents, scope guards, disciplined
branching. The net is the license to change code — a trusted existing
suite where one exists, a characterisation suite built first where one
doesn't. Operationalises Freeman & Pryce (GOOS), Feathers (WELC),
Fowler (Refactoring), Evans (DDD), Martin (Clean Architecture/Code),
Humble & Farley (CD).

## Workflows

```
GREENFIELD                          EXISTING CODE (SAFE / FULL_REFACTOR)
/london-bdd:scenario                /london-bdd:refactor-scope (declares net)
/london-bdd:decompose               /london-bdd:characterise (only if net gap)
/london-bdd:inner  (×N)             (/london-bdd:decompose)
/london-bdd:review                  /london-bdd:inner (×N) → :review
                                    net re-run (verify: still green)
/london-bdd:commit-merge            /london-bdd:commit-merge
Support: /london-bdd:acceptance  /london-bdd:unit  /london-bdd:adr  /london-bdd:debt  /london-bdd:status
```

Every command tells you which one is next when it finishes. Lost track
mid-slice? Run `/london-bdd:status` — it reads `.bdd/session.yml` and
prints the next command, no need to remember the diagram above.

## Command reference

All commands live under the `/london-bdd:` prefix.

**Slice entry points** — every piece of work starts with exactly one of these:

| Command | Use when | What it does |
|---|---|---|
| `/london-bdd:scenario` | Starting **new** behaviour (greenfield) | Conversation first: agree ubiquitous language, write the Gherkin scenario and the failing acceptance test — the outer red. |
| `/london-bdd:refactor-scope` | Refactoring **existing** code, tested or not | Declares the blast radius (what/in/out/seams, SAFE or FULL_REFACTOR mode) and the net: existing trusted suites (verified green — /characterise skipped) or a characterisation net to build. Scope only — never solution design. |

**The loop** — run in order once a slice is open:

| Command | Phase | What it does |
|---|---|---|
| `/london-bdd:characterise` | Existing code with a net gap, before change | Locks in CURRENT behaviour (right or wrong) as a regression net around the uncovered scope. Skipped when `/refactor-scope` declared existing suites as the net. Re-run post-slice to verify behaviour preserved. |
| `/london-bdd:decompose` | Between outer red and inner loop | Discovers collaborators, names roles in DDD language, sketches interface boundaries, agrees the sequence — before any code. |
| `/london-bdd:inner` | Inner loop, ×N | One full cycle for the next collaborator: failing unit test with you, minimum implementation (implementer agent), review and refactor (reviewer agent), one commit on feature/<slice>-tmp. |
| `/london-bdd:review` | Collaborator queue empty | Slice-level gate: reviewer agent audits the whole diff, clean-code pass, distil-candidate triage, then closes the outer loop. |
| `/london-bdd:commit-merge` | `phase: done` | Lands the slice: squash-merges feature/<slice>-tmp onto feature/<slice>-main. Manual by default (prints the commands); `--auto` runs the merge itself, authorized fresh each invocation. Never pushes. |

**Support** — invoked directly at any time, or by the loop commands:

| Command | What it does |
|---|---|
| `/london-bdd:acceptance` | Writes/extends a DSL-driven acceptance test (Given/When/Then). Usually via `/scenario`; direct for sad paths or a new AT. |
| `/london-bdd:unit` | One failing unit test for the current collaborator — behaviour-named, mocked collaborators, ~10 lines max. Usually via `/inner`. |
| `/london-bdd:adr` | Records an architecture decision — Context, Decision, Consequences, one page, in `adr/` next to the code. |
| `/london-bdd:debt` | Logs a `tech-debt/register.yml` entry — for scope-creep temptations, bugs found during characterisation, and every "while we're here". |
| `/london-bdd:status` | Prints exactly which command runs next, read straight from `.bdd/session.yml` — a deterministic lookup, not something to re-derive from context. |

## What's enforced (hooks)

- **A.** Production edits need a license: a recorded failing test, OR
  phase `close` (wiring), OR SAFE mode with a green net — the declared
  existing suite or a characterisation suite; the hook checks status,
  not kind.
- **B.** SAFE/FULL_REFACTOR: no edit outside the declared scope —
  "while we're here" must be explicit or logged to debt.
- **C.** Agent commits only on `feature/*-tmp`. Merges onto
  `feature/*-main` are human-only by default, or agent-run via
  `/commit-merge --auto` with fresh per-run authorization; rebases and
  pushes are always human.
- **D.** Phase transitions in `.bdd/session.yml` are forward-only and
  earned: entering `inner`/`close`/`done` requires the actual
  preconditions (outer net exists, collaborator queue drained, etc.) —
  a step can't be skipped just by writing the field.

The guard is silent when no `.bdd/session.yml` slice is active.

## Model routing

| Work | Who |
|---|---|
| Scenario, decomposition, unit tests, review decisions | Main session + you |
| Minimum implementation | `implementer` agent (Haiku, can't touch tests) |
| Design critique | `reviewer` agent (Sonnet, read-only) |

## Branching

`feature/<slice>-tmp`: one agent commit per cycle (test+impl+refactor),
disposable. `feature/<slice>-main`: landed via `/commit-merge` when the
slice is meaningfully complete — manual by default (you run the squash
yourself), or `--auto` to let the agent run it, confirmed fresh every
time. `.bdd/` files stay out of the squash.

## Install

This repo is a self-contained plugin **and** its own marketplace (the
`.claude-plugin/marketplace.json` catalogs the plugin at the repo root).
Installation is always two steps: register the marketplace, then install.

**From GitHub (recommended):**
```
/plugin marketplace add <you>/london-bdd
/plugin install london-bdd@london-bdd-marketplace
/reload-plugins
```
`<you>/london-bdd` is your `owner/repo`. The marketplace *name* comes from
the `name` field in `marketplace.json` (`london-bdd-marketplace`), which is
what you install against — not the repo name.

**From a local clone (for developing the plugin itself):**
```
git clone https://github.com/<you>/london-bdd
/plugin marketplace add ./london-bdd
/plugin install london-bdd@london-bdd-marketplace
```
Local-path install is CLI-only today; the desktop app's plugin UI supports
marketplace installs but not local-directory registration.

**Scope:** user scope (default) applies it across all your projects;
project scope commits the install to `.claude/settings.json` so teammates
who clone your work repo are offered it automatically — this is the path
for "if it works, it should speak for itself."

**Requirements & upkeep:** `python3` on PATH (guard hook). Commands and
`SKILL.md` edits apply immediately; changes to hooks or agents need
`/reload-plugins`. If skills don't appear after install, clear the cache
(`rm -rf ~/.claude/plugins/cache`), restart, reinstall.

## Turning this into a tracked GitHub repo

The unzipped folder is already a complete repo layout — just version it:
```
cd london-bdd
git init
git add .
git commit -m "feat: london-bdd plugin v0.1.0"
git branch -M main
git remote add origin https://github.com/<you>/london-bdd.git
git push -u origin main
```
The repo must be **public** — Claude Code fetches marketplaces directly
from GitHub. Once pushed, the install commands above work for you and
anyone you share it with. Bump `version` in **both** `plugin.json` and (if
you later pin versions there) the marketplace entry when you cut releases;
if `version` is unset, the commit SHA is used as the version.

## Suggested CLAUDE.md snippet

```markdown
## Delivery workflow
This project uses the london-bdd plugin for all feature and refactor work.
- New behaviour            → /london-bdd:scenario
- Any change to legacy code → /london-bdd:refactor-scope FIRST
- Never write production code without a failing test (hook-enforced)
- Agent commits: feature/<slice>-tmp only; land slices via /commit-merge
Domain glossary: docs/glossary.md (role names must match it)
```

## Layout

```
.claude-plugin/plugin.json     manifest
commands/                      workflow entry points (thin)
agents/implementer.md          Haiku, minimum code, no test edits
agents/reviewer.md             Sonnet, critique only
hooks/hooks.json + scripts/    the four hard rules + next.py (/status)
tests/test_guard.py            regression suite for the guard hook (pytest)
tests/test_next.py             regression suite for /status (pytest)
skills/london-bdd/             knowledge layer + references
```

`scripts/guard.py` is the one piece of this repo that's actual code rather
than prompts — it has its own test suite: `python3 -m pytest tests/`.
