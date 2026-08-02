# Implementer Backends — the GREEN-step interface

`/inner`'s GREEN step needs exactly one thing done: turn the current
failing unit test green with the least code possible, without touching
tests or session state. Who does that is pluggable — `implementer.backend`
in `.bdd/session.yml` picks the executor. Both backends satisfy the same
contract; `/inner` doesn't otherwise care which one ran.

## The contract

**In:**
- the failing test's file and name
- the interface/port definitions it references
- the language notes relevant to the stack
- (external backends only) a `test_command` that runs just that test, and
  the repo root

**Out:**
- production code changed, minimally, to make the test pass
- a report: green (with a summary) or honestly red (with what was tried)

**Absolute rules, regardless of backend:**
1. Never edit test files. A test that looks wrong is reported, not fixed.
2. Never edit `.bdd/` or anything under it.
3. Never edit outside what the test and its referenced interfaces require.
4. No speculative code — no extra params, no future-proofing, no comments
   about later. Hardcoding a return value to pass is fine; the next test
   forces generalisation.
5. Implement against the given interfaces exactly — no renaming, no
   "improving" them.
6. Run the tests and report the real outcome. Red after honest attempts
   is reported, not thrashed on.

## `backend: agent` (default)

The `london-bdd:implementer` Claude subagent (Haiku, `maxTurns: 10`, no
WebSearch/WebFetch — see `agents/implementer.md`). It has native file and
bash tools; `/inner` dispatches it with the context and reads its final
message as the report. This is the only backend available before this
feature — absent `implementer.backend`, sessions behave exactly as before.

## `backend: codex` — OpenAI Codex CLI

`scripts/codex_implementer.py` delegates the GREEN step to `codex exec`
(OpenAI's Codex CLI, run non-interactively). Codex is not a bare
chat-completions model — it's already a full coding agent that reads and
writes files and runs shell commands on its own inside its own sandbox.
That changes the shape of the wrapper: there is no tool loop to drive
(there's nothing to loop), so the script's job is to launch one turn
safely and verify the aftermath rather than mediate every file write:

1. Snapshot `git status --porcelain`, plus a hash of the failing test
   file's own content, BEFORE the run. (The RED step usually leaves the
   tree dirty with just that one file — this is expected, not a
   precondition failure.)
2. Run `codex exec --sandbox workspace-write "<prompt>"` — `workspace-write`
   lets Codex edit repo files without an interactive approval prompt, but
   stops well short of `--dangerously-bypass-approvals-and-sandbox` (no
   network access, nothing outside the workspace). The prompt embeds the
   same six absolute rules above plus the context (test, interfaces,
   language notes, the exact `test_command` to run).
3. Snapshot again AFTER. Any newly-touched path under a protected pattern
   (`tests/`, `test/`, `.bdd/`, or a test-name pattern like `*_test.*`,
   `*Test.java`, `*.test.*`), or any change to the test file's own hash,
   is a **violation** — Codex's own "tests pass" claim is not trusted in
   that case. The script reports `status: red` with a `violation` block
   naming the offending paths, and `/inner` must escalate to the human
   exactly as it would for a `block`-severity reviewer finding — this is
   not a normal red to retry.
4. Absent a violation, the script re-runs `test_command` **itself** — it
   never trusts Codex's internal narration of whether tests passed — and
   reports green/red from that exit code.

**stdin contract** (JSON):
```json
{
  "test": {"file": "tests/unit/OrderRepository_test.cpp",
           "name": "OrderRepository.SavesAndReturnsId"},
  "interfaces": ["src/pricing/OrderRepository.h"],
  "language_notes": "<relevant excerpt from references/language-notes.md>",
  "test_command": "ctest -R OrderRepository.SavesAndReturnsId",
  "model": null,
  "timeout_seconds": 600,
  "cwd": "/abs/path/to/repo"
}
```
`model`, if set, is passed straight through as `codex exec --model
<value>`; if absent, Codex uses whatever model its own config
(`~/.codex/config.toml`) already defaults to — this script does not
hardcode one.

**stdout contract** (JSON):
```json
{"status": "green", "summary": "...", "files_changed": ["src/pricing/OrderRepository.cpp"], "violation": null}
```
Exit code 0 covers a green result, an honest red, and a caught violation
(all normal `/inner` outcomes); exit code 1 means a configuration/protocol
error (`codex` not on PATH, bad stdin JSON, `git status` itself failing,
or `codex exec` timing out) — `/inner` treats that as a hard stop, not a
red test.

**Setup:**
- The `codex` CLI must be on `PATH` and already authenticated (`codex
  login`, or however your org provisions it) — this plugin does not
  manage Codex credentials.
- `implementer.model` in session.yml is optional; see above.
- No third-party Python packages required — stdlib only (`subprocess`,
  `hashlib`, `json`), same reasoning as `guard.py` avoiding a PyYAML
  dependency.

**Why not MCP?** Codex ships its own MCP server (`codex mcp-server`), so
if you wanted Claude to have Codex available as an ad-hoc tool across a
whole session, you would register that server rather than write your
own. But `/inner`'s GREEN step is a single bounded task with a clear
pass/fail contract, invoked from a script that already knows exactly what
to pass in and how to verify the result — a plain `codex exec` subprocess
call is simpler than standing up and managing an MCP server connection
for one shot-in-the-dark turn, and it's what the `agent` backend's own
Bash-based dispatch already looks like.

## Adding another backend

The interface is intentionally small enough that a third backend (a
different provider's CLI, a local model via Ollama, a raw API-calling
script) is a new script satisfying the same stdin/stdout JSON contract,
plus a new `implementer.backend` value wired into `/inner`'s GREEN step.
It does not require touching `agents/implementer.md`, `scripts/guard.py`,
or any other backend.
