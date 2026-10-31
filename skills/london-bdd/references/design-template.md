# Design Notes — Template

Written by `/design` to `.bdd/design-<slice>.md`, before `/scenario`.
Decisions and open questions around the slice, never the design inside
it: no collaborators, roles or interfaces (those are `/decompose`'s).
The file is untracked until `/scenario` commits it on
`feature/<slice>-tmp`. `/commit-merge` copies it to
`docs/slices/<slice>/design.md` in the landing commit on
`feature/<slice>-main`, so it outlives the disposable tmp branch.
Decisions that must outlive the slice go to an ADR as well.

```markdown
# Design — <slice name>
**Date:** <yyyy-mm-dd>
**Status:** open | agreed     # agreed = no blocking question left

## Intent
<what we are about to build and why, 2–4 sentences. /scenario turns
this into the one-sentence behaviour.>

## Decisions
- **D1 — Runs are named `<pipeline>-<n>`.** Why: <reason>.
  Rejected: UUIDs (unreadable in kubectl), timestamps (collide).
- **D2 — The outer net runs against envtest.** Why: <reason>.
  Rejected: kind (slow to start in CI), k3s (no gain over kind here).
  ADR-004.
- **D3 — CRDs live in `config/crd/`, generated from `api/v1`.** Why: …

## Open questions
- **Q1 — Do runs need a TTL?** Settled by: <who/what>.
  Blocks /scenario: no — later slice.
- **Q2 — <question>** Settled by: … Blocks /scenario: yes.

## Out of scope
- <what this slice deliberately won't decide or build>
```

Rules of thumb:
- One line of why per decision, one line per rejected alternative. If a
  decision needs more, it's an ADR.
- An open question marked "blocks /scenario: yes" is settled or
  explicitly deferred in `/scenario`'s Phase 0, and the file is updated
  either way before the Gherkin is written.
- `/scenario` and `/decompose` treat the decisions as agreed: they
  don't reopen them unless the user does, or the work shows one was
  wrong. Then the change goes into this file, with why.
- `/review` checks the finished slice against every decision. A drift
  is fixed in the code, or the decision is updated here (and its ADR
  superseded); the user picks which.
