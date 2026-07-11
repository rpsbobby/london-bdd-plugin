---
name: debt
description: Log a tech-debt register entry — explicit, versioned, reviewable. Used for scope-creep candidates, bugs found during characterisation, distil candidates, and any "while we're here" temptation.
---

# /debt — Make It Explicit or It Doesn't Exist

Debt lives in a register, not in TODO comments.

1. Ensure `tech-debt/register.yml` exists (create with empty list if not).
2. Append an entry — every field required:

```yaml
- id: TD-NNN                # next sequential
  area: <module / boundary>
  description: <what and where — specific enough to act on cold>
  impact: <what it blocks or risks — testability, port, correctness>
  effort: Small | Medium | Large
  mode: SAFE | FULL_REFACTOR   # what fixing it would take
  source: <slice or event that surfaced it>
  added: <yyyy-mm>
  status: active
```

3. Regenerate `tech-debt/DEBT.md` — human-readable table sorted by impact,
   active items first.
4. Commit: `docs: tech debt TD-NNN — <short description>`

Typical sources: scope-creep refusals from /refactor-scope, bugs
discovered (not fixed!) during /characterise, distil candidates deferred
in /review, boundary violations found by the reviewer agent.
