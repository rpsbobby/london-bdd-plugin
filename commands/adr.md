---
name: adr
description: Record an architecture decision — Context, Decision, Consequences, one page max, in git next to the code.
---

# /adr — Record the Decision

1. Determine the next number from `adr/` (create the directory if absent).
2. Draft with the user — keep each section tight:

```markdown
# ADR-NNN — <title>
**Status:** Proposed | Accepted | Superseded by ADR-MMM
**Date:** <yyyy-mm>

## Context
What forces are at play. Why a decision is needed now. 3–6 sentences.

## Decision
What we are doing. Active voice. The one paragraph someone reads in a year.

## Consequences
What becomes easier, what becomes harder, what we are explicitly accepting.
Include rejected alternatives in one line each if they were seriously considered.
```

3. One page maximum. If it doesn't fit, the decision isn't understood yet.
4. Save as `adr/ADR-NNN-<kebab-title>.md`, commit:
   `docs: ADR-NNN <title>`
5. If the decision emerged mid-slice, cross-reference the slice name.
