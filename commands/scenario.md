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

Work through these WITH the user. Points 0 and 1 are independent
decisions: settle each one on its own, in order. Points 2–5 hang
together, so once the behaviour sentence is agreed, propose all four in
one message for a single confirmation (the user can still edit any of
them). Split them back out only when one is genuinely open, e.g. a new
term the glossary doesn't settle.

0. **Backlog first.** If `docs/backlog.md` exists, show its entries:
   AT candidates earlier slices discovered. The user may pick one as this
   slice, or start something new.
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
   - `feature/<slice>-main` from the current branch
   - `feature/<slice>-tmp` from feature/<slice>-main
   - Check out `feature/<slice>-tmp`.
3. Write the failing acceptance test using the `/acceptance` shape
   (DSL-driven, Given/When/Then, **no mocks, no test doubles of our own
   code**). It must compile and fail for the right reason (behaviour
   absent, not setup error). Run it and show the output.
4. **Ask the inner-loop question:** "Build the approved test list in
   `batch` (one builder agent builds it all, then you and I review the
   result and its discovery proposals: default), or `granular` (one test
   per `/inner` call, pausing for you at each step)?" Default to `batch`
   on no answer. Either way you approve the test list at `/decompose`
   first, and this command, `/review`, and `/commit-merge` stay
   human-paced.
5. **Ask the checks question:** "Which command runs the tests in scope
   on every commit? `{files}` becomes the test files this slice touches."
   Suggest one from the repo's tooling (`uv run pytest {files}`,
   `npx vitest run {files}`, `go test ./...`). Record it as
   `checks.tests`. If the repo has a `.pre-commit-config.yaml`, check
   its hook is installed (`pre-commit install` if not): the guard blocks
   commits otherwise.
6. Create `.bdd/session.yml` with the helper, from the answers above (do
   not hand-write it; it validates the result with the guard's parser):
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/session.py init \
     --slice <slice> --mode GREENFIELD --inner <batch|granular> \
     --checks-tests "<checks command>" \
     --acceptance-file <test file> --acceptance-name "<test name>"
   ```
   This writes `phase: decompose`, `acceptance_test.status: red`, the
   branch fields (`feature/<slice>-tmp`, base `feature/<slice>-main`),
   `cycle: 0` and an empty collaborator list. It refuses to overwrite an
   existing file; archive a finished slice first (precondition 1).
7. Commit on feature/<slice>-tmp: `test: failing acceptance test — <slice>`
   (if the slice came from `docs/backlog.md`, remove that entry in the
   same commit).
8. Announce: `🔴 AT: <behaviour>` and tell the user the next command is
   `/decompose`.

## Rules

- Never write production code in this command.
- Never invent collaborators here — that is /decompose's job.
- If the user cannot state the behaviour in one sentence, the slice is too
  big. Help them cut it thinner before writing anything.
