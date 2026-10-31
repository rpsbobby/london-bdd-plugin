# The decompose map — message template

`/decompose` presents the whole map as **one message the user approves or
edits as a unit**. Use this shape, in this order. Nothing goes into
`session.yml` until the user approves; then `collaborators:` and `tests:`
are written from the approved map.

## Template

1. **Entry point**: the port or method the slice enters through, and what
   implements it.
2. **Roles table**, outside-in. One row per role:

   | # | Role | Kind | Interface | Doubled in its unit tests? |
   |---|---|---|---|---|

   - **Role**: named by capability, in the ubiquitous language.
   - **Kind**: adapter, peer, adapter-internal peer, owned data, or pure
     function.
   - **Interface**: only the methods actually called.
   - **Doubled?**: yes (mock) or no (owned, kept real), with a one-line
     reason. For a type we don't own, say that it is wrapped.
3. **Tests in build order**, grouped by role, as numbered `should_` names,
   one behaviour each. Mark which tests double which peer (in the group
   heading, e.g. *RunStore, with `Cluster` mocked*).
4. **How the outer net turns green**: the wiring that is not a unit test
   (harness, generated files, real adapters, extra adapter-level cases).
5. **To settle**: decisions the map depends on (tooling or config changes,
   and where they land), plus the sanity check result: collaborator count,
   chain depth, and anything you would cut if asked.
6. A closing question: approve, or edit?

## Example (slice `k8s-run-store`)

**Entry point:** `training.RunStore.Save(ctx, Run)`, implemented by the k8s
adapter.

| # | Role | Kind | Interface | Doubled in its unit tests? |
|---|---|---|---|---|
| 1 | `RunStore` (k8s) | Adapter | `Save(ctx, training.Run) error` | n/a, it is the unit under test |
| 2 | `Cluster` | Adapter-internal peer | `Create(ctx, TrainingRun) error` | Yes (mockgen). The real one wraps a client type we don't own. |
| 3 | `TrainingRun` (CRD type) | Owned data | `spec{upload, tier}` | No |
| 4 | `RunName` | Pure function | `RunName(tier, upload) string` | No |

**Tests, in build order**

*RunName*
1. `should_name_a_plain_upload_with_a_slug_and_a_hash`
2. `should_give_the_same_name_for_the_same_tier_and_upload`
3. `should_give_the_same_upload_a_different_name_in_each_tier`
4. `should_turn_an_awkward_upload_name_into_a_valid_name`
5. `should_keep_a_long_upload_name_within_63_characters`

*TrainingRun*

6. `should_keep_the_original_upload_and_tier_in_the_spec`

*RunStore, with `Cluster` mocked*

7. `should_create_the_run_under_its_derived_name`
8. `should_report_already_claimed_when_the_cluster_says_the_run_exists`
9. `should_return_any_other_cluster_error`

**Outer net turns green through wiring:** a k3s test harness, the CRD
installed from generated YAML, the real `Cluster` wrapper, and one extra
adapter-level case (a 300-character upload name).

**To settle:** the lint exemption for kubebuilder marker lines lands in
this slice. Sanity check: three collaborators, two levels deep; `Cluster`
could be cut if the user prefers to test `Save` only against the real
cluster, which would drop tests 7 to 9.

Do you approve this map, or want edits?
