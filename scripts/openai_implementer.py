#!/usr/bin/env python3
"""External GREEN-step backend — drives an OpenAI model through the same
implementer contract as the `london-bdd:implementer` agent (see
agents/implementer.md and skills/london-bdd/references/implementer-backends.md):
one failing test in, minimum code to turn it green out, never touching
tests or session state.

Unlike the agent backend (a Claude subagent with native file/bash tools),
an OpenAI chat-completions model has no tools of its own — this script
IS its tool loop: read_file / write_file / run_tests / report, with
write_file enforcing the same "never touch tests or .bdd/" rule the
agent follows by instruction only. Stdlib-only (see guard.py's precedent
for avoiding third-party deps in plugin scripts) — no `openai` package
required, just `urllib`.

Contract
--------
stdin:  JSON — {
          "test": {"file": "...", "name": "..."},
          "interfaces": ["path", ...],
          "language_notes": "free text",
          "test_command": "shell command that runs just this test",
          "model": "gpt-4.1",           # optional, this default if absent
          "max_turns": 10,              # optional
          "cwd": "/abs/path/to/repo"    # optional, defaults to os.getcwd()
        }
stdout: JSON — {
          "status": "green" | "red",
          "summary": "...",
          "files_changed": ["path", ...],
          "turns_used": N
        }
Exit code 0 on a completed run (status green OR honestly red after
max_turns — that is a normal /inner escalation, not a script failure).
Exit code 1 on a configuration/protocol error (missing API key, stdin
that doesn't parse, HTTP failure) — stderr carries the reason.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_MAX_TURNS = 10
API_URL = "https://api.openai.com/v1/chat/completions"

# Mirrors guard.py's ALLOWED_DIR_SEGMENTS / Rule A intent: the implementer
# (whichever backend) never edits tests or session state, on principle,
# not just because a hook happens to be watching.
PROTECTED_DIR_SEGMENTS = {"tests", "test", ".bdd"}
PROTECTED_NAME_MARKERS = ("test_", "_test", ".test.", "Test.java", "spec.")

SYSTEM_PROMPT = """You are the implementer in a London School BDD inner \
loop. You receive one failing test, the interface/port definitions it \
references, and language tooling notes. Nothing else exists for you.

Your job: the least code that makes that one test pass.

Rules — absolute:
1. You NEVER edit test files. If the test seems wrong, stop and call \
report with status "red" explaining why — do not "fix" it.
2. You NEVER edit anything under .bdd/.
3. You NEVER edit files outside what the failing test and its referenced \
interfaces require.
4. No speculation: no extra methods, no parameters "for later", no error \
handling the test doesn't demand, no comments explaining future plans. \
Hardcoding a return value is acceptable if it passes the test — the next \
test will force generalisation.
5. Implement against the given interfaces exactly. Do not rename, \
extend, or "improve" them.
6. Use read_file to see current contents, write_file to make changes, \
run_tests to check your work. After tests pass, call report with status \
"green" and a one-sentence summary. If you cannot reach green after \
honest attempts, call report with status "red" and explain what you \
tried — do not thrash.

You have a limited number of turns. Work efficiently: read what you need, \
write the minimum, run the test, report."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's current contents, relative to the repo root.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a file's full contents, relative to the repo root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the configured test command and return its output.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report",
            "description": "End the session: tests are green, or honestly red after real attempts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["green", "red"]},
                    "summary": {"type": "string"},
                },
                "required": ["status", "summary"],
            },
        },
    },
]


class ProtocolError(Exception):
    pass


def is_protected(relpath):
    p = relpath.replace(os.sep, "/")
    parts = p.split("/")
    if any(seg in PROTECTED_DIR_SEGMENTS for seg in parts[:-1]):
        return True
    name = parts[-1]
    return any(marker in name for marker in PROTECTED_NAME_MARKERS)


def resolve(cwd, relpath):
    full = os.path.abspath(os.path.join(cwd, relpath))
    if os.path.commonpath([full, os.path.abspath(cwd)]) != os.path.abspath(cwd):
        raise ProtocolError(f"path escapes repo root: {relpath}")
    return full


def tool_read_file(cwd, args):
    try:
        full = resolve(cwd, args["path"])
        with open(full, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        return f"error: {e}"


def tool_write_file(cwd, args, files_changed, test_file):
    relpath = args["path"]
    if test_file and os.path.normpath(relpath) == os.path.normpath(test_file):
        return "refused: this is the test file under test — never edit it"
    if is_protected(relpath):
        return (f"refused: '{relpath}' matches a protected path (tests/, "
                ".bdd/, or a test-file naming pattern) — the implementer "
                "backend never writes there")
    full = resolve(cwd, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(args["content"])
    if relpath not in files_changed:
        files_changed.append(relpath)
    return "ok"


def tool_run_tests(cwd, test_command):
    if not test_command:
        return "error: no test_command was provided in the context"
    proc = subprocess.run(test_command, shell=True, cwd=cwd,
                           capture_output=True, text=True, timeout=300)
    out = (proc.stdout or "") + (proc.stderr or "")
    return f"exit_code={proc.returncode}\n{out[-4000:]}"


def call_openai(api_key, model, messages):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ProtocolError(f"OpenAI API error {e.code}: {e.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        raise ProtocolError(f"OpenAI API unreachable: {e}")


def run(context):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ProtocolError("OPENAI_API_KEY is not set in the environment")

    cwd = context.get("cwd") or os.getcwd()
    test = context.get("test") or {}
    test_file = test.get("file")
    model = context.get("model") or DEFAULT_MODEL
    max_turns = context.get("max_turns") or DEFAULT_MAX_TURNS

    user_context = json.dumps({
        "test": test,
        "interfaces": context.get("interfaces") or [],
        "language_notes": context.get("language_notes") or "",
    }, indent=2)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{user_context}"},
    ]

    files_changed = []
    for turn in range(1, max_turns + 1):
        response = call_openai(api_key, model, messages)
        choice = response["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []

        if not tool_calls:
            # Model spoke without calling a tool — nudge it back on contract.
            messages.append({"role": "user",
                              "content": "Use a tool call: read_file, "
                                         "write_file, run_tests, or report."})
            continue

        for call in tool_calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            if name == "report":
                return {
                    "status": args.get("status", "red"),
                    "summary": args.get("summary", ""),
                    "files_changed": files_changed,
                    "turns_used": turn,
                }
            elif name == "read_file":
                result = tool_read_file(cwd, args)
            elif name == "write_file":
                result = tool_write_file(cwd, args, files_changed, test_file)
            elif name == "run_tests":
                result = tool_run_tests(cwd, context.get("test_command"))
            else:
                result = f"error: unknown tool {name}"

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            })

    return {
        "status": "red",
        "summary": f"did not reach green within {max_turns} turns",
        "files_changed": files_changed,
        "turns_used": max_turns,
    }


def main():
    try:
        context = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"openai_implementer: invalid JSON on stdin: {e}\n")
        sys.exit(1)

    try:
        result = run(context)
    except ProtocolError as e:
        sys.stderr.write(f"openai_implementer: {e}\n")
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
