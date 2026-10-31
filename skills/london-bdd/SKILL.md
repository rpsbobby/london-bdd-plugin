---
name: london-bdd
description: >
  Governs the London School (mockist/outside-in) BDD double loop and the
  characterisation-first legacy refactoring workflow. Use whenever the user
  invokes any london-bdd command, mentions BDD, outside-in TDD, ATDD, the
  double loop, mockist TDD, characterisation tests, or safe refactoring of
  legacy code. This skill is the knowledge layer; the plugin's commands are
  the workflow entry points; the agents and hooks enforce it.
---

# London School BDD — Double Loop (Plugin Knowledge Layer)

## Mental model

```
╔══════════════════════════════════════════╗
║  OUTER LOOP — the net                    ║
║   greenfield : failing acceptance test   ║
║   refactor   : green net — existing      ║
║                suite or characterisation ║
║        │                                 ║
║   ┌─────────────────────────────────┐    ║
║   │  INNER LOOP (per collaborator)  │    ║
║   │  🔴 failing unit test           │    ║
║   │  🟢 minimum impl (Haiku agent)  │    ║
║   │  🔵 review + refactor (Sonnet)  │    ║
║   │  ⏺ one commit per cycle        │    ║
║   └─────────────────────────────────┘    ║
║        │                                 ║
║   outer net green = slice done           ║
╚══════════════════════════════════════════╝
```

Same inner loop, different outer nets. That symmetry is the design.

## The two workflows

```
GREENFIELD                          SAFE / FULL_REFACTOR (existing code)
(/design    decisions, optional)
/scenario   discuss, Gherkin, 🔴AT   /refactor-scope  scope + declare net
/decompose  collaborators, roles     /characterise    ONLY if net gap
/inner ×N   cycle per collaborator   (/decompose if FULL_REFACTOR)
/review     slice gate, close loop   /inner ×N  →  /review
                                     net re-run (verify: still green)
/commit-merge   land the slice (both workflows, once phase: done)
```

Every command ends by naming the next one — the loop always tells you
where to go.

`/design` is the optional step before `/scenario` for slices that need
ground settled first: naming, the outer net's test environment, where
artefacts live. It records decisions and open questions in
`.bdd/design-<slice>.md`, which `/scenario` reads in Phase 0 and commits
with the slice. It decides what sits around the slice, never the
collaborators inside it: those are still discovered at `/decompose`.

**The net is the license; characterisation is only one way to build it.**
Characterisation-first is a technique for *untested* code. Code already
covered by trusted behavioural tests (e.g. built through this very loop —
loosely coupled, outcome-asserting ATs) already HAS its net: the human
declares those suites the net at `/refactor-scope` (after a real green
run), `/characterise` is skipped, and refactoring proceeds green-to-green
on the existing suite. Forcing characterisation onto tested code pins
implementation behaviour — manufacturing exactly the coupling the outer
net exists to avoid. Characterisation is required only where coverage is
missing or untrusted, and only over that gap.

Mode is declared at slice start and recorded in `.bdd/session.yml`.
Switching modes mid-slice requires an explicit checkpoint with the user.

## Inner-loop modes — batch by default

`/decompose` proposes the collaborators and the unit tests that drive
them, and the human approves that map once. `/inner` then works the list
in one of two modes, set as `inner:` in `.bdd/session.yml` at slice start:

- **batch** (default): one Sonnet `builder` subagent builds every test
  unattended (red → green → refactor → commit per test), then proposes
  what's still untested: UT corner cases and, when it has the context, AT
  scenarios. The driver (main session) reviews the diff and the proposals
  with the human. Approved UTs get exactly one more build round, with no
  further discovery.
- **granular**: the human-paced cycle, one test per `/inner` call, with
  the Haiku `implementer` and the Sonnet `reviewer` each cycle.

Discovery only proposes and the human approves every test that enters
the list. AT candidates for this slice need approval, and candidates for
other slices go to `docs/backlog.md`. `/review` runs one more automatic
AT-discovery pass before the merge, then asks. See
`references/test-discovery.md`. The outer red, `/review`, and
`/commit-merge` are human-paced in both modes.

## Core principles (Freeman & Pryce)

