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

## `backend: openai` — external model

`scripts/openai_implementer.py` drives an OpenAI chat-completions model
through the same contract. Because that model has no tools of its own,
the script IS the tool loop: it hands the model four function-call tools
— `read_file`, `write_file`, `run_tests`, `report` — and executes them
locally, feeding results back until `report` is called or `max_turns`
(default 10) runs out.

`write_file` enforces rules 1–2 itself, in code, not just by instruction:
it refuses the exact test-file path plus anything under `tests/`, `test/`,
`.bdd/`, or matching common test-name patterns (`test_*`, `*_test`,
`*.test.*`, `*Test.java`, `spec.*`). A refusal is returned to the model as
a tool result, the same way a compiler error would be — the model sees it
and corrects course, it isn't a hard crash.

**stdin contract** (JSON):
```json
{
  "test": {"file": "tests/unit/OrderRepository_test.cpp",
           "name": "OrderRepository.SavesAndReturnsId"},
  "interfaces": ["src/pricing/OrderRepository.h"],
  "language_notes": "<relevant excerpt from references/language-notes.md>",
  "test_command": "ctest -R OrderRepository.SavesAndReturnsId",
  "model": "gpt-4.1",
  "max_turns": 10,
  "cwd": "/abs/path/to/repo"
}
```

**stdout contract** (JSON):
```json
{"status": "green", "summary": "...", "files_changed": ["src/pricing/OrderRepository.cpp"], "turns_used": 4}
```

Exit code 0 covers both a green result and an honest red (that's a normal
`/inner` escalation, not a script failure); exit code 1 means a
configuration/protocol error (bad JSON, missing key, unreachable API) —
`/inner` treats that as a hard stop, not a red test, and hands back to
the human immediately rather than retrying.

**Setup:**
- `OPENAI_API_KEY` must be set in the environment. If it's missing,
  `/inner` stops and tells the user rather than silently falling back to
  the `agent` backend — a silent fallback would mean tests run against
  the wrong model without anyone deciding that.
- `implementer.model` in session.yml overrides the default (`gpt-4.1`).
- No third-party Python packages required — stdlib `urllib` only, same
  reasoning as `guard.py` avoiding a PyYAML dependency.

## Adding another backend

The interface is intentionally small enough that a third backend (a
different provider, a local model via Ollama, a CLI agent like `aider`)
is a new script satisfying the same stdin/stdout JSON contract, plus a
new `implementer.backend` value wired into `/inner`'s GREEN step. It does
not require touching `agents/implementer.md`, `scripts/guard.py`, or the
`agent` backend at all.
