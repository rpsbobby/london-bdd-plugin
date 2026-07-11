# Characterisation — Locking In What IS

Legacy code (Feathers' definition): code without tests. A characterisation
test verifies the code does the *current* thing, not the *right* thing.

## Probe-first discovery

1. Write a test with a deliberately wrong assertion.
2. Run it. The failure output reveals the real behaviour.
3. Lock the observed value in as the assertion.
4. Surprises are gold — show every one to the user. Bugs discovered are
   LOGGED (/debt), never fixed during characterisation.

```cpp
// We don't claim 247.50 is correct. We claim it's what the code does today.
TEST(LegacyPricerCharacterisation, CurrentTierBPricing) {
    LegacyPricer pricer(loadLegacyConfig());
    EXPECT_EQ(pricer.calculate("WGT-001", 3, "B"), 247.50);
}
```

## Style rules — deliberately relaxed

- No DSL forced; Given/When/Then only if it falls out naturally.
- Correctness over readability: magic values, long bodies, ugly setups all
  acceptable. **Ugliness = the current model of the behaviour is poor.**
  Flag such tests as `distil_candidates` in session.yml. When the
  behaviour is later understood, rewrite as a proper unit/acceptance test
  and DELETE the ugly one. The suite shrinks by design.

## Dependency-breaking techniques (choose per seam)

| Technique | When |
|---|---|
| **Extract and Override** | Subclass the legacy class in the test, override the problematic method |
| **Parameterise Constructor** | Inject the dependency; default to the real one in production |
| **Parameterise Method** | Same, at method level, for local dependencies |
| **Introduce Seam** | Create the substitution point where none exists (link/preprocessor seams in C++ if unavoidable) |
| **Sprout Method / Class** | NEW behaviour goes in a new, fully tested unit called from legacy — don't grow the untested blob |

## Characterisation as contract for replacement

```
Legacy component
  → characterisation suite (records behaviour)
  → TDD new implementation (suite = outer loop)
  → swap at the seam (suite proves parity)
  → retire legacy + distil suite into real tests
```

## Verification runs

Post-slice, the suite must be green. Red means observable behaviour
changed — the user decides: intended (update the test, record why in the
commit) or regression (fix under the net). Never decide alone; never
delete a test to pass.
