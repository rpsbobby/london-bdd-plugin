---
name: design
description: Optional, before /scenario — talk through the high-level decisions a greenfield slice needs first (naming, test environment, where things live, technology choices) and record decisions and open questions in .bdd/design-<slice>.md, so /scenario starts from an agreed design. No code, no tests, no Gherkin.
---

# /design — Agree the Ground Before the Slice (optional)

Some slices need decisions before anyone can say what the behaviour is:
what runs are called, which test environment the outer net runs in
(envtest, kind or k3s), where the CRDs live. `/scenario` starts at
"behaviour in one sentence", so those talks have no home there and leave
no record. `/design` gives them one: a short file of decisions and open
questions that `/scenario` reads first and that is archived with the
slice.

It is optional. Skip it when the slice is a plain behaviour on known
ground. Read the `london-bdd` skill and `references/design-template.md`.

## Preconditions

1. `.bdd/session.yml`: no active slice, or the active one is `done`.
   Otherwise STOP: say which slice and phase is active and which command
   is expected next. Design the next slice once this one lands.
2. No git requirements. `/design` creates no branch and makes no commit:
   the file stays untracked until `/scenario` commits it on
   `feature/<slice>-tmp`. If the previous slice is `done` but not landed
   yet, `/commit-merge` leaves this file in place.

## Steps

1. **Name the slice.** Agree a working kebab-case slice name (`/scenario`
   reuses it; if it changes there, the file is renamed). If
   `.bdd/design-<slice>.md` already exists, read it and carry on from its
   open questions rather than starting over.
2. **Intent.** In a few sentences: what we are about to build and why.
   This is not yet the one-sentence behaviour; `/scenario` sharpens it.
3. **List the topics.** Ask what has to be settled before the scenario
   can be written, and propose topics from what you see in the repo. Good
   topics sit around the slice:
   - names the domain will use (run naming, identifiers, resource names)
   - external boundaries and what the outer net doubles or runs for real
   - the test environment for the outer net (envtest vs kind vs k3s,
     testcontainers, a fake server)
   - where artefacts live (CRD placement, packages, modules, config)
   - technology choices the slice can't start without
   Not topics: collaborators, roles, interfaces, class structure. Those
   are discovered outside-in at `/decompose`; settling them here would
   invent them.
4. **Work the topics one at a time.** For each: lay out the options with
   their trade-offs, recommend one, and let the user decide. Record it as
   a decision (what, why, rejected alternatives in a line each) or, if it
   can't be settled now, as an open question (what would settle it, and
   whether it blocks `/scenario`).
5. **ADR check.** A decision that will outlive the slice (a naming
   scheme, a test environment the whole repo will use) belongs in an ADR
   too. The design file does land with the slice, as
   `docs/slices/<slice>/design.md`, but as that slice's record: nobody
   looks there for a repo-wide rule. Offer `/adr` for each one and note
   the ADR number in the decision. Slice-only decisions stay in the file.
6. **Write `.bdd/design-<slice>.md`** in the template's shape, with
   `Status: agreed` if no blocking question is open, otherwise
   `Status: open`. Show it to the user and apply their edits.
7. Tell the user the next command is `/scenario`, which reads this file
   in Phase 0. `/decompose` builds the map within its decisions, and
   `/review` checks the finished slice against them. If blocking questions are open, say they must be settled
   (or explicitly deferred) there before the Gherkin is written; the user
   can also come back to `/design` once they have the answers.

## Rules

- No production code, no tests, no Gherkin, no branches, no commits.
- Decisions, not designs: no class diagrams, no interfaces, no
  collaborator names. Design inside the slice emerges from the loop.
- One page. If the file grows past that, the slice is too big or the
  talk has drifted into implementation: cut it, or move the extra to a
  later slice's design.
- Greenfield only. Refactor slices start with `/refactor-scope`, which
  declares scope and never solution.
