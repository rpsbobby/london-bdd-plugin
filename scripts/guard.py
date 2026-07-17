#!/usr/bin/env python3
"""london-bdd guard hook.

Enforces the four hard rules when a .bdd/session.yml slice is active:

  A. No production edit without a recorded failing test.
  B. In SAFE / FULL_REFACTOR mode, no edit outside the declared scope.
  C. `git commit` only on the slice's feature/<slice>-tmp branch. Merges
     onto feature/<slice>-main are the developer's manual action, unless
     `/commit-merge --auto` has dropped a fresh, untracked
     `.bdd/.merge-authorized` marker naming this exact tmp/base branch
     pair (see find_merge_marker). Rebases are never allowed for the agent.
  D. Phase transitions in session.yml are forward-only and earned (see
     validate_phase_transition) — checked on Edit/Write/MultiEdit, and on
     Bash only for the narrow case of a redirect/tee write at that exact
     path (see bash_targets_session_yml). A human editing the file
     directly, outside Claude Code entirely, always bypasses every rule
     here — that's expected: this hook governs the agent's own tool
     calls, not the developer's own editor.

Note on the marker file: `git checkout <base_branch>` removes
`.bdd/session.yml` from the working tree (it's tracked only on the tmp
branch), so by the time `git merge --squash` actually runs, session.yml is
gone and Rule C can't consult it. `.merge-authorized` is deliberately
never git-added, so checkout never touches it — it survives the branch
switch and is the only thing Rule C's merge/landing-commit checks rely on.

Because session.yml is unreadable on a slice's main branch, an *entirely
unauthorized* merge attempt there (no marker at all) can't be detected by
session.yml either. `sibling_tmp_branch` closes that gap: if the current
branch matches `feature/<slice>-main` and `feature/<slice>-tmp` exists,
Rule C treats it as governed and blocks the merge regardless of whether
any session file is present.

If none of session.yml, the merge marker, or a matching tmp sibling
branch are found, the guard is silent — the plugin never interferes with
work outside a BDD slice.

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
    s = {"slice": None, "mode": None, "branch": None, "base_branch": None,
         "current_failing_test": None, "scope_in": [], "scope_out": [],
         "phase": None, "char_status": None, "acceptance_status": None,
         "collaborators": [], "cycle": 0}
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return s
    m = re.search(r"^slice:\s*(\S+)", text, re.M)
    if m: s["slice"] = m.group(1)
    m = re.search(r"^mode:\s*(\S+)", text, re.M)
    if m: s["mode"] = m.group(1)
    m = re.search(r"^phase:\s*(\S+)", text, re.M)
    if m: s["phase"] = m.group(1)
    m = re.search(r"^branch:\s*(\S+)", text, re.M)
    if m: s["branch"] = m.group(1)
    m = re.search(r"^base_branch:\s*(\S+)", text, re.M)
    if m: s["base_branch"] = m.group(1)
    m = re.search(r"^cycle:\s*(\d+)", text, re.M)
    if m: s["cycle"] = int(m.group(1))
    m = re.search(r"^current_failing_test:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if m and re.search(r"\bfile:\s*\S", m.group(1)):
        s["current_failing_test"] = True
    m = re.search(r"^characterisation:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if m:
        st = re.search(r"\bstatus:\s*(\S+)", m.group(1))
        if st: s["char_status"] = st.group(1)
    m = re.search(r"^acceptance_test:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if m:
        st = re.search(r"\bstatus:\s*(\S+)", m.group(1))
        if st: s["acceptance_status"] = st.group(1)
    m = re.search(r"^collaborators:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    if m:
        for role_m in re.finditer(
                r"-\s*role:\s*(\S+)\s*\n\s*status:\s*(\S+)", m.group(1)):
            s["collaborators"].append(
                {"role": role_m.group(1), "status": role_m.group(2)})
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


PHASE_ORDER = ["characterise", "decompose", "inner", "close", "done"]


def extract_new_phase(tool_input):
    """Pull the phase: value an in-flight edit would write, from whichever
    shape the tool uses (Write's content, Edit's new_string, MultiEdit's
    edits[].new_string). Returns None if this edit doesn't touch phase:."""
    chunks = []
    if "content" in tool_input:
        chunks.append(tool_input["content"])
    if "new_string" in tool_input:
        chunks.append(tool_input["new_string"])
    for e in tool_input.get("edits") or []:
        if "new_string" in e:
            chunks.append(e["new_string"])
    text = "\n".join(chunks)
    m = re.search(r"^phase:\s*(\S+)", text, re.M)
    return m.group(1) if m else None


