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


def guard_full(repo, kind, command=None, file_path=None):
    tool_input = {}
    if command is not None:
        tool_input["command"] = command
    if file_path is not None:
        tool_input["file_path"] = file_path
    payload = json.dumps({"tool_input": tool_input, "cwd": str(repo)})
    proc = subprocess.run(
        [sys.executable, str(GUARD), kind], input=payload,
        capture_output=True, text=True)
    return proc.returncode, proc.stderr, proc.stdout


def guard(repo, kind, command=None, file_path=None):
    code, err, _stdout = guard_full(repo, kind, command=command,
                                     file_path=file_path)
    return code, err


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


def test_allows_safe_edit_licensed_by_green_existing_net(repo):
    """The net is the license, whatever its kind: a declared existing
    suite licenses green-to-green refactoring without characterisation."""
    open_slice(repo, "x", mode="SAFE",
               **{"net": "\n  kind: existing\n  status: green"})
    code, _ = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 0


def test_allows_safe_edit_licensed_by_legacy_characterisation_block(repo):
    """Pre-net session files (characterisation: block) keep working."""
    open_slice(repo, "x", mode="SAFE",
               **{"characterisation": "\n  status: green"})
    code, _ = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 0


def test_blocks_safe_edit_when_declared_net_is_not_green(repo):
    open_slice(repo, "x", mode="SAFE",
               **{"net": "\n  kind: existing\n  status: absent"})
    code, err = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 2
    assert "Rule A" in err


def test_net_block_overrides_legacy_characterisation_block(repo):
    """When both blocks exist, net: is authoritative — a red net blocks
    even if a stale characterisation block still says green."""
    open_slice(repo, "x", mode="SAFE",
               **{"net": "\n  kind: characterisation\n  status: red",
                  "characterisation": "\n  status: green"})
    code, err = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 2
    assert "Rule A" in err


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


# ---- Rule D: phase transitions can't skip a step ----------------------

def edit_session(repo, new_phase):
    """Simulate an Edit tool call that rewrites the phase: line in
    .bdd/session.yml, the way a command would. Fixture state (collaborators,
    acceptance_test, characterisation) is seeded via open_slice's **extra
    before this is called."""
    bdd = repo / ".bdd" / "session.yml"
    payload = json.dumps({
        "tool_input": {
            "file_path": str(bdd),
            "old_string": "phase: " + _current_phase(bdd),
            "new_string": f"phase: {new_phase}",
        },
        "cwd": str(repo),
    })
    proc = subprocess.run(
        [sys.executable, str(GUARD), "edit"], input=payload,
        capture_output=True, text=True)
    return proc.returncode, proc.stderr


def _current_phase(session_file):
    for line in session_file.read_text().splitlines():
        if line.startswith("phase:"):
            return line.split(":", 1)[1].strip()
    return ""


