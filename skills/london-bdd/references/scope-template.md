# Refactor Scope Artifact — Template

Written by `/refactor-scope` to `.bdd/scope-<slice>.md`. Scope, never
solution: no class diagrams, no target architecture — design emerges from
the loop.

```markdown
# Scope — <slice name>
**Mode:** SAFE | FULL_REFACTOR
**Mandate:** (FULL_REFACTOR only) agreed with <who/when>
**Driving change:** <the ask, one sentence>
**Net:** existing — <suites, verified green when/how> |
         characterisation — <why existing coverage doesn't qualify>

## In
- src/pricing/LegacyPricer.cpp        — <why it must change>
- src/pricing/LegacyPricer.h

## Out (explicitly untouched, even if ugly)
- src/pricing/TaxTable.cpp            — tempting, logged as TD-014
- src/orders/**                       — adjacent context, separate slice

## Seams
- LegacyPricer::calculate — Parameterise Constructor (config injection)
- LegacyPricer::fetchRates — Extract and Override (network call)

## Blast radius notes
<call sites, known consumers, anything that reads the outputs>
```

Rules of thumb:
- **Net** records a judgment, not an inventory: "existing" means the user
  looked at the suites, agreed they assert outcomes (not implementation),
  and saw them green — then /characterise is skipped. When in doubt,
  characterise the doubtful part only.
- Every "while we're here" temptation lands in **Out** + `/debt`, never
  silently in **In**.
- More than ~5 files in **In** → challenge the slice size.
- **Out** with a reason is more valuable than **In** — it's the record of
  restraint that keeps SAFE mode safe.