def validate_phase_transition(s, new_phase):
    """Rule D: mechanizes session-schema.md's 'phase transitions are
    forward-only ... commands refuse to run out of order' — without this,
    that line is just prose the agent is trusted to self-enforce, and
    .bdd/session.yml is otherwise unguarded (it must stay writable for the
    commands that legitimately advance it). Returns an error message, or
    None if the transition is legal. Unrecognized phase values (custom
    workflows) are waved through — this only polices the documented ones."""
    old_phase = s["phase"]
    if new_phase not in PHASE_ORDER:
        return None
    if old_phase in PHASE_ORDER and (
            PHASE_ORDER.index(new_phase) < PHASE_ORDER.index(old_phase)):
        return (f"Rule D: phase cannot move backward from '{old_phase}' to "
                f"'{new_phase}'. Phase transitions are forward-only within "
                "a slice (session-schema.md).")

    if new_phase == "decompose" and s["mode"] in ("SAFE", "FULL_REFACTOR"):
        if s["char_status"] != "green":
            return ("Rule D: cannot enter phase 'decompose' — the "
                    "characterisation net must be green first "
                    "(/characterise).")

    if new_phase == "inner":
        if s["mode"] == "GREENFIELD":
            if not s["collaborators"]:
                return ("Rule D: cannot enter phase 'inner' with an empty "
                        "collaborator queue — run /decompose first.")
            if s["acceptance_status"] != "red":
                return ("Rule D: cannot enter phase 'inner' — the "
                        "acceptance test must be recorded red first "
                        "(/scenario).")
        elif s["mode"] in ("SAFE", "FULL_REFACTOR"):
            if s["char_status"] != "green":
                return ("Rule D: cannot enter phase 'inner' — the "
                        "characterisation net must be green first "
                        "(/characterise).")

    if new_phase == "close":
        if not s["collaborators"]:
            return ("Rule D: cannot enter phase 'close' with no "
                    "collaborators recorded — the inner loop queue must be "
                    "worked and drained first (/inner).")
        unfinished = [c["role"] for c in s["collaborators"]
                      if c["status"] != "done"]
        if unfinished:
            return ("Rule D: cannot enter phase 'close' — collaborator(s) "
                     f"still open: {', '.join(unfinished)}. Finish the "
                     "queue with /inner.")

    if new_phase == "done" and old_phase != "close":
        return ("Rule D: cannot enter phase 'done' except from 'close' — "
                "run /review to close the outer loop first.")

    return None


MERGE_MARKER = ".merge-authorized"


def find_merge_marker(start):
    """Untracked marker dropped by /commit-merge --auto. Never git-added,
    so `git checkout <base_branch>` never removes it — unlike
    .bdd/session.yml, which is tracked only on the tmp branch."""
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".bdd", MERGE_MARKER)
        if os.path.isfile(p):
            try:
                text = open(p, encoding="utf-8").read()
            except OSError:
                return None, None
            mb = re.search(r"^branch:\s*(\S+)", text, re.M)
            mm = re.search(r"^base_branch:\s*(\S+)", text, re.M)
            if mb and mm:
                return {"branch": mb.group(1), "base_branch": mm.group(1)}, d
            return None, None
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


