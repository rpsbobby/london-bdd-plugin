# Approval Testing — Golden Master at Scale

Approval testing (Feathers' "Golden Master", formalised as a technique by
Llewellyn Falco's ApprovalTests project) is probe-first discovery
(`characterisation.md`) scaled up: instead of hand-transcribing one
observed value into an assertion, the tool captures the *entire* actual
output to a file, diffs it against a previously approved file on every
run, and hands you a diff (often via a visual diff tool) to accept or
reject. Accepting **is** the "lock the observed value in" step from
probe-first — same judgment, automated capture.

## When to reach for it

Plain hand-written probe-first assertions (`characterisation.md`) stay
the default for small, scalar outputs — a price, a status code, a count.
Reach for approval testing when hand-transcription itself becomes the
bottleneck:

- **Structured or large output** — an object graph, a generated report,
  a JSON payload, rendered markup. Hand-copying it into an assertion is
  error-prone and the assertion becomes unreadable.
- **Combinatorial input sweeps** — characterising a function across many
  input combinations at once (approval libraries can parameterise a
  single approved file per combination).
- **Output that changes shape**, not just value, as understanding
  improves — a diff shows *what* moved, which a hardcoded assertion
  can't.

Both techniques are still probe-first in spirit: the first captured
output is not truth, it's a proposal. Nothing is approved without the
human looking at the diff and agreeing it's the current, real behaviour
— never a shortcut past that judgment call.

## Workflow

1. Write the test to call the legacy code and hand the output to the
   approval tool's assert call — no expected value written by hand.
2. Run it. First run has no approved file: it fails and writes a
   `.received` file (naming varies by tool) alongside the (still empty
   or absent) `.approved` file, and usually opens a diff tool.
3. **Show the received output to the user before approving anything** —
   same rule as probe-first: surprises are gold, discovered bugs get
   logged to `/debt`, never silently fixed here.
4. On agreement, approve it — the tool copies received → approved (or
   the human runs the reporter's "accept" action). The `.approved` file
   is now the locked-in expected value.
5. Commit the test **and** its `.approved` file together — the approved
   file is the assertion, not fixture noise. Never commit a `.received`
   file; add its pattern to `.gitignore` once, per project.
6. Treat the approved file exactly like any other characterisation
   value: ugly/unreadable output is a `distil_candidates` signal, not a
   defect to fix.

## Guardrail

The agent may propose using an approval tool and may write the capture
call, but **never auto-approves** a `.received` file on its own judgment
— that is the same human checkpoint probe-first already requires for a
hand-transcribed value. Approved files live under the test paths the
guard hook already treats as always-writable (`tests/`, `test/`), so no
scope declaration changes are needed to use one.

## Framework by stack

| Stack | Library | Notes |
|---|---|---|
| JavaScript / TypeScript | **Vitest/Jest built-in snapshots** (`toMatchSnapshot()` / `toMatchInlineSnapshot()`) | Already in the recommended stack (`language-notes.md`) — no new dependency. |
| Python | **syrupy** (pytest-native snapshot plugin) | Idiomatic for the recommended pytest stack. **approvaltests** (Python port of the original ApprovalTests) is the alternative when you want its reporter to pop a visual diff tool. |
| Java / Kotlin | **ApprovalTests Java** (`com.approvaltests:approvaltests`) | Integrates with JUnit 5; works from Kotlin unchanged. |
| Ruby | **approvals** gem (Ruby port of ApprovalTests) or **rspec-snapshot** | Either integrates with RSpec's `describe`/`it`. |
| Go | **goldie** (`github.com/sebdah/goldie`), or the plain `testdata/*.golden` + `-update` idiom | Golden-file testing is already a standard Go convention — goldie is a thin, idiomatic wrapper, not a new paradigm. |
| C++ (Qt) | **ApprovalTests.cpp** | Integrates with the recommended GoogleTest stack (`qt-cpp-notes.md`). |

## Worked example (Python + syrupy)

```python
def test_should_render_pricing_report_for_tier_b(snapshot):
    report = render_pricing_report(load_legacy_catalog(), tier="B")
    assert report == snapshot
```

First run: no snapshot exists, syrupy writes one and fails, showing the
full rendered report. Show it to the user — is this really what tier B
pricing renders today? Agreed → `pytest --snapshot-update` locks it in
as `__snapshots__/test_pricing_report.ambr`, committed alongside the
test. Any future run that changes the report's shape or values fails
with a readable diff instead of a wall of hand-maintained assertions.
