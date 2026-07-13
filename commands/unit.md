---
name: unit
description: Write one failing unit test for the current collaborator — behaviour-named, mocked collaborators, narrow scope, max ~10 lines. The inner loop's red. Usually invoked via /inner.
---

# /unit — The Inner Red

Read the `london-bdd` skill. Language tooling in references.

## Shape — non-negotiable

- **Behaviour-named, `should_`-prefixed**: `should_<behaviour>` (or
  `test_should_<behaviour>` / `TestShould<Behaviour>` where the framework
  requires a `test_`/`Test` discovery prefix — pytest, Go, JUnit method
  names). The name states what is broken and why it matters when it fails.
  Not DSL-forced — plain test code.
- **One behaviour per test.** Body target ≤ 10 lines. Over that → the
  behaviour is too big or setup should be extracted.
- **Double the peers, keep the owned behaviour real** (the doubling
  principle in the skill). Peers = roles this class *delegates to or talks
  to* (from the decompose map): I/O, external services, other aggregates.
  Double those. Value objects, pure functions, and calculations this class
  *owns* — use the real thing; doubling them tests the wrapping and
  asserts nothing. The discriminator is **peer vs internal**, not "is it a
  separate class". Assert on the message sent to a peer OR the returned
  value — interaction or outcome, never internals.
- Double only our own roles. Third-party types get wrapped first, then the
  wrapper is the role you double.
- The class under test should not exist yet, or only as a stub.
- **The sentence heuristic:** read the test body aloud. If it doesn't flow
  as a sentence, the interface is wrong — fix the design, not the test.

## Procedure

1. Check session.yml: `phase: inner`, a collaborator with
   `status: pending|red` at the head of the queue, on feature/<slice>-tmp,
   `current_failing_test` empty (one red at a time — never two).
2. Confirm with the user which behaviour of the collaborator this test
   drives.
3. Write the test. Run it; verify it fails for the right reason.
4. Set `current_failing_test` in session.yml (this unlocks production
   edits for the hook), collaborator `status: red`.
5. Announce `🔴 UT: <class> — <behaviour>`.
6. Hand back to `/inner` — its GREEN step (implementer agent) is next.

Do NOT commit here — the commit happens once per full cycle
(test + impl + refactor), handled by /inner.
