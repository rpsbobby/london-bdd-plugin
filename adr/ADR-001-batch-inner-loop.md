# ADR-001 — Batch inner loop with driver review and test discovery
**Status:** Accepted
**Date:** 2026-10

## Context
The inner loop runs four agent steps around every single unit test: red in
the main session, green in a Haiku implementer (or Codex), a Sonnet
reviewer, then a commit. A slice of N tests costs N+1 reviews, and in
`assisted` mode a human checkpoint at each step. That is too granular for a
human to follow and too slow for most slices; the control it offers is
rarely needed. Separately, nothing in the loop asks "what behaviour is still
untested?" — decompose's queue is the only source of tests, so corner cases
and implied behaviour surface only if someone happens to notice them.

## Decision
`session.yml` gains `inner: batch | granular` (absent = `batch`), replacing
`autonomy`. In **batch** mode the driver (main session, Opus) runs
`/decompose`, which produces collaborators *and* a planned `tests:` list; the
human approves the whole map once. `/inner` hands the list to one Sonnet
`builder` subagent, which works it red → green → refactor → commit per test
(no separate implementer, no per-cycle reviewer), then runs **discovery**:
it *proposes*, never builds, uncovered behaviour in both directions — UT
candidates (corner cases of existing collaborators) and AT candidates
(new scenarios / sad paths) when it has the context to see them. The driver
reviews the diff and the proposals with the human. Approved UTs go back to
the builder for exactly one more round, which does not discover again. AT
candidates for *this* slice need human approval (they change its scope);
candidates belonging to another slice are written to `docs/backlog.md`
without blocking, to be picked up by a later `/scenario`. `/review` keeps
one automatic AT-discovery pass before `/commit-merge`; further rounds only
when the human asks. **Granular** mode keeps today's human-paced per-test
flow with the Haiku implementer and Sonnet reviewer. The pluggable
implementer backend (`implementer.backend`/`model`, Codex) and the
autonomous `runner` agent are retired.

## Consequences
Easier: one approval, one build, one review per slice in the common case;
missing tests are actively searched for; the review that matters is done by
the strongest model with the human present. Harder: a review covers a larger
diff, and a builder mistake can propagate across several tests before anyone
looks — mitigated by the guard (Rule A still demands a recorded failing test
per production edit) and per-test commits on the tmp branch. Accepted:
`session.yml` files from before this change that omit the field now run
batch, and get explicit guard `allow`s, instead of assisted prompting.

Rejected: keeping `autonomy` alongside `inner` (two knobs for one choice);
per-collaborator discovery (needs a review point that doesn't exist);
letting discovery build small tests unasked (less control for little time
saved); keeping Codex as a GREEN delegate in batch (reintroduces per-test
hand-offs).
