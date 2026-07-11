# london-bdd — London School BDD Double Loop for Claude Code

Outside-in BDD and characterisation-first legacy refactoring as one
enforced workflow: model-routed agents, scope guards, disciplined
branching. Operationalises Freeman & Pryce (GOOS), Feathers (WELC),
Fowler (Refactoring), Evans (DDD), Martin (Clean Architecture/Code),
Humble & Farley (CD).

## Workflows

```
GREENFIELD                          LEGACY (SAFE / FULL_REFACTOR)
/london-bdd:scenario                /london-bdd:refactor-scope
/london-bdd:decompose               /london-bdd:characterise
/london-bdd:inner  (×N)             (/london-bdd:decompose)
/london-bdd:review                  /london-bdd:inner (×N) → :review
                                    /london-bdd:characterise (verify)
Support: /london-bdd:acceptance  /london-bdd:unit  /london-bdd:adr  /london-bdd:debt
```

## What's enforced (hooks)

- **A.** Production edits need a license: a recorded failing test, OR
  phase `close` (wiring), OR SAFE mode with a green characterisation net.
- **B.** SAFE/FULL_REFACTOR: no edit outside the declared scope —
  "while we're here" must be explicit or logged to debt.
- **C.** Agent commits only on `feature-tmp/*`; merges are human-only.

The guard is silent when no `.bdd/session.yml` slice is active.

## Model routing

| Work | Who |
|---|---|
| Scenario, decomposition, unit tests, review decisions | Main session + you |
| Minimum implementation | `implementer` agent (Haiku, can't touch tests) |
| Design critique | `reviewer` agent (Sonnet, read-only) |

## Branching

`feature-tmp/<slice>`: one agent commit per cycle (test+impl+refactor),
disposable. `feature-main/<slice>`: you squash-merge by hand when a slice
is meaningfully complete. `.bdd/` files stay out of the squash.

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
- Agent commits: feature-tmp only; I squash to feature-main myself
Domain glossary: docs/glossary.md (role names must match it)
```

## Layout

```
.claude-plugin/plugin.json     manifest
commands/                      workflow entry points (thin)
agents/implementer.md          Haiku, minimum code, no test edits
agents/reviewer.md             Sonnet, critique only
hooks/hooks.json + scripts/    the three hard rules
skills/london-bdd/             knowledge layer + references
```