def test_blocks_phase_moving_backward(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done"})
    code, err = edit_session(repo, "decompose")
    assert code == 2
    assert "Rule D" in err


REVIEW_TEST = ("\n  - name: should_check_on_entry\n    collaborator: A"
               "\n    origin: review\n    status: pending")


def test_allows_close_back_to_inner_with_open_review_test(repo):
    open_slice(repo, "x", phase="close",
               **{"collaborators": "\n  - role: A\n    status: pending",
                  "tests": REVIEW_TEST,
                  "acceptance_test": "\n  status: green"})
    code, _ = edit_session(repo, "inner")
    assert code == 0


def test_blocks_close_back_to_inner_without_review_test(repo):
    open_slice(repo, "x", phase="close",
               **{"collaborators": "\n  - role: A\n    status: done",
                  "tests": "\n  - name: should_a\n    collaborator: A"
                           "\n    origin: planned\n    status: pending"})
    code, err = edit_session(repo, "inner")
    assert code == 2
    assert "origin: review" in err


def test_blocks_close_back_to_inner_when_review_test_already_done(repo):
    open_slice(repo, "x", phase="close",
               **{"collaborators": "\n  - role: A\n    status: done",
                  "tests": REVIEW_TEST.replace("pending", "done")})
    code, _ = edit_session(repo, "inner")
    assert code == 2


def test_blocks_done_back_to_inner_even_with_review_test(repo):
    open_slice(repo, "x", phase="done",
               **{"collaborators": "\n  - role: A\n    status: pending",
                  "tests": REVIEW_TEST})
    code, _ = edit_session(repo, "inner")
    assert code == 2


def test_blocks_close_with_unfinished_collaborator(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: red"})
    code, err = edit_session(repo, "close")
    assert code == 2
    assert "Rule D" in err
    assert "A" in err


def test_blocks_close_with_no_collaborators(repo):
    open_slice(repo, "x", phase="inner")
    code, err = edit_session(repo, "close")
    assert code == 2
    assert "Rule D" in err


def test_allows_close_safe_with_green_existing_net_and_nothing_to_build(repo):
    """Tidy-only slice: the existing green net is the license, no tests or
    collaborators are ever recorded."""
    open_slice(repo, "x", phase="inner", mode="SAFE",
               **{"net": "\n  kind: existing\n  status: green"})
    code, _ = edit_session(repo, "close")
    assert code == 0


def test_blocks_close_safe_with_characterisation_net_and_no_collaborators(repo):
    open_slice(repo, "x", phase="inner", mode="SAFE",
               **{"net": "\n  kind: characterisation\n  status: green"})
    code, err = edit_session(repo, "close")
    assert code == 2
    assert "Rule D" in err


def test_blocks_close_safe_existing_net_with_open_test(repo):
    open_slice(repo, "x", phase="inner", mode="SAFE",
               **{"net": "\n  kind: existing\n  status: green",
                  "tests": "\n  - name: should_a\n    origin: planned"
                           "\n    status: pending"})
    code, err = edit_session(repo, "close")
    assert code == 2
    assert "Rule D" in err


def test_allows_close_when_all_collaborators_done(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done"})
    code, _ = edit_session(repo, "close")
    assert code == 0


def test_allows_close_when_multiword_role_names_are_all_done(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: Camera factory\n    status: done"
                                    "\n  - role: TimerTrigger factory\n    status: done"})
    code, _ = edit_session(repo, "close")
    assert code == 0


def test_blocks_inner_greenfield_with_empty_queue(repo):
    open_slice(repo, "x", phase="decompose", mode="GREENFIELD")
    code, err = edit_session(repo, "inner")
    assert code == 2
    assert "Rule D" in err


def test_blocks_inner_greenfield_without_red_acceptance_test(repo):
    open_slice(repo, "x", phase="decompose", mode="GREENFIELD",
               **{"collaborators": "\n  - role: A\n    status: pending"})
    code, err = edit_session(repo, "inner")
    assert code == 2
    assert "Rule D" in err


def test_allows_inner_greenfield_with_queue_and_red_at(repo):
    open_slice(repo, "x", phase="decompose", mode="GREENFIELD",
               **{"collaborators": "\n  - role: A\n    status: pending",
                  "tests": "\n  - name: should_a\n    collaborator: A"
                           "\n    origin: planned\n    status: pending",
                  "acceptance_test": "\n  status: red"})
    code, _ = edit_session(repo, "inner")
    assert code == 0


def test_blocks_inner_safe_without_green_characterisation(repo):
    open_slice(repo, "x", phase="characterise", mode="SAFE")
    code, err = edit_session(repo, "inner")
    assert code == 2
    assert "Rule D" in err


def test_allows_inner_safe_with_green_characterisation(repo):
    open_slice(repo, "x", phase="characterise", mode="SAFE",
               **{"characterisation": "\n  status: green"})
    code, _ = edit_session(repo, "inner")
    assert code == 0


def test_allows_inner_safe_with_green_existing_net(repo):
    """/refactor-scope declared the existing suites the net — /characterise
    is skipped and the slice may enter inner directly."""
    open_slice(repo, "x", phase="characterise", mode="SAFE",
               **{"net": "\n  kind: existing\n  status: green"})
    code, _ = edit_session(repo, "inner")
    assert code == 0


def test_blocks_inner_safe_when_existing_net_not_verified_green(repo):
    open_slice(repo, "x", phase="characterise", mode="SAFE",
               **{"net": "\n  kind: existing\n  status: absent"})
    code, err = edit_session(repo, "inner")
    assert code == 2
    assert "Rule D" in err


def test_allows_decompose_full_refactor_with_green_existing_net(repo):
    open_slice(repo, "x", phase="characterise", mode="FULL_REFACTOR",
               **{"net": "\n  kind: existing\n  status: green"})
    code, _ = edit_session(repo, "decompose")
    assert code == 0


def test_blocks_done_not_from_close(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done"})
    code, err = edit_session(repo, "done")
    assert code == 2
    assert "Rule D" in err


def test_allows_done_from_close(repo):
    open_slice(repo, "x", phase="close")
    code, _ = edit_session(repo, "done")
    assert code == 0


# ---- Rule D: Bash can't dodge the phase-transition check --------------

def test_blocks_bash_redirect_write_to_session_yml(repo):
    open_slice(repo, "x", phase="inner")
    code, err = guard(repo, "bash",
                       command="echo 'phase: close' > .bdd/session.yml")
    assert code == 2
    assert "Rule D" in err


def test_blocks_bash_tee_write_to_session_yml(repo):
    open_slice(repo, "x", phase="inner")
    code, err = guard(repo, "bash",
                       command="echo 'phase: close' | tee .bdd/session.yml")
    assert code == 2
    assert "Rule D" in err


def test_allows_bash_read_of_session_yml(repo):
    open_slice(repo, "x", phase="inner")
    code, _ = guard(repo, "bash", command="cat .bdd/session.yml")
    assert code == 0


def test_allows_bash_redirect_that_does_not_target_session_yml(repo):
    open_slice(repo, "x", phase="inner")
    code, _ = guard(repo, "bash",
                     command="cat .bdd/session.yml > /tmp/session-copy.yml")
    assert code == 0


def test_silent_bash_write_to_session_yml_when_no_active_slice(repo):
    code, _ = guard(repo, "bash",
                     command="echo 'phase: inner' > .bdd/session.yml")
    assert code == 0


# ---- inner: batch — explicit allow, not just silence -------------------
#
# `inner: granular` sessions are human-paced and rely on Claude Code's
# normal permission prompt for every Edit/Write/Bash call — the guard only
# ever blocks or stays silent. `inner: batch` (the default when the field
# is absent) hands the test list to an unattended builder subagent, so
# once an action survives Rules A-E the guard must say so explicitly (a
# PreToolUse `allow` decision on stdout), not just decline to object.

def test_licensed_edit_stays_silent_when_granular(repo):
    open_slice(repo, "x", inner="granular",
               current_failing_test="\n  file: t.py\n  name: t")
    code, _err, out = guard_full(repo, "edit",
                                  file_path=str(repo / "src" / "order.py"))
    assert code == 0
    assert out == ""


def test_licensed_edit_explicitly_allowed_when_batch(repo):
    open_slice(repo, "x", inner="batch",
               current_failing_test="\n  file: t.py\n  name: t")
    code, _err, out = guard_full(repo, "edit",
                                  file_path=str(repo / "src" / "order.py"))
    assert code == 0
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_absent_inner_field_defaults_to_batch(repo):
    open_slice(repo, "x", current_failing_test="\n  file: t.py\n  name: t")
    code, _err, out = guard_full(repo, "edit",
                                  file_path=str(repo / "src" / "order.py"))
    assert code == 0
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_always_allowed_path_explicitly_allowed_when_batch(repo):
    open_slice(repo, "x", inner="batch")
    code, _err, out = guard_full(
        repo, "edit", file_path=str(repo / "tests" / "unit" / "x_test.py"))
    assert code == 0
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_unlicensed_edit_still_blocked_when_batch(repo):
    """inner: batch licenses nothing by itself — Rule A still gates
    production edits on a recorded failing test."""
    open_slice(repo, "x", inner="batch")
    code, err = guard(repo, "edit", file_path=str(repo / "src" / "order.py"))
    assert code == 2
    assert "Rule A" in err


def test_bash_explicitly_allowed_when_batch(repo):
    open_slice(repo, "x", inner="batch")
    code, _err, out = guard_full(repo, "bash", command="git commit -m cycle")
    assert code == 0
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_rebase_still_blocked_when_batch(repo):
    """Rules A-E are never relaxed by batch mode — it only removes the
    prompt for what the rules already license."""
    main_br, tmp_br = open_slice(repo, "x", phase="done", inner="batch")
    write_marker(repo, tmp_br, main_br)
    run_git(repo, "checkout", "-q", main_br)
    code, err = guard(repo, "bash", command="git rebase feature/x-tmp")
    assert code == 2
    assert "rebase" in err.lower()


def test_no_active_slice_stays_silent(repo):
    """The batch default is a session.yml property — with no session at
    all there is nothing to declare it, so behaviour is unchanged
    (silent, not allow)."""
    (repo / "src").mkdir()
    code, _err, out = guard_full(repo, "edit",
                                  file_path=str(repo / "src" / "order.py"))
    assert code == 0
    assert out == ""


# ---- Rule D: the planned/discovered test list -------------------------
#
# /decompose records a `tests:` list next to the collaborators; batch and
# granular mode both work it. Close is earned by draining that list, not
# just by marking collaborators done.

def yaml_tests(*items):
    """items: (name, collaborator, origin, status) tuples."""
    return "".join(
        f"\n  - name: {n}\n    collaborator: {c}\n    origin: {o}"
        f"\n    status: {s}" for n, c, o, s in items)


def test_blocks_close_with_an_unfinished_planned_test(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done",
                  "tests": yaml_tests(
                      ("should_save", "A", "planned", "done"),
                      ("should_reject_empty", "A", "planned", "pending"))})
    code, err = edit_session(repo, "close")
    assert code == 2
    assert "Rule D" in err
    assert "should_reject_empty" in err


def test_blocks_close_with_an_unfinished_discovered_test(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done",
                  "tests": yaml_tests(
                      ("should_save", "A", "planned", "done"),
                      ("should_handle_duplicate", "A", "discovered", "red"))})
    code, err = edit_session(repo, "close")
    assert code == 2
    assert "should_handle_duplicate" in err


def test_allows_close_when_every_test_is_done(repo):
    open_slice(repo, "x", phase="inner",
               **{"collaborators": "\n  - role: A\n    status: done",
                  "tests": yaml_tests(
                      ("should_save", "A", "planned", "done"),
                      ("should_handle_duplicate", "A", "discovered", "done"))})
    code, _ = edit_session(repo, "close")
    assert code == 0


def test_blocks_inner_greenfield_without_a_planned_test_list(repo):
    open_slice(repo, "x", phase="decompose", mode="GREENFIELD",
               **{"collaborators": "\n  - role: A\n    status: pending",
                  "acceptance_test": "\n  status: red"})
    code, err = edit_session(repo, "inner")
    assert code == 2
    assert "Rule D" in err
    assert "test" in err.lower()


# ---- Rule E: every slice commit runs the checks -----------------------
#
# The repo's own git hooks run on every commit, so the guard's job is to
# stop the agent skipping them. On top of that it runs the tests in the
# slice's scope itself, from session.yml's `checks.tests` template, and
# blocks the commit if they fail.

# Runs each in-scope file as a python script; any non-zero exit fails.
RUN_EACH = "sh -c 'for f; do python3 \"$f\" || exit 1; done' _ {files}"


def write_file(repo, rel, text):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


PASSING = "raise SystemExit(0)\n"
FAILING = "print('boom: expected 2 got 3')\nraise SystemExit(1)\n"


@pytest.mark.parametrize("command", [
    "git commit --no-verify -m cycle",
    "git commit -n -m cycle",
    "git commit -anm cycle",
    "SKIP=ruff git commit -m cycle",
    "git -c core.hooksPath=/dev/null commit -m cycle",
    "HUSKY=0 git commit -m cycle",
])
def test_blocks_commit_that_bypasses_the_repo_hooks(repo, command):
    open_slice(repo, "x")
    code, err = guard(repo, "bash", command=command)
    assert code == 2
    assert "Rule E" in err


def test_allows_commit_whose_message_merely_mentions_no_verify(repo):
    open_slice(repo, "x")
    code, _ = guard(repo, "bash",
                     command='git commit -m "explain -n and --no-verify"')
    assert code == 0


def test_blocks_commit_when_pre_commit_config_has_no_installed_hook(repo):
    write_file(repo, ".pre-commit-config.yaml", "repos: []\n")
    open_slice(repo, "x")
    code, err = guard(repo, "bash", command="git commit -m cycle")
    assert code == 2
    assert "pre-commit install" in err


def test_allows_commit_when_pre_commit_hook_is_installed(repo):
    write_file(repo, ".pre-commit-config.yaml", "repos: []\n")
    write_file(repo, ".git/hooks/pre-commit", "#!/bin/sh\nexit 0\n")
    open_slice(repo, "x")
    code, _ = guard(repo, "bash", command="git commit -m cycle")
    assert code == 0


def test_blocks_commit_when_a_test_changed_in_the_slice_fails(repo):
    open_slice(repo, "x", checks=f"\n  tests: {RUN_EACH}")
    write_file(repo, "tests/test_order.py", FAILING)
    run_git(repo, "add", "tests/test_order.py")
    code, err = guard(repo, "bash", command="git commit -m cycle")
    assert code == 2
    assert "Rule E" in err
    assert "boom: expected 2 got 3" in err


def test_untracked_test_files_are_in_scope(repo):
    """`git add -A && git commit` is one Bash call: the guard sees it
    before the add, so untracked test files must count already."""
    open_slice(repo, "x", checks=f"\n  tests: {RUN_EACH}")
    write_file(repo, "tests/test_order.py", FAILING)
    code, err = guard(repo, "bash", command="git add -A && git commit -m c")
    assert code == 2
    assert "boom" in err


def test_allows_commit_when_the_tests_in_scope_pass(repo):
    open_slice(repo, "x", checks=f"\n  tests: {RUN_EACH}")
    write_file(repo, "tests/test_order.py", PASSING)
    run_git(repo, "add", "tests/test_order.py")
    code, _ = guard(repo, "bash", command="git commit -m cycle")
    assert code == 0


def test_tests_outside_the_slice_are_not_run(repo):
    write_file(repo, "tests/test_legacy.py", FAILING)
    run_git(repo, "add", "tests/test_legacy.py")
    run_git(repo, "commit", "-q", "-m", "legacy")
    open_slice(repo, "x", checks=f"\n  tests: {RUN_EACH}")
    write_file(repo, "tests/test_order.py", PASSING)
    code, _ = guard(repo, "bash", command="git add -A && git commit -m c")
    assert code == 0


def test_red_acceptance_test_is_out_of_scope_during_inner(repo):
    open_slice(repo, "x", phase="inner", checks=f"\n  tests: {RUN_EACH}",
               acceptance_test="\n  file: tests/acceptance/test_place.py"
                               "\n  status: red")
    write_file(repo, "tests/acceptance/test_place.py", FAILING)
    code, _ = guard(repo, "bash", command="git add -A && git commit -m c")
    assert code == 0


def test_acceptance_test_is_in_scope_once_the_slice_closes(repo):
    open_slice(repo, "x", phase="close", checks=f"\n  tests: {RUN_EACH}",
               acceptance_test="\n  file: tests/acceptance/test_place.py"
                               "\n  status: red")
    write_file(repo, "tests/acceptance/test_place.py", FAILING)
    code, err = guard(repo, "bash", command="git add -A && git commit -m c")
    assert code == 2
    assert "boom" in err


def test_safe_net_suites_are_always_in_scope(repo):
    write_file(repo, "tests/char/test_pricing.py", FAILING)
    run_git(repo, "add", "tests/char/test_pricing.py")
    run_git(repo, "commit", "-q", "-m", "net")
    open_slice(repo, "x", mode="SAFE", checks=f"\n  tests: {RUN_EACH}",
               net="\n  kind: existing\n  suites:"
                   "\n    - tests/char/test_pricing.py\n  status: green")
    code, err = guard(repo, "bash", command="git commit -m refactor")
    assert code == 2
    assert "boom" in err


def test_no_checks_template_runs_no_tests(repo):
    open_slice(repo, "x")
    write_file(repo, "tests/test_order.py", FAILING)
    code, _ = guard(repo, "bash", command="git add -A && git commit -m c")
    assert code == 0


# ---- Rule E: {outer_net} keeps the red outer net out of inner commits --

# Always fails, printing what the placeholder became between brackets.
SHOW_OUTER = "sh -c 'echo \"OUTER[$0]\"; exit 1' {outer_net}"
ACCEPTANCE = ("\n  file: tests/acceptance/test_place.py"
              "\n  name: TestPlaceOrder\n  status: red")


def commit_with_outer_net(repo, phase, tpl=SHOW_OUTER, acceptance=ACCEPTANCE):
    open_slice(repo, "x", phase=phase, checks=f"\n  tests: {tpl}",
               acceptance_test=acceptance)
    write_file(repo, "tests/test_order.py", PASSING)
    return guard(repo, "bash", command="git add -A && git commit -m c")


def test_outer_net_is_the_acceptance_test_name_before_close(repo):
    code, err = commit_with_outer_net(repo, "inner")
    assert code == 2
    assert "OUTER[TestPlaceOrder]" in err


def test_outer_net_is_empty_from_close_on(repo):
    code, err = commit_with_outer_net(repo, "close")
    assert code == 2
    assert "OUTER[]" in err


def test_outer_net_is_empty_without_a_recorded_name(repo):
    code, err = commit_with_outer_net(
        repo, "inner", acceptance="\n  file: tests/acceptance/test_place.py")
    assert code == 2
    assert "OUTER[]" in err


def test_outer_net_name_cannot_inject_shell(repo):
    evil = "\"x'; touch pwned; echo '\""
    code, err = commit_with_outer_net(
        repo, "inner", acceptance=f"\n  name: {evil}\n  status: red")
    assert code == 2
    assert not (repo / "pwned").exists()


def test_template_without_outer_net_is_unchanged(repo):
    code, err = commit_with_outer_net(
        repo, "inner", tpl="sh -c 'echo \"FILES[$*]\"; exit 1' _ {files}")
    assert code == 2
    assert "FILES[tests/test_order.py]" in err

