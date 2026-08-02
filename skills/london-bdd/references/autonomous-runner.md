# The Autonomous Runner — `/inner`'s unattended execution mechanism

`autonomy: autonomous` means the inner loop drives itself: no pause at
`/unit`'s behaviour pick, none at the reviewer's `should`/`consider`
proposals, none between cycles. Someone still has to actually run that
loop. In `assisted` mode it's the main session, pausing for the user at
every step. In `autonomous` mode it's the `london-bdd:runner` subagent —
`/inner` dispatches it once, it drains the whole remaining collaborator
queue, and it reports back exactly once.

## Why a subagent, not the main session looping in place

Before this, `autonomy: autonomous` had `/inner` loop back to its own step
1 "in the same turn" for every remaining collaborator. That worked, but it
meant the *entire* queue's diffs, reviewer critiques, and implementer
reports all accumulated in one continuous main-session turn — the
harness's between-turn compaction never got a chance to run until the
whole queue finished.

Nothing in this workflow's state lives in conversation memory —
`.bdd/session.yml` is the sole source of truth, and `scripts/guard.py` /
`scripts/next.py` are both agent-agnostic (they key off session.yml + git
state + the tool-call payload, never "who called this"). That combination
makes it safe to move the drain into an isolated subagent: it picks up
correctly with zero inherited context, and the hooks enforce it identically
to the main session. Only a short report crosses back to the main session's
own transcript, not every cycle's full content.

## Why nested dispatch, not one inline model

The runner's own job (RED + orchestration) still needs Sonnet-level
judgment to replicate what `assisted` mode does at main-session level —
picking the next behaviour, naming things against the ubiquitous language,
deciding whether a refactor proposal is safe to apply unattended. GREEN and
REVIEW, though, are already scoped, single-purpose agents with their own
model routing (`implementer`: Haiku, minimum code, no test edits;
`reviewer`: Sonnet, read-only critique). The runner nest-dispatches both
per cycle rather than doing their work itself — this was a deliberate
choice, considered against collapsing everything into one model, and
rejected specifically to preserve today's cost profile and the reviewer's
independence from the code it's critiquing.

## The contract

**In:** repo root, slice name, `.bdd/session.yml` path — the same inputs
`/inner` already has. Nothing about prior conversation; the runner reads
everything else itself.

**Out:** one commit per completed cycle on `feature/<slice>-tmp`, exactly
as `assisted` mode produces, plus exactly one final report — completed or
escalated (shape below).

**Absolute rules:**
1. Never write a second failing test while one is already open — check
   `current_failing_test` on entry before deciding whether to resume at
   GREEN or start fresh at RED.
2. Never apply a fix to a `block`-severity reviewer finding — escalate.
3. Never retry a GREEN-step backend blindly, never widen its context to
   help it pass.
4. Never merge, never push, never touch `feature/*-main`.
5. Never end a turn without producing the completed/escalated report — an
   incomplete cycle with no report is strictly worse than an honest early
   stop.
6. Never let the turn budget run out mid-write — the soft guard (stop
   before starting a new cycle if fewer than ~15 turns remain) exists
   specifically so `session.yml` is never left in a state nothing
   describes.

## Report shape

```
## Autonomous run report — <slice>

**Outcome:** completed | escalated

**Cycles run this dispatch:**
1. <role> — <behaviour> — commit <sha> — <one-line summary>
...

<completed>
Collaborator queue is empty. `phase` set to `close`. Next command: /review.

<escalated>
**Escalated at cycle <n+1>, collaborator `<role>`, step <RED|GREEN|REVIEW|COMMIT>.**
**Trigger:** implementer-stayed-red | codex-protocol-error | codex-violation |
            reviewer-block | hook-rejection | git-state-unexpected | turn-budget
**What happened:** <verbatim test failure / reviewer's exact block line /
  hook's exact stderr — never summarized away>
**session.yml state right now:** phase `<phase>`, current_failing_test
  `<file:name|none>`, `<role>` status `<status>`, cycle `<n>`.
**Queue remaining:** <ordered role/status list>
**Recommended next step:** <concrete>
```

The key design point: **escalation needs no new session.yml choreography.**
Every step of the runner's cycle (RED, GREEN, COMMIT) already writes at the
same checkpoints `assisted` mode uses between its own user-paused steps —
escalating just means the runner stops before its next natural write. The
on-disk state left behind is exactly the shape a human-paused `assisted`
cycle already produces, which `scripts/next.py` already interprets
correctly (e.g. "`<role>` has a recorded failing test — continue the
cycle"). The report's only new job is carrying the *why* — the test output,
the reviewer's exact finding, the hook's exact message — since the
dispatching session witnessed none of the runner's internal turns and
can't reconstruct it from a git diff the way `/review` reconstructs an
autonomous run's design decisions.

## Resuming after an escalation

Re-running `/inner` simply re-dispatches the runner. Its own resume-safety
check (a non-empty `current_failing_test` on entry means this dispatch is
a resume, not a fresh start) picks the cycle back up at the right step —
no separate resume flag or session.yml field is needed.

## Operational note — verify nested dispatch empirically before relying on it

The runner's whole design assumes a dispatched subagent can itself dispatch
a further subagent (`runner` → `implementer`/`reviewer`). This was not
something any existing file in this repo documented one way or the other
when the runner was added, and it could not be verified from inside the
authoring session — that session's plugin install was a cached copy
(`~/.claude/plugins/cache/<marketplace>/london-bdd/<version>/`) pinned to a
specific commit, not a live pointer to the working repo, so newly-added
agent files never became visible no matter how many times `/reload-plugins`
ran. If you're standing this up for real: install the plugin from a
local-path pointed directly at this working copy (see README's Install
section), confirm a trivial nested-dispatch probe works end to end, and
only then trust `autonomy: autonomous` in production. If nesting turns out
not to be supported by your harness version, this design needs revisiting
— do not silently collapse `runner` into doing GREEN/REVIEW itself; that
was a deliberately rejected alternative (see above), not a safe fallback to
reach for quietly.

## Adding to / changing this contract

`commands/inner.md` steps 1-4 describe the identical algorithm for
`assisted` mode; `agents/runner.md` restates it in full for its own
self-contained context (subagents can't invoke slash commands). The two
must be kept in sync by hand — each file carries a comment pointing at the
other. If the RED/GREEN/REVIEW/COMMIT algorithm itself changes, update
both; if only the unattended-execution mechanics change (report shape,
escalation triggers, turn budget), this file and `agents/runner.md` are
the only two that need touching.
