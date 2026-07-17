#!/usr/bin/env python3
"""london-bdd status — deterministic "what's next" lookup.

Reads .bdd/session.yml the same way scripts/guard.py does when enforcing
the hard rules, so /status and the hooks can never disagree. This is a
lookup, not a judgment call: no exploration, no git log spelunking, no
re-deriving state from conversation memory. If it's slow, session.yml
drifted from reality — fix the file, not the reasoning.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402


def compute(s):
    if s is None:
        return ("/scenario (greenfield) or /refactor-scope (legacy)",
                 "no active slice")

    phase = s["phase"]
    slice_name = s["slice"] or "?"
    tag = f"[{slice_name}]"

    if phase == "characterise":
        return "/characterise", f"{tag} building the characterisation net"

    if phase == "decompose":
        return "/decompose", f"{tag} naming collaborators for the slice"

    if phase == "inner":
        pending = [c for c in s["collaborators"] if c["status"] != "done"]
        if not pending:
            return "/review", (f"{tag} collaborator queue is drained but "
                                "phase wasn't advanced to close — run "
                                "/review")
        head = pending[0]
        if s["current_failing_test"]:
            return "/inner", (f"{tag} {head['role']} has a recorded "
                               "failing test — continue the cycle "
                               "(implement, review, commit)")
        return "/inner", (f"{tag} {head['role']} is next "
                           f"({len(pending)} collaborator(s) left)")

    if phase == "close":
        return "/review", f"{tag} collaborator queue empty — slice gate"

    if phase == "done":
        base = s["base_branch"] or "the base branch"
        return "/commit-merge", f"{tag} slice closed — land it on {base}"

    return "?", f"{tag} unrecognized phase '{phase}' in session.yml"


def main():
    cwd = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    session_path, _ = guard.find_session(cwd)
    s = guard.parse_session(session_path) if session_path else None
    cmd, reason = compute(s)
    print(f"next: {cmd} — {reason}")


if __name__ == "__main__":
    main()
