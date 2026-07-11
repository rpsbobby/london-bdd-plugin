---
name: decompose
description: Break the slice into collaborators — name roles in DDD language, sketch interface boundaries, agree the sequence before any code. Runs between the outer red and the inner loop.
---

# /decompose — Discover Collaborators, Name Roles

Read the `london-bdd` skill and `references/collaborator-discovery.md`.

## Preconditions

1. `.bdd/session.yml`: `phase: decompose`, outer net red (AT) or green
   (characterisation), on feature-tmp.

## Steps

1. Starting from the entry point, ask per responsibility: *what does this
   object need to ask for or tell?* Name each discovered role by
   **capability, not implementation** (`OrderRepository`, not
   `SqliteOrderStore`), in the project's ubiquitous language.
2. **Confirm every role name with the user** before recording it. Names
   are design decisions — they are the user's to make.
3. Sketch the minimal interface per role: only the methods actually
   called, starting with one.
4. Sanity checks (from the skill): >3–4 collaborators on one class →
   challenge; chain deeper than 3 levels → slice thinner.
5. Order the queue outside-in (entry point first) and write it to
   `collaborators:` in session.yml, all `status: pending`.
   Set `phase: inner`.
6. Commit: `docs: collaborator map — <slice>` (the map goes in
   `.bdd/scope-<slice>.md` or the session file — no production code).
7. Tell the user: next command is `/inner`, which will work the queue one
   collaborator at a time.

## Rules

- No production code, no interfaces committed as code yet — the inner loop
  drives them into existence. This is a map, not a skeleton.
- In FULL_REFACTOR mode, the map must respect the Clean Architecture
  boundary rule in the skill (UI knows nothing of domain; domain depends
  on nothing).
