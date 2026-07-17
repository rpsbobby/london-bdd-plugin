---
name: status
description: Print exactly which command runs next, from .bdd/session.yml — a deterministic lookup, no exploration. Use anytime you're unsure what step you're on.
---

# /status — What Runs Next

This is a lookup, not a judgment call. `.bdd/session.yml` is the single
source of truth (see `references/session-schema.md`) — parse it directly,
the same way `scripts/guard.py` does when enforcing the hard rules, so the
answer here and the hooks' behaviour never disagree.

## Steps

1. Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/next.py`
2. Print its output as-is.
3. If it says no active slice, offer `/scenario` (new behaviour) or
   `/refactor-scope` (existing code).
4. Do not second-guess the result by reading git log, scanning the repo,
   or reasoning from earlier conversation context — session.yml is
   trusted over memory (skill operating rule 6).
