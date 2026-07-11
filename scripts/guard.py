#!/usr/bin/env python3
"""london-bdd guard hook.

Enforces the three hard rules when a .bdd/session.yml slice is active:

  A. No production edit without a recorded failing test.
  B. In SAFE / FULL_REFACTOR mode, no edit outside the declared scope.
  C. `git commit` only on the slice's feature-tmp branch.

If no session file exists, the guard is silent — the plugin never
interferes with work outside a BDD slice.

Exit 0        -> allow
Exit 2 + msg  -> block (stderr message is shown to Claude)
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

def read_stdin_json():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def find_session(start):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".bdd", "session.yml")
        if os.path.isfile(p):
            return p, d
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


def parse_session(path):
    """Minimal YAML subset parser — avoids a PyYAML dependency."""
    s = {"mode": None, "branch": None, "current_failing_test": None,
         "scope_in": [], "scope_out": [], "phase": None, "char_status": None}
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return s
    m = re.search(r"^mode:\s*(\S+)", text, re.M)
    if m: s["mode"] = m.group(1)
    m = re.search(r"^phase:\s*(\S+)", text, re.M)
    if m: s["phase"] = m.group(1)
    m = re.search(r"^branch:\s*(\S+)", text, re.M)
    if m: s["branch"] = m.group(1)
    m = re.search(r"^current_failing_test:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if m and re.search(r"\bfile:\s*\S", m.group(1)):
        s["current_failing_test"] = True
    m = re.search(r"^characterisation:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if m:
        st = re.search(r"\bstatus:\s*(\S+)", m.group(1))
        if st: s["char_status"] = st.group(1)
    block = re.search(r"^scope:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if block:
        cur = None
        for line in block.group(1).splitlines():
            if re.match(r"\s+in:", line): cur = "scope_in"; continue
            if re.match(r"\s+out:", line): cur = "scope_out"; continue
            if re.match(r"\s+\w+:", line): cur = None; continue
            item = re.match(r"\s+-\s*(\S.*?)\s*(#.*)?$", line)
            if item and cur:
                s[cur].append(item.group(1).strip("'\""))
    return s


def git_branch(cwd):
    try:
        return subprocess.run(
            ["git", "branch", "--show-current"], cwd=cwd,
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def block(msg):
    sys.stderr.write("[london-bdd guard] " + msg + "\n")
    sys.exit(2)


def rel(path, root):
    try:
        return os.path.relpath(os.path.abspath(path), root)
    except ValueError:
        return path


ALLOWED_DIR_SEGMENTS = {"tests", "test", "adr", "tech-debt", "docs", ".bdd"}
ALLOWED_FILENAMES = {"CLAUDE.md"}


def is_always_allowed(relpath):
    p = relpath.replace(os.sep, "/")
    if p.startswith("."):          # .bdd/, .github/, dotfiles
        return True
    parts = p.split("/")
    if any(seg in ALLOWED_DIR_SEGMENTS for seg in parts[:-1]):
        return True                # tests/ anywhere in the path, nested included
    name = parts[-1]
    return name in ALLOWED_FILENAMES or name.startswith("README")


def in_scope(relpath, patterns):
    p = relpath.replace(os.sep, "/")
    for pat in patterns:
        pat = pat.replace(os.sep, "/")
        if fnmatch.fnmatch(p, pat) or p == pat or p.startswith(pat.rstrip("/*") + "/"):
            return True
    return False


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "edit"
    payload = read_stdin_json()
    tool_input = payload.get("tool_input", {}) or {}
    cwd = payload.get("cwd") or os.getcwd()

    session_path, root = find_session(cwd)
    if not session_path:
        sys.exit(0)  # no active slice -> guard is silent
    s = parse_session(session_path)

    if kind == "bash":
        cmd = tool_input.get("command", "")
        if re.search(r"\bgit\s+(commit|merge|rebase)\b", cmd):
            br = git_branch(root)
            if re.search(r"\bgit\s+commit\b", cmd):
                if s["branch"] and br != s["branch"]:
                    block(f"Rule C: commits belong on '{s['branch']}' "
                          f"(currently on '{br or 'unknown'}'). Check out the "
                          "slice branch or let the developer commit by hand.")
                if not br.startswith("feature-tmp"):
                    block("Rule C: agent commits are allowed only on a "
                          "feature-tmp branch. Squash-merges to feature-main "
                          "are the developer's manual action.")
            if re.search(r"\bgit\s+(merge|rebase)\b", cmd):
                block("Rule C: merges/rebases onto shared branches are the "
                      "developer's manual action, never the agent's.")
        sys.exit(0)

    # kind == "edit"
    fp = tool_input.get("file_path") or tool_input.get("path") or ""
    if not fp:
        sys.exit(0)
    r = rel(fp, root)
    if is_always_allowed(r):
        sys.exit(0)  # tests, docs, .bdd, registers are always writable

    # Rule A — red gate. A production edit is licensed by any ONE of:
    #   1. a recorded failing test (the normal inner-loop red)
    #   2. phase == close (wiring the composition root to close the outer loop)
    #   3. SAFE mode with a green characterisation net (refactoring moves
    #      are green-to-green by definition; the net is the license)
    licensed = (
        s["current_failing_test"]
        or s["phase"] == "close"
        or (s["mode"] == "SAFE" and s["char_status"] == "green")
    )
    if not licensed:
        block(f"Rule A: production edit to '{r}' is blocked — no license. "
              "Licenses: a failing test in session.yml (/unit, /acceptance), "
              "phase 'close' (composition-root wiring), or SAFE mode with a "
              "green characterisation net. If this file is not production "
              "code, move it under an allowed path.")

    # Rule B — scope gate
    if s["mode"] in ("SAFE", "FULL_REFACTOR") and s["scope_in"]:
        if in_scope(r, s["scope_out"]):
            block(f"Rule B: '{r}' is declared OUT of scope for this slice. "
                  "Extend the scope explicitly (/refactor-scope) or log the "
                  "temptation to /debt.")
        if not in_scope(r, s["scope_in"]):
            block(f"Rule B ({s['mode']}): '{r}' is outside the declared "
                  "scope. Extend scope explicitly or log to /debt — no "
                  "silent 'while we're here'.")
    sys.exit(0)


if __name__ == "__main__":
    main()
