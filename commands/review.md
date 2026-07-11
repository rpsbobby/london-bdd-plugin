---
name: review
description: Slice-level review gate — reviewer agent audits the whole slice diff, clean code pass, distil-candidate triage, then close the outer loop. Runs when the collaborator queue is empty.
---

# /review — Close the Slice Properly

## Preconditions

`.bdd/session.yml`: `phase: close`, all collaborators `done`, on
feature-tmp.

## Steps

1. **Wire the composition root.** Real implementations composed at the
   boundary; no test doubles leak into production wiring.
2. **Run the outer net.**
   - GREENFIELD: acceptance test → expect `🟢 AT`. Still red → treat as a
     new inner-loop entry point (missing wiring is the usual cause);
     re-open `phase: inner` with the discovered collaborator.
   - SAFE/FULL_REFACTOR: run `/characterise` in verification mode.
3. **Dispatch `london-bdd:reviewer`** with the full slice diff
   (feature-tmp vs base). Slice-level concerns: duplication across cycles,
   names drifting from the ubiquitous language, boundary rule violations,
   test suite coherence, anything implemented beyond what tests demand.
   Present proposals; apply accepted ones; keep everything green.
4. **Distil triage.** Walk `characterisation.distil_candidates`: for each,
   decide with the user — rewrite now as a proper unit/acceptance test
   (then delete the ugly one), or log to `/debt` with the insight gained.
   The characterisation suite should shrink over time.
5. **Reflection (from the skill):** any awkward mock (design smell)?
   duplicated setup? happy AND sad path covered?
6. Final commit on feature-tmp. Set `phase: done`.
7. **Hand back to the human:** present the squash-merge summary
   (cycles, files, behaviours) and the suggested squash message. The
   developer performs the squash onto feature-main themselves. Remind:
   `.bdd/session.yml` and scope artifacts stay out of the squash.
