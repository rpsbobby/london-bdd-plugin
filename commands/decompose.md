---
name: decompose
description: Break the slice into collaborators and the tests that drive each one — name roles in DDD language, sketch interface boundaries, list the planned unit tests, agree the whole map with the user once before any code. Runs between the outer red and the inner loop.
---

# /decompose — Discover Collaborators, Plan the Tests

Read the `london-bdd` skill, `references/collaborator-discovery.md`, and
`references/decompose-map-template.md`.

## Preconditions

1. `.bdd/session.yml`: `phase: decompose`, outer net red (AT) or green
   (characterisation), on feature/<slice>-tmp.
2. `acceptance_test.kind: contract` with a `stub:`: read the stub. It
   holds signatures only, every method "not implemented". Anything more
   (a branch, a field, a call to a collaborator) is behaviour no test
   drove: show it to the user, and either give it a test in the map or
   have them empty the stub by hand (Rule A blocks the agent from editing
   production code before a failing unit test exists).

## Steps

1. Starting from the entry point, ask per responsibility: *what does this
   object need to ask for or tell?* Name each discovered role by
   **capability, not implementation** (`OrderRepository`, not
   `SqliteOrderStore`), in the project's ubiquitous language.
2. Sketch the minimal interface per role: only the methods actually
   called, starting with one.
3. Per role, list the unit tests that drive it, as `should_` names, one
   behaviour each, outside-in. Cover what the acceptance test needs, plus
   the obvious sad path per role. Don't chase every corner case:
   discovery at the end of the inner loop exists for that.
4. Sanity checks (from the skill): >3–4 collaborators on one class →
   challenge; chain deeper than 3 levels → slice thinner.
5. **Present the whole map as one message, in the shape of
   `references/decompose-map-template.md`:** entry point, roles table
   (role, kind, interface, doubled or kept real), tests in build order
   grouped by role, how the outer net turns green, things to settle with
   the sanity check result, and a closing "approve, or edit?". The user
   approves or edits it as one unit. Names are design decisions, so
   nothing is recorded until they approve. One approval, not one per
   role.
6. Write to session.yml: `collaborators:` ordered outside-in, all
   `status: pending`; `tests:` in build order, each with `name`,
   `collaborator`, `origin: planned`, `status: pending`;
   `discovery_rounds: 0`. Set `phase: inner`.
7. Commit: `docs: collaborator map — <slice>` (the map goes in
   `.bdd/scope-<slice>.md` or the session file, with no production code).
8. Tell the user the next command is `/inner`: in batch mode it builds
   the whole list, in granular mode one test per call.

## Rules

- No production code, no interfaces committed as code yet: the inner loop
  drives them into existence. This is a map, not a skeleton.
- In FULL_REFACTOR mode, the map must respect the Clean Architecture
  boundary rule in the skill (UI knows nothing of domain; domain depends
  on nothing).