- Design emerges **outside-in** — start with behaviour, not data.
- Collaborators are **discovered, not invented**. Introduce an interface
  when a class needs a helper; mock it in the unit test.
- Each inner-loop cycle drives exactly one behaviour of one collaborator.

## The doubling principle (scale-invariant)

**Double at the boundary of the thing under test; keep real what lives
inside it.** This one rule governs every level — only the *radius* of "the
thing under test" changes:

```
Acceptance : unit-under-test = the slice
             double  → outside the slice (external boundaries: gateway,
                       clock, backend across the wire, hardware)
             real    → every collaborator inside the slice you own

Unit       : unit-under-test = one class + the behaviour it OWNS
             double  → its peers (roles it delegates to / talks to)
             real    → the class itself, and value objects, pure functions,
                       and in-process calculations it owns
```

The discriminator is **peer vs internal**, not "is it a separate class":

- **Talks to** — I/O, external service, another aggregate, anything with
  its own lifecycle or identity → it's a *peer/role* → **double it**.
- **Owns** — a value object, a pure function, a calculation extracted only
  for readability → it's an *internal* → **keep it real**. Doubling it
  tests the wrapping and asserts nothing.

Freeman & Pryce's actual position is "mock **roles**, not objects": an
extracted pure function is not a role, it's an internal. The smell, at
either level, is **anything doubled that the unit-under-test actually
owns** — a faked domain object in an acceptance test, or a mocked value
object in a unit test, are the same mistake at different radii.

- Mocks verify **interactions** (messages sent to peers); prefer outcome
  assertions where they suffice.

## The three test suites — distinct shapes on purpose

| Suite | Shape | Command |
|---|---|---|
| **Acceptance** | DSL Given/When/Then, business language; doubles external boundaries deliberately (to identify dependencies), internal collaborators stay real; external outcomes only. Executable identifier is `should_`-prefixed (see naming convention below). | `/acceptance` |
| **Unit** | Behaviour-named, `should_`-prefixed, one behaviour, body ≤ ~10 lines. Double **peers** (roles the class delegates to); keep **owned** behaviour real (value objects, pure functions). See the doubling principle. | `/unit` |
| **Characterisation** | Records CURRENT behaviour. No DSL forced, no naming convention imposed. **Correctness over readability — ugliness is a signal**, and every eyesore is a distil candidate for later rewrite as a proper unit/acceptance test. The suite is designed to shrink. | `/characterise` |

## Test naming convention

Every acceptance and unit test name states the expected behaviour and
starts with **`should`**:

- Frameworks with no discovery prefix (Vitest/Jest `it()`, RSpec, Kotlin
  backtick names): `should <behaviour>` — e.g. `it('should return 201 …')`.
- Frameworks that require a `test_`/`Test` discovery prefix (pytest, Go's
  `testing` package, JUnit method names): `test_should_<behaviour>` /
  `TestShould<Behaviour>` — e.g. `def test_should_place_order(...)`.

Gherkin `Scenario:` titles stay pure business language — this convention
governs the executable identifier wrapping the scenario, not the DSL text.
Characterisation tests are exempt (see table above) — they record what IS,
not what should be.

## Model routing (enforced by agent definitions)

```
Outer loop, decomposition, review, discovery triage →  main session (driver) + user
Build the test list (inner: batch)                  →  builder agent (Sonnet): red, green,
                                                         refactor, commit per test,
                                                         then discovery proposals
Minimum implementation (inner: granular)            →  implementer agent (Haiku)
Design critique (inner: granular)                   →  reviewer agent (Sonnet, read-only)
```

The human approves every role name and every test that enters the list,
at `/decompose` and at discovery triage. In granular mode the implementer
gets one failing test and the interfaces it references, nothing else.

## Branching discipline

```
feature/<slice>-main  human history — landed via /commit-merge
feature/<slice>-tmp   agent workspace — two commits per test: at green
                      (test + impl) and after refactor; each runs the
                      repo hooks + tests in scope (Rule E); disposable
```

Never commit on feature/<slice>-main. Never auto-stash. Wrong branch = stop
and ask. Merging tmp onto main happens only through `/commit-merge`: manual
by default (prints the commands, developer runs them), or `--auto` where
the agent runs the squash-merge itself, authorized fresh every invocation
— never a persisted "always auto". The guard hook enforces all of this;
commands check first anyway — commands are polite, hooks are absolute.

