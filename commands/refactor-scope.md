---
name: refactor-scope
description: Start a SAFE or FULL_REFACTOR slice on legacy code — declare the scope (what/in/out/seams/mode), not the design. Use before touching any existing untested code.
---

# /refactor-scope — Scope the Change, Not the Code

You are declaring the blast radius of a legacy change. **This command
designs SCOPE, never solution.** No class diagrams, no target
architecture — design emerges later from the loop. Read the `london-bdd`
skill and `references/scope-template.md`.

## Preconditions

1. `.bdd/session.yml` — same rules as /scenario (no active slice, clean git).

## Steps

1. **Ask the driving question:** what change is being asked for, in one
   sentence? (Bug fix, behaviour change, port prep, debt payoff…)
2. **Walk the code with the user.** Identify:
   - `in:` — files/classes that must change
   - `out:` — things adjacent and tempting but explicitly untouched.
     Every "while we're here" candidate goes here or into `/debt`.
   - `seams:` — where a characterisation net can attach without changing
     behaviour (Feathers: extract-and-override, parameterise constructor,
     sprout). Name each seam and its technique.
3. **Declare the mode:**
   - `SAFE` (default): characterise → small moves → verify. Boy scout rule.
   - `FULL_REFACTOR`: only with an explicit mandate. Ask: "Has this been
     agreed with the team?" Record the answer in the scope artifact.
4. Create branches (`feature/<slice>-main`, `feature/<slice>-tmp`), check
   out feature/<slice>-tmp.
5. Write `.bdd/session.yml` with `mode`, `phase: characterise`, the scope
   block, branch fields.
6. Write the human-readable scope artifact to `.bdd/scope-<slice>.md`
   (template in references). Commit: `chore: declare refactor scope — <slice>`
7. Tell the user: next command is `/characterise`. **No production edit is
   possible until the net exists** — the hooks enforce this.

## Rules

- Scope creep is the enemy. If the user adds "and also…" mid-discussion,
  offer: extend scope explicitly (update session.yml + artifact) or log it
  to `/debt`. Never silently absorb it.
- If more than ~5 files land in `in:`, challenge the slice size.
