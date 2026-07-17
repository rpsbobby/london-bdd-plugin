"""Regression suite for scripts/next.py — the deterministic 'what's next'
lookup, tested through the real entry point against real temp git repos,
matching test_guard.py's conventions."""
import subprocess
import sys
from pathlib import Path

from test_guard import init_repo, open_slice  # noqa: F401 (fixture reuse)

NEXT = Path(__file__).resolve().parent.parent / "scripts" / "next.py"


def run_next(repo):
    proc = subprocess.run(
        [sys.executable, str(NEXT), str(repo)],
        capture_output=True, text=True)
    return proc.stdout.strip()


def test_no_session_suggests_slice_entry_points(tmp_path):
    init_repo(tmp_path)
    out = run_next(tmp_path)
    assert "/scenario" in out
    assert "/refactor-scope" in out


def test_phase_characterise_suggests_characterise(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="characterise", mode="SAFE")
    out = run_next(tmp_path)
    assert out.startswith("next: /characterise")


def test_phase_decompose_suggests_decompose(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="decompose", mode="GREENFIELD")
    out = run_next(tmp_path)
    assert out.startswith("next: /decompose")


def test_phase_inner_with_pending_collaborator_names_it(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="inner",
               **{"collaborators": "\n  - role: OrderRepository\n    status: pending"})
    out = run_next(tmp_path)
    assert out.startswith("next: /inner")
    assert "OrderRepository" in out


def test_phase_inner_with_recorded_failing_test(tmp_path):
    init_repo(tmp_path)
    open_slice(
        tmp_path, "x", phase="inner",
        **{"collaborators": "\n  - role: OrderRepository\n    status: pending",
           "current_failing_test": "\n  file: tests/unit/x_test.py\n  name: t"})
    out = run_next(tmp_path)
    assert out.startswith("next: /inner")
    assert "failing test" in out


def test_phase_inner_with_all_collaborators_done_flags_review(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done"})
    out = run_next(tmp_path)
    assert out.startswith("next: /review")


def test_phase_close_suggests_review(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="close")
    out = run_next(tmp_path)
    assert out.startswith("next: /review")


def test_phase_done_suggests_commit_merge(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="done")
    out = run_next(tmp_path)
    assert out.startswith("next: /commit-merge")
