"""/commit-merge --auto, run the way the command file documents it: the
exclusion step is read from commands/commit-merge.md, so the test follows
the doc rather than a copy of it."""
import re
import subprocess
from pathlib import Path

from test_guard import (  # noqa: F401 (repo is a fixture)
    guard, open_slice, repo, run_git, write_marker)

COMMIT_MERGE = (Path(__file__).resolve().parent.parent
                / "commands" / "commit-merge.md")


def auto_exclusion_step():
    """The shell line of auto mode's step 5 (exclude .bdd/ bookkeeping)."""
    auto = COMMIT_MERGE.read_text().split("## Auto mode", 1)[1]
    m = re.search(r"^5\..*?```\n(.*?)\n\s*```", auto, re.S | re.M)
    assert m, "auto mode step 5 should hold the exclusion in a code block"
    return m.group(1).strip()


def land_slice_with_bookkeeping(repo):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    bdd = repo / ".bdd"
    (bdd / "design-x.md").write_text("# Design — x\n")
    (bdd / "scope-x.md").write_text("# Scope — x\n")
    (bdd / "archive").mkdir()
    (bdd / "archive" / "old.yml").write_text("slice: old\n")
    (repo / "src").mkdir()
    (repo / "src" / "order.py").write_text("ORDER = 1\n")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "slice work")
    write_marker(repo, tmp_br, main_br)
    run_git(repo, "checkout", "-q", main_br)
    run_git(repo, "merge", "--squash", tmp_br)
    subprocess.run(auto_exclusion_step(), shell=True, cwd=repo, check=True)
    return main_br, tmp_br


def test_auto_mode_lands_no_bdd_bookkeeping(repo):
    land_slice_with_bookkeeping(repo)
    code, _ = guard(repo, "bash", command="git commit -m squash")
    assert code == 0
    run_git(repo, "commit", "-q", "-m", "squash")
    landed = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"], cwd=repo,
        capture_output=True, text=True, check=True).stdout.split()
    assert landed == ["src/order.py"]


def test_auto_mode_exclusion_keeps_the_merge_marker(repo):
    land_slice_with_bookkeeping(repo)
    left = sorted(p.name for p in (repo / ".bdd").iterdir())
    assert left == [".merge-authorized"]
