---
name: scenario
description: Start a GREENFIELD slice — discuss the use case, agree ubiquitous language, write the Gherkin scenario and the failing acceptance test (outer red). Use when beginning new behaviour.
---

# /scenario — Outer Loop Entry (Greenfield)

You are opening the outer loop of the London School double loop. This is a
**conversation first, test second** command. Read the `london-bdd` skill
before proceeding.

## Preconditions (check before anything else)

1. Read `.bdd/session.yml` if it exists.
   - If a slice is active and `phase != done`: STOP. Tell the user which
     slice/phase is active and which command is expected next.
   - If the previous slice is `done`: archive it to `.bdd/archive/`.
2. Check git state: must be clean. Never auto-stash.

## Phase 0 — Discuss (do not skip, do not rush)

Work through these WITH the user, one at a time:

1. **Behaviour in one sentence**, in business language. Push back on
   technical framing ("insert row" → "customer places an order").
2. **Ubiquitous language check** — do the nouns/verbs match the domain
   glossary and existing code? Flag any drift. New terms get agreed here.
3. **Entry point** and **observable outcome** — externally visible only.
4. **One meaningful sad path** to cover alongside the happy path.
5. **Clean architecture boundary** — which layer does the AT enter through?
   (Application layer preferred; UI entry only for smoke tests.)

## Phase 1 — Scenario + failing AT

1. Write the Gherkin scenario (shape in the skill: Feature/Background/
   Scenario, happy + sad path). Confirm with the user.
2. Create the branches:
   - `feature-main/<slice>` from the current branch
   - `feature-tmp/<slice>` from feature-main
   - Check out `feature-tmp/<slice>`.
3. Write the failing acceptance test using the `/acceptance` shape
   (DSL-driven, Given/When/Then, **no mocks, no test doubles of our own
   code**). It must compile and fail for the right reason (behaviour
   absent, not setup error). Run it and show the output.
4. Create `.bdd/session.yml`:
   `mode: GREENFIELD`, `phase: decompose`, `acceptance_test.status: red`,
   branch fields set, empty collaborator list.
5. Commit on feature-tmp: `test: failing acceptance test — <slice>`
6. Announce: `🔴 AT: <behaviour>` and tell the user the next command is
   `/decompose`.

## Rules

- Never write production code in this command.
- Never invent collaborators here — that is /decompose's job.
- If the user cannot state the behaviour in one sentence, the slice is too
  big. Help them cut it thinner before writing anything.