def git_branch(cwd):
    try:
        return subprocess.run(
            ["git", "branch", "--show-current"], cwd=cwd,
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def sibling_tmp_branch(cwd, br):
    """If br is a slice's feature/<slice>-main and feature/<slice>-tmp
    exists, return the tmp branch name. Lets Rule C recognize a slice's
    main branch as governed even when .bdd/session.yml (tracked only on
    tmp) isn't present in the working tree to prove it."""
    m = re.match(r"^feature/(.+)-main$", br or "")
    if not m:
        return None
    tmp = f"feature/{m.group(1)}-tmp"
    try:
        out = subprocess.run(
            ["git", "branch", "--list", tmp], cwd=cwd,
            capture_output=True, text=True, timeout=5).stdout
        return tmp if out.strip() else None
    except Exception:
        return None


def bash_targets_session_yml(cmd):
    """True if cmd redirects/tees output at .bdd/session.yml — the way to
    dodge Rule D's phase-transition check, which only inspects Edit/Write/
    MultiEdit tool calls. Deliberately narrow: only unambiguous redirect
    syntax (>, >>, tee) is matched. cp/mv/sed -i/python one-liners are NOT
    caught here — regexing every way Bash can write a file is a losing
    arms race and risks false positives on legitimate reads or the
    documented archive-copy flow. This blocks the accidental case (Claude
    reaching for a shell one-liner instead of the Edit tool), not a
    determined adversarial one."""
    for m in re.finditer(r"(?:>>|>)\s*(\S+)", cmd):
        target = m.group(1).strip("'\"")
        if target.replace(os.sep, "/").endswith(".bdd/session.yml"):
            return True
    m = re.search(r"\btee\b(?:\s+-\S+)*\s+(\S+)", cmd)
    if m:
        target = m.group(1).strip("'\"")
        if target.replace(os.sep, "/").endswith(".bdd/session.yml"):
            return True
    return False


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

    session_path, session_root = find_session(cwd)
    s = parse_session(session_path) if session_path else None
    marker, marker_root = find_merge_marker(cwd)
    root = session_root or marker_root or os.path.abspath(cwd)

    if kind == "bash":
        cmd = tool_input.get("command", "")
        if session_path and bash_targets_session_yml(cmd):
            block("Rule D: writes to .bdd/session.yml via Bash bypass the "
                  "phase-transition check — use the Edit or Write tool so "
                  "the guard can validate the target phase. (Reading or "
                  "archiving the file via Bash is unaffected; this only "
                  "blocks redirect/tee writes at that exact path.)")
        if re.search(r"\bgit\s+(commit|merge|rebase)\b", cmd):
            br = git_branch(root)
            sibling = sibling_tmp_branch(root, br)
            if not session_path and not marker and not sibling:
                sys.exit(0)  # not a slice's tmp, main, or pending merge -> silent
            landing = bool(marker) and br == marker["base_branch"]
            if re.search(r"\bgit\s+commit\b", cmd) and not landing:
                if s and s["branch"] and br != s["branch"]:
                    block(f"Rule C: commits belong on '{s['branch']}' "
                          f"(currently on '{br or 'unknown'}'). Check out the "
                          "slice branch or let the developer commit by hand.")
                if not re.match(r"^feature/.+-tmp$", br):
                    block("Rule C: agent commits are allowed only on a "
                          "feature/<slice>-tmp branch, or the merge-landing "
                          "commit authorized via /commit-merge --auto.")
            if re.search(r"\bgit\s+rebase\b", cmd):
                block("Rule C: rebases are the developer's manual action, "
                      "never the agent's.")
            if re.search(r"\bgit\s+merge\b", cmd):
                squash_src = re.search(r"--squash\s+(\S+)", cmd)
                authorized = (
                    landing
                    and squash_src is not None
                    and squash_src.group(1) == marker["branch"]
                )
                if not authorized:
                    block("Rule C: merges onto shared branches are the "
                          "developer's manual action, unless authorized via "
                          "`/commit-merge --auto` — a fresh "
                          ".bdd/.merge-authorized marker naming this exact "
                          "tmp branch, while checked out on its "
                          "base_branch, with an exact "
                          "'git merge --squash <tmp>'.")
        sys.exit(0)

    # kind == "edit"
    if not session_path:
        sys.exit(0)  # no active slice -> guard is silent
    fp = tool_input.get("file_path") or tool_input.get("path") or ""
    if not fp:
        sys.exit(0)
    r = rel(fp, root)

    # Rule D — phase-transition gate. Checked even though .bdd/ is
    # otherwise always-allowed below: session.yml itself must stay
    # writable for legitimate transitions, but the *value* written must
    # be an earned one.
    if r.replace(os.sep, "/") == ".bdd/session.yml":
        new_phase = extract_new_phase(tool_input)
        if new_phase and new_phase != s["phase"]:
            err = validate_phase_transition(s, new_phase)
            if err:
                block(err)

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
