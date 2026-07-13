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
║   refactor   : characterisation suite    ║
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
GREENFIELD                          SAFE / FULL_REFACTOR (legacy)
/scenario   discuss, Gherkin, 🔴AT   /refactor-scope  scope, NOT design
/decompose  collaborators, roles     /characterise    lock in what IS
/inner ×N   cycle per collaborator   (/decompose if FULL_REFACTOR)
/review     slice gate, close loop   /inner ×N  →  /review
                                     /characterise (verify: still green)
/commit-merge   land the slice (both workflows, once phase: done)
```

Every command ends by naming the next one — the loop always tells you
where to go.

Mode is declared at slice start and recorded in `.bdd/session.yml`.
Switching modes mid-slice requires an explicit checkpoint with the user.

## Core principles (Freeman & Pryce)

- Design emerges **outside-in** — start with behaviour, not data.
- Collaborators are **discovered, not invented**. Introduce an interface
  when a class needs a helper; mock it in the unit test.
- Each inner-loop cycle drives exactly one collaborator into existence.

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
Outer loop, decomposition, unit tests, review  →  main session (Sonnet/Opus) + user
Minimum implementation                          →  implementer agent (Haiku)
Design critique                                 →  reviewer agent (Sonnet, read-only)
```

The human writes/approves every test name and role name. The implementer
gets one failing test and the interfaces it references — nothing else.

## Branching discipline

```
feature/<slice>-main  human history — landed via /commit-merge
feature/<slice>-tmp   agent workspace — one commit per completed cycle
                      (test + impl + refactor together), disposable
```

Never commit on feature/<slice>-main. Never auto-stash. Wrong branch = stop
and ask. Merging tmp onto main happens only through `/commit-merge`: manual
by default (prints the commands, developer runs them), or `--auto` where
the agent runs the squash-merge itself, authorized fresh every invocation
— never a persisted "always auto". The guard hook enforces all of this;
commands check first anyway — commands are polite, hooks are absolute.

## The three hard rules (hook-enforced)

- **A.** A production edit requires a license — any one of: a recorded
  failing test in `.bdd/session.yml` (the normal red); phase `close`
  (composition-root wiring); or SAFE mode with a **green** characterisation
  net (refactoring moves are green-to-green; the net is the license).
- **B.** In SAFE/FULL_REFACTOR, no edit outside the declared scope.
  "While we're here" → extend scope explicitly or `/debt`.
- **C.** Agent commits only on `feature/*-tmp`. Merges onto
  `feature/*-main` are human by default, or agent-run via
  `/commit-merge --auto` with fresh per-run authorization. Rebases are
  always human.

## Operating rules

1. Show the traffic light (🔴/🟢/🔵) before each action.
2. One failing test at a time — never two reds open.
3. Never mock types you don't own — wrap first.
4. Confirm role names with the user before introducing an interface.
5. Run tests after every change; show real output.
6. Session state lives in `.bdd/session.yml` (see
   `references/session-schema.md`) — read first, update last, trust it
   over memory.
7. Deviations requested by the user are honoured but noted, with why the
   step matters.

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

- `references/session-schema.md` — the state file all commands share
- `references/scope-template.md` — the refactor scope artifact
- `references/characterisation.md` — Feathers techniques and probe-first
- `references/collaborator-discovery.md` — role heuristics and naming
- `references/language-notes.md` — general per-language tooling
- `references/qt-cpp-notes.md` — Qt/C++ specifics (stub, distil from use)
- `references/python-notes.md` — Python specifics (stub, distil from use)
- `references/example-slice.md` — worked greenfield example
