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
   - If the previous slice is `done`: move it to `.bdd/archive/<slice>.yml`
     (move, not copy: no session.yml may remain before step 6 of Phase 1),
     and its `.bdd/design-<slice>.md`, if any, to
     `.bdd/archive/design-<slice>.md`.
2. Check git state: must be clean. Never auto-stash. One exception: an
   untracked `.bdd/design-<slice>.md` written by `/design` for this
   slice. It stays untracked until the Phase 1 commit.

## Phase 0 — Discuss (do not skip, do not rush)

Work through these WITH the user. Points 0 and 1 are independent
decisions: settle each one on its own, in order. Points 2–6 hang
together, so once the behaviour sentence is agreed, propose them all in
one message for a single confirmation (the user can still edit any of
them). Split them back out only when one is genuinely open, e.g. a new
term the glossary doesn't settle.

0. **Design notes, then backlog.** If `/design` left a
   `.bdd/design-<slice>.md`, this slice is that one: read it, take its
   slice name, and summarise its decisions and open questions in a few
   lines. The decisions are agreed: build on them, don't reopen them
   unless the user does or the behaviour talk shows one was wrong (then
   update the file, with why). Settle each open question marked as
   blocking `/scenario` now, or have the user defer it explicitly, and
   update the file either way. If there is more than one design file,
   ask which slice this is. Otherwise, if `docs/backlog.md` exists, show
   its entries: AT candidates earlier slices discovered. The user may
   pick one as this slice, or start something new. Unsettled ground
   (naming, test environment, where things live) that stalls the
   behaviour talk is a sign to stop and run `/design` first.
1. **Behaviour in one sentence**, in business language. Push back on
   technical framing ("insert row" → "customer places an order").
2. **Ubiquitous language check** — do the nouns/verbs match the domain
   glossary and existing code? Flag any drift. New terms get agreed here.
3. **Entry point** and **observable outcome** — externally visible only.
4. **One meaningful sad path** to cover alongside the happy path.
5. **Clean architecture boundary** — which layer does the AT enter through?
   (Application layer preferred; UI entry only for smoke tests.) Take
   boundaries and the test environment from the design notes, if any.
6. **Outer net kind.** `dsl` (the default) is the DSL acceptance test
   above. Propose `contract` when the slice adds an adapter behind a port
   that already exists (a Kubernetes `RunStore` next to the in-memory
   one): the outer red is then the port's contract suite, run against
   every subject. It passes against the subjects that already exist (the
   fake, other adapters) and fails against the new one. Agree the
   subjects with the user.

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
   For a `contract` net, write (or extend) the port's contract suite so
   it runs once per subject, and add the new adapter as a subject. If the
   new adapter has to exist for the suite to compile, write its **empty
   stub**: the type, its constructor, and the port's methods, each
   failing with "not implemented" (or returning the zero value), in the
   adapter's real production file. No behaviour, no branches, no
   collaborators: `/inner` builds those under failing unit tests. Don't
   put a placeholder store in the test file instead. Show the run: green
   for the existing subjects, red for the new one, for "not implemented".
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
   For a `contract` net, add `--acceptance-kind contract`, one
   `--subject <name>` per subject (at least two: one already green, and
   the new one), and `--stub <path>` when step 3 wrote a stub.
   This writes `phase: decompose`, `acceptance_test.status: red`, the
   branch fields (`feature/<slice>-tmp`, base `feature/<slice>-main`),
   `cycle: 0` and an empty collaborator list. It refuses to overwrite an
   existing file; archive a finished slice first (precondition 1).
7. Commit on feature/<slice>-tmp: `test: failing acceptance test — <slice>`
   (a `contract` net's stub goes in this commit too, and so does
   `.bdd/design-<slice>.md` if `/design` wrote one)
   (if the slice came from `docs/backlog.md`, remove that entry in the
   same commit).
8. Announce: `🔴 AT: <behaviour>` and tell the user the next command is
   `/decompose`.

## Rules

- Never write production code in this command. The one exception is a
  `contract` net's empty stub (Phase 1 step 3): signatures only, every
  method "not implemented". It's written before session.yml exists, so
  the guard doesn't police it. Keep it empty: `/decompose` checks it
  before mapping.
- Never invent collaborators here — that is /decompose's job.
- If the user cannot state the behaviour in one sentence, the slice is too
  big. Help them cut it thinner before writing anything.
