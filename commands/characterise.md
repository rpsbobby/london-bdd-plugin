---
name: characterise
description: Build the characterisation net around the declared scope — lock in CURRENT behaviour as a regression suite before any change. Also used post-slice to verify behaviour preserved.
---

# /characterise — Lock In What IS, Not What Should Be

Read the `london-bdd` skill and `references/characterisation.md`.

A characterisation test records what the code **actually does** — right or
wrong. It is the outer net for SAFE and FULL_REFACTOR modes, playing the
role the acceptance test plays in greenfield.

## Preconditions

1. `.bdd/session.yml` exists with a declared scope, `phase: characterise`
   (or `phase: close`, for the post-slice verification run).
2. On the slice's `feature/<slice>-tmp` branch.

## Building the net (phase: characterise)

For each seam declared in scope:

1. **Probe first.** Write a test with a deliberately wrong assertion, run
   it, and let the failure output reveal the real behaviour. Then lock the
   observed value in. Show the user each discovered behaviour — surprises
   here are gold.
2. **Cover the scope, not the world.** Only behaviour reachable through
   the declared seams. Inputs: typical cases, boundaries, and any case the
   user knows customers hit.
3. **Style rules — deliberately relaxed:**
   - No DSL forced. Given/When/Then only if it falls out naturally.
   - Correctness over readability. Hardcoded magic values, long bodies,
     odd setups are ALL acceptable here.
   - **Ugliness is a signal, not a defect.** Every test that hurts to read
     gets added to `characterisation.distil_candidates` in session.yml —
     it marks behaviour that needs a better model distilled later. Do not
     beautify it now.
4. Tests live in `tests/characterisation/<area>/`. They must run in the
   commit stage locally and are wired into the pipeline's regression gate.
5. When the net is green and the user agrees it covers the scope:
   - Update session.yml: `characterisation.status: green`,
     `phase: decompose` (FULL_REFACTOR) or `phase: inner` (SAFE — small
     moves may not need formal decomposition; ask the user).
   - Commit: `test: characterisation net — <slice>`
   - Tell the user the next command: `/decompose` (FULL_REFACTOR) or
     `/inner` (SAFE).

## Verification run (phase: close)

Run the suite. Green = behaviour preserved; report and hand back to
`/review`, which invoked this run. Red = a change altered observable
behaviour. STOP and present the diff to the user: is this an intended
behaviour change (update the test, record WHY in the commit message) or a
regression (fix under the net)? Never decide this alone.

## Rules

- Never "fix" behaviour discovered during characterisation, even obvious
  bugs. Log them to `/debt` or a ticket. The net records reality first.
- Never delete a characterisation test to make it pass.
