# Python Testing Notes — STUB

> **TODO: distil from real usage.** Fill each section the first time the
> loop hits it in a real slice.

## Toolchain
- Unit: pytest. Doubles: a two-line fake class first; `unittest.mock`
  last. Interfaces: `abc.ABC` or `typing.Protocol` (prefer Protocol —
  structural, no inheritance coupling).
- TODO: project layout convention (src/ vs flat) matching the pipeline.

## Acceptance
- TODO: chosen DSL approach (pytest-bdd vs plain readable pytest with
  given/when/then helpers) — decide on first real acceptance slice.

## Characterisation
- Golden-master via **syrupy** (pytest-native snapshot plugin) for
  wide-output functions — `assert value == snapshot`, approve with
  `pytest --snapshot-update`. Reach for **approvaltests** instead when
  the reporter's pop-up diff tool is wanted. See
  `references/approval-testing.md`.

## Backend-in-Compose
- TODO: acceptance against the docker-compose stack — fixtures for
  bring-up/teardown, contract tests against the Qt client's expectations.
