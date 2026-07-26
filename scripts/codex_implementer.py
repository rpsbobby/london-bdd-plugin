#!/usr/bin/env python3
"""External GREEN-step backend — drives OpenAI's Codex CLI (`codex exec`)
through the same implementer contract as the `london-bdd:implementer`
agent (see agents/implementer.md and
skills/london-bdd/references/implementer-backends.md): one failing test
in, minimum code to turn it green out, never touching tests or session
state.

Unlike a raw chat-completions model, `codex exec` is already a full
non-interactive coding agent — it reads and writes files and runs shell
commands on its own, inside its own sandbox. This script does not run a
tool loop for it (there's nothing to loop); it launches one `codex exec`
turn and verifies the aftermath:

  1. Snapshot `git status --porcelain` and the failing test file's
     content BEFORE the run (the RED step usually leaves the tree dirty
     with just that one file).
  2. Run `codex exec --sandbox workspace-write <prompt>` — workspace-write
     lets it edit repo files without an interactive approval prompt, but
     stops short of `--dangerously-bypass-approvals-and-sandbox` (no
     network, no operations outside the workspace).
  3. Snapshot again AFTER. Any newly-touched path under a protected
     pattern (tests/, test/, .bdd/, or a test-name pattern), or any
     change to the test file's own content, is a violation — we do not
     trust Codex's own "I passed" claim in that case, we escalate.
  4. Absent a violation, run test_command OURSELVES (never trust the
     model's internal claim) and report green/red from its exit code.

Stdlib-only, same reasoning as guard.py avoiding a PyYAML dependency and
openai_implementer.py's precedent (superseded by this file) avoiding the
`openai` package.

Contract
--------
stdin:  JSON — {
          "test": {"file": "...", "name": "..."},
          "interfaces": ["path", ...],
          "language_notes": "free text",
          "test_command": "shell command that runs just this test",
          "model": "o4-mini",           # optional — passed as --model if set
          "timeout_seconds": 600,        # optional
          "cwd": "/abs/path/to/repo"     # optional, defaults to os.getcwd()
        }
stdout: JSON — {
          "status": "green" | "red",
          "summary": "...",
          "files_changed": ["path", ...],
          "violation": null | {"paths": [...], "reason": "..."}
        }
Exit code 0 on a completed run (green, honest red, or a caught
violation — all normal /inner escalation shapes, not script failures).
Exit code 1 on a configuration/protocol error (codex not on PATH, stdin
that doesn't parse, codex exec itself timing out) — stderr carries the
reason.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

DEFAULT_TIMEOUT_SECONDS = 600

PROTECTED_DIR_SEGMENTS = {"tests", "test", ".bdd"}
PROTECTED_NAME_MARKERS = ("test_", "_test", ".test.", "Test.java", "spec.")

PROMPT_TEMPLATE = """You are the implementer in a London School BDD inner \
loop, working directly in this repository's working tree.

Context:
{context_json}

Your job: the least code that makes the failing test above pass.

Rules — absolute:
1. Do NOT edit the test file ({test_file}) or any file under tests/, \
test/, or .bdd/. If the test looks wrong, stop and explain why instead \
of touching it.
2. Do NOT edit files outside what the failing test and its referenced \
interfaces require.
3. No speculative code: no extra methods, no parameters "for later", no \
error handling the test doesn't demand. Hardcoding a return value is \
acceptable if it passes the test.
4. Implement against the given interfaces exactly — do not rename, \
extend, or "improve" them.
5. After writing code, run: {test_command}
   Report whether it passed and, briefly, what you changed.
"""


class ProtocolError(Exception):
    pass


def is_protected(relpath):
    p = relpath.replace(os.sep, "/")
    parts = p.split("/")
    if any(seg in PROTECTED_DIR_SEGMENTS for seg in parts[:-1]):
        return True
    name = parts[-1]
    return any(marker in name for marker in PROTECTED_NAME_MARKERS)


def git_status(cwd):
    """Map of relpath -> porcelain status code, e.g. {'src/x.py': ' M'}.
    Rename entries ('R  old -> new') are recorded under the new path."""
    try:
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=cwd,
                               capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        raise ProtocolError(f"`git status` failed in {cwd}: {e}")
    out = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        code, rest = line[:2], line[3:]
        path = rest.split(" -> ")[-1].strip().strip('"')
        out[path] = code
    return out


def file_hash(cwd, relpath):
    if not relpath:
        return None
    full = os.path.join(cwd, relpath)
    try:
        with open(full, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def find_violations(before, after, test_file):
    new_protected = sorted(
        p for p in after if p not in before and is_protected(p))
    return new_protected


def build_prompt(context):
    test = context.get("test") or {}
    payload = json.dumps({
        "test": test,
        "interfaces": context.get("interfaces") or [],
        "language_notes": context.get("language_notes") or "",
    }, indent=2)
    return PROMPT_TEMPLATE.format(
        context_json=payload,
        test_file=test.get("file", "<unspecified>"),
        test_command=context.get("test_command") or "<no test_command given>",
    )


def run_codex(cwd, prompt, model, timeout_seconds):
    codex_bin = shutil.which("codex")
    if not codex_bin:
        raise ProtocolError("`codex` is not on PATH")
    cmd = [codex_bin, "exec", "--sandbox", "workspace-write"]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                               timeout=timeout_seconds)
    except subprocess.TimeoutExpired as e:
        raise ProtocolError(f"codex exec timed out after {timeout_seconds}s: {e}")


def run_test_command(cwd, test_command):
    if not test_command:
        return 1, "error: no test_command was provided in the context"
    proc = subprocess.run(test_command, shell=True, cwd=cwd,
                           capture_output=True, text=True, timeout=300)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out[-4000:]


def run(context):
    cwd = context.get("cwd") or os.getcwd()
    test = context.get("test") or {}
    test_file = test.get("file")
    timeout_seconds = context.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS

    before = git_status(cwd)
    before_hash = file_hash(cwd, test_file)

    prompt = build_prompt(context)
    codex_proc = run_codex(cwd, prompt, context.get("model"), timeout_seconds)

    after = git_status(cwd)
    after_hash = file_hash(cwd, test_file)

    violations = find_violations(before, after, test_file)
    if before_hash != after_hash:
        violations = [test_file] + violations

    files_changed = sorted(p for p in after if p not in before)

    if violations:
        return {
            "status": "red",
            "summary": "codex touched protected path(s) it must not edit: "
                        + ", ".join(violations),
            "files_changed": files_changed,
            "violation": {"paths": violations,
                          "reason": "test file or tests/.bdd/ path changed "
                                    "during the codex exec turn"},
        }

    if codex_proc.returncode != 0:
        tail = ((codex_proc.stdout or "") + (codex_proc.stderr or ""))[-2000:]
        return {
            "status": "red",
            "summary": f"codex exec exited {codex_proc.returncode}: {tail}",
            "files_changed": files_changed,
            "violation": None,
        }

    exit_code, test_output = run_test_command(cwd, context.get("test_command"))
    status = "green" if exit_code == 0 else "red"
    summary = (codex_proc.stdout or "").strip()[-2000:] or "(no summary from codex)"
    if status == "red":
        summary += f"\n\ntest run (exit {exit_code}):\n{test_output}"

    return {
        "status": status,
        "summary": summary,
        "files_changed": files_changed,
        "violation": None,
    }


def main():
    try:
        context = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"codex_implementer: invalid JSON on stdin: {e}\n")
        sys.exit(1)

    try:
        result = run(context)
    except ProtocolError as e:
        sys.stderr.write(f"codex_implementer: {e}\n")
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
