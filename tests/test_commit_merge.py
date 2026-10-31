"""/commit-merge, run the way the command file documents it: the shell
steps are read from commands/commit-merge.md, so the tests follow the doc
rather than a copy of it."""
import re
import subprocess
from pathlib import Path

from test_guard import (  # noqa: F401 (repo is a fixture)
    guard, open_slice, repo, run_git, write_marker)

COMMIT_MERGE = (Path(__file__).resolve().parent.parent
                / "commands" / "commit-merge.md")


def code_block(section, step=None):
    """The first code block of a '## <section>' (or of its numbered step),
    with the slice name and message filled in."""
    text = COMMIT_MERGE.read_text().split(f"## {section}", 1)[1]
    if step is not None:
        text = re.search(rf"^{step}\.(.*?)(?=^\d+\.|\Z)", text,
                         re.S | re.M).group(1)
    m = re.search(r"```\n(.*?)\n\s*```", text, re.S)
    assert m, f"{section} step {step} should hold its commands in a code block"
    return (m.group(1).replace("<slice>", "x")
            .replace("<message>", "squash"))


def sh(repo, script):
    subprocess.run(script, shell=True, cwd=repo, check=True,
                   capture_output=True)


def build_slice(repo, notes=True):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    bdd = repo / ".bdd"
    if notes:
        (bdd / "design-x.md").write_text("# Design — x\n")
        (bdd / "scope-x.md").write_text("# Scope — x\n")
    (bdd / "archive").mkdir()
    (bdd / "archive" / "old.yml").write_text("slice: old\n")
    (repo / "src").mkdir()
    (repo / "src" / "order.py").write_text("ORDER = 1\n")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "slice work")
    return main_br, tmp_br


def land_auto(repo):
    main_br, tmp_br = "feature/x-main", "feature/x-tmp"
    write_marker(repo, tmp_br, main_br)
    run_git(repo, "checkout", "-q", main_br)
    run_git(repo, "merge", "--squash", tmp_br)
    sh(repo, code_block("Auto mode", step=5))
    code, _ = guard(repo, "bash", command="git commit -m squash")
    assert code == 0
    run_git(repo, "commit", "-q", "-m", "squash")


def landed(repo):
    return sorted(subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"], cwd=repo,
        capture_output=True, text=True, check=True).stdout.split())


SLICE_NOTES = ["docs/slices/x/design.md", "docs/slices/x/scope.md"]


def test_auto_mode_keeps_slice_notes_and_drops_the_rest_of_bdd(repo):
    build_slice(repo)
    land_auto(repo)
    assert landed(repo) == SLICE_NOTES + ["src/order.py"]


def test_auto_mode_exclusion_keeps_the_merge_marker(repo):
    build_slice(repo)
    land_auto(repo)
    left = sorted(p.name for p in (repo / ".bdd").iterdir())
    assert left == [".merge-authorized"]


def test_auto_mode_without_notes_lands_only_the_product(repo):
    build_slice(repo, notes=False)
    land_auto(repo)
    assert landed(repo) == ["src/order.py"]
    assert not (repo / "docs").exists()


def test_manual_mode_keeps_slice_notes_and_drops_the_rest_of_bdd(repo):
    build_slice(repo)
    sh(repo, code_block("Manual mode"))
    assert landed(repo) == SLICE_NOTES + ["src/order.py"]
    assert not (repo / ".bdd").exists()


def next_slice_design(repo):
    """/design may run for the next slice once this one is done, before
    /commit-merge: its notes are untracked and must survive the landing."""
    nxt = repo / ".bdd" / "design-next.md"
    nxt.write_text("# Design — next\n")
    return nxt


def test_auto_mode_keeps_the_next_slices_design_notes(repo):
    build_slice(repo)
    nxt = next_slice_design(repo)
    land_auto(repo)
    assert nxt.read_text() == "# Design — next\n"
    assert landed(repo) == SLICE_NOTES + ["src/order.py"]
    left = sorted(p.name for p in (repo / ".bdd").iterdir())
    assert left == [".merge-authorized", "design-next.md"]


def test_manual_mode_keeps_the_next_slices_design_notes(repo):
    build_slice(repo)
    nxt = next_slice_design(repo)
    sh(repo, code_block("Manual mode"))
    assert nxt.read_text() == "# Design — next\n"
    assert landed(repo) == SLICE_NOTES + ["src/order.py"]
    assert sorted(p.name for p in (repo / ".bdd").iterdir()) == [
        "design-next.md"]