## The five hard rules (hook-enforced)

- **A.** A production edit requires a license — any one of: a recorded
  failing test in `.bdd/session.yml` (the normal red); phase `close`
  (composition-root wiring); or SAFE mode with a **green net**
  (refactoring moves are green-to-green; the net is the license). The
  net's kind — declared existing suite or characterisation — is recorded
  in session.yml by the human; the hook checks status, not kind.
- **B.** In SAFE/FULL_REFACTOR, no edit outside the declared scope.
  "While we're here" → extend scope explicitly or `/debt`.
- **C.** Agent commits only on `feature/*-tmp`. Merges onto
  `feature/*-main` are human by default, or agent-run via
  `/commit-merge --auto` with fresh per-run authorization. Rebases are
  always human.
- **D.** Phase transitions in `.bdd/session.yml` are forward-only and
  earned, not self-reported: entering `inner` requires the outer net to
  exist (AT red / net green) and, for GREENFIELD, a
  non-empty collaborator queue and test list; entering `close` requires
  every collaborator and every test `done`; entering `done` requires coming from `close`. The
  guard hook validates the target phase on every edit to session.yml, so
  a step can't be skipped just by writing the field.
- **E.** Every agent commit in a slice runs the checks. The repo's own git
  hooks can't be skipped (`--no-verify`, `-n`, `core.hooksPath`, `SKIP=`),
  a `.pre-commit-config.yaml` must have its hook installed, and the tests
  in the slice's scope must pass: test files the slice touched, the
  acceptance test from `close` on, and a SAFE net's suites, run through
  session.yml's `checks.tests` command. Commit often, at green and after
  refactor, so the checks run on small diffs.

## Operating rules

1. Show the traffic light (🔴/🟢/🔵) before each action.
2. One failing test at a time — never two reds open.
3. Never mock types you don't own — wrap first.
4. Role names and the test list are approved by the user at `/decompose`,
   before any interface is introduced.
5. Run tests after every change; show real output.
6. Session state lives in `.bdd/session.yml` (see
   `references/session-schema.md`) — read first, update last, trust it
   over memory. Unsure what's next? Run `/status` (`scripts/next.py`) —
   it's a deterministic lookup, not something to re-derive by exploring
   the repo.
7. Deviations requested by the user are honoured but noted, with why the
   step matters.
8. Batch mode never overrides an escalation trigger: a `block`-severity
   finding, a test that stays red after honest attempts, a design
   question the map didn't answer, or a hook rejection (Rules A–E) all
   stop the loop and hand back to the human.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Fragile/slow AT | Testing implementation detail | Assert external outcome only |
| Own objects doubled in outer net | Contaminated outer loop | Real internal collaborators; double only external boundaries |
| Inner loop never closes | Chain too deep | Slice thinner (see collaborator-discovery) |
| Units green, AT red | Wiring/composition root | Treat as new inner-loop entry |
| Implementer gold-plating | Context beyond the test leaked | Pass only test + interfaces |
| Characterisation "cleanup" urge | Misreading ugliness as defect | It's a distil signal — flag, don't beautify |

## Reference files

- `/status` — deterministic "what's next" lookup (`scripts/next.py`);
  run it anytime instead of re-deriving state from the repo
- `references/session-schema.md` — the state file all commands share
- `references/design-template.md` — the optional pre-slice design notes
- `references/scope-template.md` — the refactor scope artifact
- `references/characterisation.md` — Feathers techniques and probe-first
- `references/approval-testing.md` — golden-master/approval testing and
  which library to reach for per language
- `references/collaborator-discovery.md` — role heuristics and naming
- `references/decompose-map-template.md` — the shape of the map /decompose
  presents for approval
- `references/test-discovery.md` — what discovery looks for, UT vs AT
  sizing, the proposal format, and how approved proposals are recorded
- `references/language-notes.md` — general per-language tooling
- `references/qt-cpp-notes.md` — Qt/C++ specifics (stub, distil from use)
- `references/python-notes.md` — Python specifics (stub, distil from use)
- `references/example-slice.md` — worked greenfield example
