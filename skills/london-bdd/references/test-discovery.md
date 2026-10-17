# Test Discovery — What Is Still Untested?

Decompose's test list is a plan, not the whole truth. Building it teaches
you things the plan couldn't see. Discovery is the deliberate pass that
asks what behaviour the slice now has, or obviously should have, that no
test pins down. It **proposes**. It never writes a test or production code.

Who runs it, and when:

| Where | Who | Scope | Automatic rounds |
|---|---|---|---|
| `/inner` batch, end of round 1 | `builder` subagent | UT + AT | one; round 2 never rediscovers |
| `/inner` granular, queue drained | main session | UT + AT | one |
| `/review`, before the merge | main session (driver) | AT only | one; more only when the human asks |

`discovery_rounds` in session.yml counts the inner-loop rounds that have
run (0 or 1). Never start a second automatic round. The human can always
ask for another one explicitly.

## Where to look

Read the slice diff (`base_branch..HEAD`), the test list in session.yml,
the acceptance test(s), and the decompose map. Then, per collaborator:

1. **Boundaries of each input.** Empty, zero, one, many, max, negative,
   malformed. Only the ones the role's contract actually cares about.
2. **Each peer's failure modes.** For every doubled peer the class talks
   to: what if it raises, returns nothing, returns a duplicate, times out?
   Is that behaviour decided anywhere?
3. **Branches without a driving test.** Any `if`/`match`/early return in
   production code that no test forces. That is either a missing test or
   over-implementation. Say which.
4. **Implied behaviour.** Things the domain language promises but the
   tests don't check ("an order is *placed*" — so is a placed order
   immutable? re-placeable?).
5. **The sad path at slice level.** Does the acceptance test cover at
   least one meaningful domain error? Are there others a user would hit?

## Sizing: UT or AT?

- **UT candidate:** stays inside one collaborator's contract. You can
  write it as one `should_` unit test, ≤ ~10 lines, against roles that
  already exist. Corner cases, peer failures, boundary inputs.
- **AT candidate:** externally visible behaviour across the slice: a new
  scenario, a new sad path, a new outcome a user would notice. Tag it:
  - `this-slice`: a variation of the current scenario (a sad path or
    edge case of the same use case). Needs human approval, because it
    widens the slice.
  - `other-slice`: new behaviour, a different use case. Goes to
    `docs/backlog.md` without blocking anything. A later `/scenario`
    picks it up.

When unsure, propose it as AT `other-slice`: the backlog is cheap and
widening a slice is not.

Propose an AT only when you have the context to argue it, meaning you can
name the actor, the trigger, and the observable outcome. A vague "more
error handling" is not a proposal.

## Proposal format

```
### Discovery — <slice>, round <n>

UT
1. <Collaborator> — should_<behaviour>
   why: <the gap, with file:line of the untested branch or contract>
2. ...

AT
1. [this-slice | other-slice] <scenario title in business language>
   given/when/then: <one line each>
   why: <what a user would see that nothing tests today>

Over-implementation (code no test demands)
1. <file:line> — <what it does> → add UT <name> | delete it
```

Empty sections say `none`. Five strong proposals beat fifteen weak ones.
Rank each section most-valuable first.

## Recording decisions (driver, after the human decides)

- Approved UT → append to `tests:` with `origin: discovered`,
  `status: pending`, under its collaborator.
- Approved AT `this-slice` → `/acceptance` extends the acceptance test
  (recorded red), then append the UTs it needs to `tests:`.
- AT `other-slice` → append to `docs/backlog.md` (title, given/when/then,
  why, source slice). This file lives outside `.bdd/`, so it survives the
  squash.
- Rejected → drop it, or `/debt` if it's a real risk nobody wants now.
