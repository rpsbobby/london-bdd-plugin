---
name: refactor-scope
description: Start a SAFE or FULL_REFACTOR slice on existing code — declare the scope (what/in/out/seams/mode) and the net (trusted existing suites, or characterisation to build), never the design. Use before refactoring any existing code, tested or not.
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
   - `SAFE` (default): net → small moves → verify. Boy scout rule.
   - `FULL_REFACTOR`: only with an explicit mandate. Ask: "Has this been
     agreed with the team?" Record the answer in the scope artifact.
4. **Assess the net.** The net is the license; characterisation is only
   one way to build it. Ask: is the declared scope already covered by
   trusted behavioural tests (e.g. code built through the double loop,
   with loosely coupled outcome-asserting ATs)?
   - **Covered:** run those suites NOW and show the output. If green, the
     user confirms the declaration and the net is
     `net: {kind: existing, suites: [...], status: green}` —
     `/characterise` is skipped entirely. This is a human judgment,
     recorded, never assumed: "the suite exists" is not "the user
     declared it trusted".
   - **Not covered / not trusted / partial:** the net (or the gap) must
     be characterised first — `net: {kind: characterisation, status: absent}`.
   Coverage that is implementation-coupled does NOT qualify — a net that
   breaks on refactoring is not a net.
5. Create branches (`feature/<slice>-main`, `feature/<slice>-tmp`), check
   out feature/<slice>-tmp.
6. Write `.bdd/session.yml` with `mode`, the scope block, branch fields,
   the `net:` block, and the phase the net decision earned:
   - net still to build → `phase: characterise`
   - net existing + green → `phase: inner` (SAFE) or `phase: decompose`
     (FULL_REFACTOR)
7. Write the human-readable scope artifact to `.bdd/scope-<slice>.md`
   (template in references — include the net declaration and why).
   Commit: `chore: declare refactor scope — <slice>`
8. Tell the user the next command: `/characterise` if the net must be
   built (**no production edit is possible until the net is green** — the
   hooks enforce this), otherwise `/inner` (SAFE) or `/decompose`
   (FULL_REFACTOR) — the existing green suite is already the license.

## Rules

- Scope creep is the enemy. If the user adds "and also…" mid-discussion,
  offer: extend scope explicitly (update session.yml + artifact) or log it
  to `/debt`. Never silently absorb it.
- If more than ~5 files land in `in:`, challenge the slice size.
