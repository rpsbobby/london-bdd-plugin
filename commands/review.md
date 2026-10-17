---
name: review
description: Slice-level review gate — reviewer agent audits the whole slice diff, clean code pass, distil-candidate triage, then close the outer loop. Runs when the collaborator queue is empty.
---

# /review — Close the Slice Properly

## Preconditions

`.bdd/session.yml`: `phase: close`, all collaborators and tests `done`,
on feature/<slice>-tmp.

## Steps

1. **Wire the composition root.** Real implementations composed at the
   boundary; no test doubles leak into production wiring.
2. **Run the outer net.**
   - GREENFIELD: acceptance test → expect `🟢 AT`. Still red → treat as a
     new inner-loop entry point (missing wiring is the usual cause);
     re-open `phase: inner` with the discovered collaborator.
   - SAFE/FULL_REFACTOR: re-run the declared net (`net.suites` in
     session.yml). For a characterisation net, that's `/characterise` in
     verification mode; for `net.kind: existing`, just run the declared
     suites and show the output. Either way: green = behaviour preserved;
     red = STOP and present the diff to the user — intended change or
     regression is never the agent's call alone.
3. **Slice review.** Slice-level concerns: duplication across cycles,
   names drifting from the ubiquitous language, boundary rule violations,
   test suite coherence, anything implemented beyond what tests demand.
   - `inner: granular`: dispatch `london-bdd:reviewer` with the full
     slice diff (feature/<slice>-tmp vs base).
   - `inner: batch`: you (the driver) already reviewed each builder round
     in `/inner`. Apply the findings accepted there, from
     `.bdd/review-<slice>.md`, then run `agents/reviewer.md`'s checklist
     over the full slice diff for anything that only shows across rounds.
   Present proposals; apply accepted ones; keep everything green.
4. **AT discovery: one automatic pass.** Run the AT half of
   `references/test-discovery.md` over the finished slice. Every
   candidate is a follow-up: this slice's scope closed at `/inner`. Then
   ask the user, and don't decide yourself: write the approved
   candidates to `docs/backlog.md`, run discovery again, or drop them.
   Never start a second pass unasked.
5. **Distil triage.** Walk `net.distil_candidates` (characterisation nets
   only; an existing-suite net has none): for each, decide with the user —
   rewrite now as a proper unit/acceptance test (then delete the ugly
   one), or log to `/debt` with the insight gained. The characterisation
   suite should shrink over time.
6. **Reflection (from the skill):** any awkward mock (design smell)?
   duplicated setup? happy AND sad path covered?
7. Final commit on feature/<slice>-tmp. Set `phase: done`.
8. Tell the user: the slice is closed, next command is `/commit-merge` to
   land it on feature/<slice>-main (manual by default, `--auto` to let the
   agent run the squash-merge itself). This step is identical in batch and
   granular mode. `inner` never reaches the merge.
