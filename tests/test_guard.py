"""Regression suite for scripts/guard.py — the plugin's own hard rules,
tested the way the plugin asks every other project to test: real
behaviour through the real entry point (subprocess, real git repos), not
mocked internals."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent.parent / "scripts" / "guard.py"


def run_git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True,
                    capture_output=True, text=True)


def init_repo(repo):
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "t@t.com")
    run_git(repo, "config", "user.name", "t")
    run_git(repo, "commit", "-q", "--allow-empty", "-m", "init")


def write_session(repo, **fields):
    bdd = repo / ".bdd"
    bdd.mkdir(exist_ok=True)
    body = "\n".join(f"{k}: {v}" for k, v in fields.items()) + "\n"
    (bdd / "session.yml").write_text(body)


def write_marker(repo, branch, base_branch):
    bdd = repo / ".bdd"
    bdd.mkdir(exist_ok=True)
    (bdd / ".merge-authorized").write_text(
        f"branch: {branch}\nbase_branch: {base_branch}\n")


def guard(repo, kind, command=None, file_path=None):
    tool_input = {}
    if command is not None:
        tool_input["command"] = command
    if file_path is not None:
        tool_input["file_path"] = file_path
    payload = json.dumps({"tool_input": tool_input, "cwd": str(repo)})
    proc = subprocess.run(
        [sys.executable, str(GUARD), kind], input=payload,
        capture_output=True, text=True)
    return proc.returncode, proc.stderr


@pytest.fixture
def repo(tmp_path):
    init_repo(tmp_path)
    return tmp_path


def open_slice(repo, slice_name, phase="inner", mode="GREENFIELD", **extra):
    main_br = f"feature/{slice_name}-main"
    tmp_br = f"feature/{slice_name}-tmp"
    run_git(repo, "branch", "-M", main_br)
    run_git(repo, "checkout", "-q", "-b", tmp_br)
    fields = dict(slice=slice_name, mode=mode, phase=phase,
                  branch=tmp_br, base_branch=main_br, **extra)
    write_session(repo, **fields)
    run_git(repo, "add", ".bdd/session.yml")
    run_git(repo, "commit", "-q", "-m", "session")
    return main_br, tmp_br


# ---- Rule A: production edit requires a license ----------------------

def test_blocks_production_edit_with_no_failing_test(repo):
    open_slice(repo, "x")
    (repo / "src").mkdir()
    code, err = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 2
    assert "Rule A" in err


def test_allows_production_edit_with_recorded_failing_test(repo):
    open_slice(repo, "x", current_failing_test="\n  file: tests/unit/x_test.py\n  name: t")
    code, _ = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 0


def test_allows_edit_under_tests_dir_regardless_of_license(repo):
    open_slice(repo, "x")
    code, _ = guard(repo, "edit", file_path=str(repo / "tests" / "unit" / "x_test.py"))
    assert code == 0


def test_silent_when_no_active_slice(repo):
    (repo / "src").mkdir()
    code, _ = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 0


# ---- Rule B: scope gate (SAFE/FULL_REFACTOR) --------------------------

def test_blocks_edit_outside_declared_scope(repo):
    open_slice(repo, "x", mode="SAFE")
    # char_status must be green to license the edit at all; set scope too
    bdd = repo / ".bdd" / "session.yml"
    bdd.write_text(bdd.read_text() + (
        "characterisation:\n  status: green\n"
        "scope:\n  in:\n    - src/pricing/*\n  out:\n    - src/tax/*\n"
    ))
    code, err = guard(repo, "edit", file_path=str(repo / "src" / "tax" / "table.py"))
    assert code == 2
    assert "Rule B" in err


def test_allows_edit_inside_declared_scope(repo):
    open_slice(repo, "x", mode="SAFE")
    bdd = repo / ".bdd" / "session.yml"
    bdd.write_text(bdd.read_text() + (
        "characterisation:\n  status: green\n"
        "scope:\n  in:\n    - src/pricing/*\n  out:\n    - src/tax/*\n"
    ))
    code, _ = guard(repo, "edit", file_path=str(repo / "src" / "pricing" / "calc.py"))
    assert code == 0


# ---- Rule C: commits ---------------------------------------------------

def test_blocks_commit_off_the_tmp_branch(repo):
    main_br, tmp_br = open_slice(repo, "x")
    run_git(repo, "checkout", "-q", main_br)
    code, err = guard(repo, "bash", command="git commit -m oops")
    assert code == 2
    assert "Rule C" in err


def test_allows_commit_on_the_tmp_branch(repo):
    open_slice(repo, "x")
    code, _ = guard(repo, "bash", command="git commit -m cycle")
    assert code == 0


def test_rebase_always_blocked_even_with_marker(repo):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    write_marker(repo, tmp_br, main_br)
    run_git(repo, "checkout", "-q", main_br)
    code, err = guard(repo, "bash", command="git rebase feature/x-tmp")
    assert code == 2
    assert "rebase" in err.lower()


# ---- Rule C: merges — the auto-merge marker flow ----------------------

def test_blocks_merge_on_slice_main_with_no_marker(repo):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    run_git(repo, "checkout", "-q", main_br)
    code, err = guard(repo, "bash", command=f"git merge --squash {tmp_br}")
    assert code == 2
    assert "Rule C" in err


def test_allows_merge_with_matching_marker(repo):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    write_marker(repo, tmp_br, main_br)
    run_git(repo, "checkout", "-q", main_br)
    # checkout removed .bdd/session.yml (tracked only on tmp) — this is
    # the exact gap the marker exists to survive.
    assert not (repo / ".bdd" / "session.yml").exists()
    assert (repo / ".bdd" / ".merge-authorized").exists()
    code, _ = guard(repo, "bash", command=f"git merge --squash {tmp_br}")
    assert code == 0


def test_blocks_merge_when_marker_names_a_different_tmp_branch(repo):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    write_marker(repo, "feature/other-tmp", main_br)
    run_git(repo, "checkout", "-q", main_br)
    code, err = guard(repo, "bash", command=f"git merge --squash {tmp_br}")
    assert code == 2
    assert "Rule C" in err


def test_allows_landing_commit_after_authorized_merge(repo):
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    write_marker(repo, tmp_br, main_br)
    run_git(repo, "checkout", "-q", main_br)
    run_git(repo, "merge", "--squash", tmp_br)
    code, _ = guard(repo, "bash", command="git commit -m squash")
    assert code == 0


def test_blocks_unauthorized_merge_even_without_any_marker_file(repo):
    """The dangerous case: no session.yml reachable on main (never
    tracked there), no marker at all — must still block, not go silent."""
    main_br, tmp_br = open_slice(repo, "x", phase="done")
    run_git(repo, "checkout", "-q", main_br)
    assert not (repo / ".bdd").exists()
    code, err = guard(repo, "bash", command=f"git merge --squash {tmp_br}")
    assert code == 2
    assert "Rule C" in err


def test_silent_for_unrelated_repo_with_no_slice_at_all(repo):
    run_git(repo, "checkout", "-q", "-b", "main-line")
    code, _ = guard(repo, "bash", command="git merge --squash some-other-branch")
    assert code == 0
