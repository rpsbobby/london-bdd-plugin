---
name: acceptance
description: Write or extend a DSL-driven acceptance test (Given/When/Then, business language). The outer loop's red. Mocks external boundaries deliberately to identify dependencies; never mocks internal collaborators. Usually invoked via /scenario, directly when adding a sad path or new AT.
---

# /acceptance — The Outer Net

Read the `london-bdd` skill. Language tooling:
`references/language-notes.md` (+ `qt-cpp-notes.md` / `python-notes.md`).

## Shape — non-negotiable

- **DSL-driven.** Given/When/Then structure, readable by a non-developer.
  The test IS the executable specification.
- **Business language throughout.** Domain terms from the ubiquitous
  language; no HTTP verbs, SQL, or class names in scenario text.
- **Doubles at the boundary, deliberately — this is the point.** A feature
  always depends on something external (payment gateway, clock, external
  service, hardware, the backend across the wire). Faking or mocking those
  boundaries is how the acceptance test **discovers and pins down the
  slice's real dependencies**. Introduce each double consciously and name
  the port it stands for — the doubles you are forced to add ARE the
  outside-in discovery of your collaborators.
- **Everything inside the slice stays real.** Do NOT double your own
  domain/application collaborators — the whole point is verifying they
  work together. The line:
  ```
  double  → external boundaries (deliberately, to identify them)
  real    → everything inside the slice you own
  ```
  Prefer a fake/stub (controlled, passive) over an interaction mock unless
  the interaction itself is the observable behaviour (e.g. "the gateway
  was charged", "the notification was sent").
- **Asserts externally visible outcomes only** — response, persisted
  state, emitted event, or a deliberate interaction with a boundary double.
  Never internal calls or intermediate state of code you own.
- **Enters at the application layer boundary.** Qt/UI entry is for smoke
  tests, not acceptance.
- Happy path AND at least one meaningful sad path per behaviour. Sad path
  asserts a *meaningful* outcome (domain error), not a stack trace.

## Procedure

1. Check session.yml — active slice, on feature-tmp.
2. Draft the Gherkin (or DSL test names) first; confirm with the user.
3. Name the boundary doubles you expect to need and WHICH port each
   represents. Confirm with the user — these become collaborators in
   /decompose. Wrap third-party types before doubling them; never mock a
   third-party class directly.
4. Write the test. It must **compile and fail for the right reason** —
   run it and verify the failure is "behaviour absent", not a setup error.
5. Update `acceptance_test` in session.yml (`status: red`). Record the
   identified boundary ports so /decompose can seed the collaborator queue.
6. Commit: `test: failing acceptance test — <behaviour>`
7. Announce `🔴 AT: <behaviour>`.

## Rules

- Mocking an INTERNAL collaborator contaminates the outer loop — remove it,
  wire the real object. Mocking an EXTERNAL boundary is correct and
  intended.
- Every boundary double must correspond to a named port you own. If you
  can't name the port, you haven't found the boundary yet — discuss with
  the user.
- If the test needs to know an implementation detail to assert, the
  boundary is wrong; discuss before proceeding.
