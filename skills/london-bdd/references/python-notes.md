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
- TODO: golden-master via approval files (pytest snapshots) for
  wide-output functions.

## Backend-in-Compose
- TODO: acceptance against the docker-compose stack — fixtures for
  bring-up/teardown, contract tests against the Qt client's expectations.
