---
name: commit-merge
description: Land the slice — squash-merge feature/<slice>-tmp onto feature/<slice>-main. Manual by default (prints the commands for the developer to run); `--auto` lets the agent run the merge itself, authorized fresh each invocation via an untracked marker file. Runs after /review, when phase is done.
---

# /commit-merge — Land the Slice

## Preconditions

1. `.bdd/session.yml`: `phase: done` (set by `/review`'s final step).
   Otherwise STOP and tell the user which command is expected first.
2. On `feature/<slice>-tmp`, working tree clean. One exception: an
   untracked `.bdd/design-<next>.md` that `/design` wrote for a later
   slice (it may run once this one is `done`). The cleanup below leaves
   it in place for that slice's `/scenario`.

## Build the summary (both modes)

From session.yml — `cycle`, `last_commit`, the collaborator list, the
acceptance test / characterisation status — draft:

- The squash-merge commit message (behaviours delivered; not a raw
  cycle-by-cycle log).
- The exact commands (shown below).

## Manual mode (default: `/commit-merge`)

Print the summary and:
```
git checkout feature/<slice>-main
git merge --squash feature/<slice>-tmp
for n in design scope review; do
  [ -f .bdd/$n-<slice>.md ] || continue
  mkdir -p docs/slices/<slice> && cp .bdd/$n-<slice>.md docs/slices/<slice>/$n.md
done; [ -d docs/slices/<slice> ] && git add docs/slices/<slice>
git restore --staged .bdd/ 2>/dev/null
find .bdd -mindepth 1 ! -path '.bdd/design-*.md' -delete
rm -f .bdd/design-<slice>.md; rmdir .bdd 2>/dev/null || true
git commit -m "<message>"
```
The loop keeps the slice's design, scope and review notes in
`docs/slices/<slice>/` (`design.md`, `scope.md`, `review.md`, whichever
exist), so they outlive the disposable tmp branch; the rest of `.bdd/`
stays out. The `find` spares other slices' design notes: `/design` may
already have written the next one's. Do not run them. Tell the user this
is theirs to run by hand, and that `feature/<slice>-tmp` is disposable
once merged — delete it whenever.

## Auto mode (`/commit-merge --auto`)

The `--auto` flag itself is the developer's authorization for this run —
no additional y/n prompt. There is no persisted "always auto": omit the
flag next time and it's manual again.

**Why the exact order matters:** `git checkout feature/<slice>-main`
removes `.bdd/session.yml` from the working tree (it's tracked only on
the tmp branch) — so session.yml can't carry the authorization across the
branch switch. Instead, drop an **untracked** marker before checking out;
untracked files survive `git checkout` because there's nothing to
reconcile against the target branch's tree.

1. Show the summary and commands.
2. While still on feature/<slice>-tmp, write `.bdd/.merge-authorized`
   (plain text, **do not `git add` it**):
   ```
   branch: feature/<slice>-tmp
   base_branch: feature/<slice>-main
   ```
3. `git checkout feature/<slice>-main`
4. `git merge --squash feature/<slice>-tmp`
5. Keep the slice's notes, drop its bookkeeping. The design, scope and
   review notes are copied to `docs/slices/<slice>/` and land with the
   slice, since `feature/<slice>-tmp` is disposable. The rest of `.bdd/`
   (session.yml, the archive) stays out, as in manual mode, except the
   untracked marker, which the next step still needs, and other slices'
   design notes, which `/design` may already have written:
   ```
   for n in design scope review; do
     [ -f .bdd/$n-<slice>.md ] || continue
     mkdir -p docs/slices/<slice> && cp .bdd/$n-<slice>.md docs/slices/<slice>/$n.md
   done; [ -d docs/slices/<slice> ] && git add docs/slices/<slice>
   git restore --staged .bdd/ 2>/dev/null
   find .bdd -mindepth 1 ! -path .bdd/.merge-authorized ! -path '.bdd/design-*.md' -delete
   rm -f .bdd/design-<slice>.md
   ```
6. `git commit -m "<message>"`
7. Clean up: `rm -f .bdd/.merge-authorized; rmdir .bdd 2>/dev/null || true`.
8. **Never push.** Pushing to a remote is always the developer's own
   action, in every mode.
9. Report the result (commit hash, files, behaviours) and remind the user
   `feature/<slice>-tmp` is disposable.

If step 4 conflicts, STOP — do not attempt automatic resolution. Report
the conflict, run `rm -f .bdd/.merge-authorized` to withdraw the
authorization, and hand back to the user to resolve and commit by hand.

The guard hook independently re-checks steps 4 and 6: it only allows
`git merge --squash <tmp>` and the following `git commit` while the
current branch matches `.bdd/.merge-authorized`'s `base_branch` and the
squash source matches its `branch`. It does not (and cannot, since
session.yml is gone by then) re-check `phase: done` — that precondition
is this command's responsibility, checked once, before the marker is
ever written.

## Rules

- Never merge or rebase anything other than the slice's own tmp→main pair.
- Never run outside `phase: done`.
- Never push, in either mode.
- If the outer net or slice-level review isn't actually closed (phase
  isn't `done`), refuse and point at `/review`.
