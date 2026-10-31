#!/usr/bin/env python3
"""london-bdd session helper — the preferred writer for .bdd/session.yml.

Subcommands validate the file and make the routine bookkeeping updates the
builder performs, so a hand edit can't leave it malformed (stray keys under
`collaborators:`, a missing `cycle`). Parsing reuses guard.parse_session, so
the helper and the hooks read the file the same way; this adds only the
structural strictness the guard doesn't need.

Every update writes a temp file, validates it, and renames it into place;
an update that would introduce a new problem is refused and the file is
left untouched. `phase:` is never changed here — phase moves stay an
Edit/Write call so guard Rule D (validate_phase_transition) checks them.

Usage:
  session.py validate [path]
  session.py set-test NAME --status S [--file F]
  session.py set-collaborator ROLE --status S [--file F]
  session.py set-failing-test --test-file P --name N [--file F]
  session.py commit-cycle --message M [--file F]
  session.py set-discovery-rounds N [--file F]
"""
import argparse
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402

REQUIRED = ("slice", "mode", "phase", "branch", "base_branch", "cycle")
KNOWN = set(REQUIRED) | {
    "inner", "checks", "acceptance_test", "net", "characterisation",
    "scope", "collaborators", "tests", "discovery_rounds",
    "current_failing_test", "last_commit"}
MODES = ("GREENFIELD", "SAFE", "FULL_REFACTOR")
PHASES = ("scope", "characterise", "scenario", "decompose", "inner",
          "close", "done")
INNER = ("batch", "granular")
COLLAB_STATUS = ("pending", "red", "done")
TEST_STATUS = ("pending", "red", "green", "done")
ORIGINS = ("planned", "discovered", "review")
ACCEPT_STATUS = ("red", "green", "absent")
NET_STATUS = ("red", "green", "absent")


def top_value(text, key):
    m = re.search(rf"^{key}:[ \t]*(.*?)[ \t]*(?:#.*)?$", text, re.M)
    return m.group(1).strip("'\"") if m else None


def block(text, key):
    """Indented body under a top-level `key:` line, or None."""
    m = re.search(rf"^{key}:[ \t]*\n((?:[ \t]+.*\n?|[ \t]*\n)*)", text, re.M)
    return m.group(1) if m else None


def items(body):
    """Split a '- k: v' list body into [{key: value}, ...] (raw strings)."""
    out = []
    for chunk in re.split(r"^[ \t]*-[ \t]*", body, flags=re.M)[1:]:
        out.append(dict(re.findall(r"^[ \t]*(\w+):[ \t]*(.*?)[ \t]*$",
                                   chunk, re.M)))
    return out


def one_of(errors, where, value, allowed):
    if value not in allowed:
        errors.append(f"{where}: '{value}' is not one of "
                      f"{' | '.join(allowed)}")


def problems(text, path):
    """(errors, warnings) for session.yml text."""
    errors, warnings = [], []
    for key in REQUIRED:
        if top_value(text, key) in (None, ""):
            errors.append(f"missing required top-level key '{key}'")
    # structural checks run on the text, so they work on a temp candidate
    cyc = top_value(text, "cycle")
    if cyc is not None and not re.fullmatch(r"\d+", cyc):
        errors.append(f"cycle: '{cyc}' is not an integer")
    if top_value(text, "mode") is not None:
        one_of(errors, "mode", top_value(text, "mode"), MODES)
    if top_value(text, "phase") is not None:
        one_of(errors, "phase", top_value(text, "phase"), PHASES)
    if top_value(text, "inner") is not None:
        one_of(errors, "inner", top_value(text, "inner"), INNER)
    acc = block(text, "acceptance_test")
    if acc is not None:
        m = re.search(r"\bstatus:[ \t]*(\S+)", acc)
        if m:
            one_of(errors, "acceptance_test.status", m.group(1),
                   ACCEPT_STATUS)
    net = block(text, "net")
    if net is not None:
        m = re.search(r"\bstatus:[ \t]*(\S+)", net)
        if m:
            one_of(errors, "net.status", m.group(1), NET_STATUS)
    roles = set()
    collabs = block(text, "collaborators")
    for i, it in enumerate(items(collabs or ""), 1):
        where = f"collaborators[{i}]"
        stray = sorted(set(it) - {"role", "status"})
        if stray:
            errors.append(f"{where}: stray key(s) {', '.join(stray)} "
                          "(only role and status are allowed)")
        for k in ("role", "status"):
            if not it.get(k):
                errors.append(f"{where}: missing '{k}'")
        if it.get("status"):
            one_of(errors, f"{where}.status", it["status"], COLLAB_STATUS)
        if it.get("role"):
            roles.add(it["role"])
    s = guard.parse_session(path)
    if len(s["collaborators"]) != len(items(collabs or "")):
        errors.append("collaborators: the guard's parser reads "
                      f"{len(s['collaborators'])} of "
                      f"{len(items(collabs or ''))} items — each must be "
                      "'- role: X' followed directly by 'status: Y'")
    for i, it in enumerate(items(block(text, "tests") or ""), 1):
        where = f"tests[{i}]"
        stray = sorted(set(it) - {"name", "collaborator", "origin",
                                  "status"})
        if stray:
            errors.append(f"{where}: stray key(s) {', '.join(stray)}")
        for k in ("name", "collaborator", "origin", "status"):
            if not it.get(k):
                errors.append(f"{where}: missing '{k}'")
        if it.get("origin"):
            one_of(errors, f"{where}.origin", it["origin"], ORIGINS)
        if it.get("status"):
            one_of(errors, f"{where}.status", it["status"], TEST_STATUS)
        if it.get("collaborator") and it["collaborator"] not in roles:
            errors.append(f"{where}: collaborator '{it['collaborator']}' "
                          "is not listed under collaborators:")
    for m in re.finditer(r"^([A-Za-z_]\w*):", text, re.M):
        if m.group(1) not in KNOWN:
            warnings.append(f"unknown top-level key '{m.group(1)}'")
    return errors, warnings


def read(path):
    try:
        return open(path, encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"session.py: cannot read {path}: {e.strerror}")


def locate(path):
    if path:
        return path
    found, _ = guard.find_session(os.getcwd())
    return found or os.path.join(".bdd", "session.yml")


def report(errors, warnings, path):
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    return 1 if errors else 0


def cmd_validate(args):
    path = locate(args.path)
    errors, warnings = problems(read(path), path)
    code = report(errors, warnings, path)
    if not code:
        print(f"ok: {path}")
    return code


def write_checked(path, new_text, old_errors=()):
    """Validate new_text; write atomically only if it adds no problem."""
    tmp_dir = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=tmp_dir, prefix=".session-",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        errors, warnings = problems(new_text, tmp)
        fresh = [e for e in errors if e not in old_errors]
        if fresh:
            report(fresh, [], path)
            print(f"refusing to write {path}: update would leave it "
                  "invalid", file=sys.stderr)
            return 1
        os.replace(tmp, path)
        tmp = None
        # problems that predate this update stay visible, not hidden
        report([], warnings, path)
        for e in errors:
            print(f"warning (still present): {e}", file=sys.stderr)
        return 0
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def update(args, edit):
    path = locate(args.file)
    text = read(path)
    old_errors, _ = problems(text, path)
    try:
        new_text = edit(text)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return write_checked(path, new_text, old_errors)


def check_enum(value, allowed, what):
    if value not in allowed:
        raise ValueError(f"{what} '{value}' is not one of "
                         f"{' | '.join(allowed)}")


def edit_item(text, key, field, match, status, what):
    """Set `status` on the list item under `key:` whose `field` == match."""
    m = re.search(rf"^{key}:[ \t]*\n((?:[ \t]+.*\n?|[ \t]*\n)*)", text, re.M)
    if not m:
        raise ValueError(f"no {key}: block in session.yml")
    chunks = re.split(r"(?m)^(?=[ \t]*-[ \t])", m.group(1))
    hit = False
    for i, chunk in enumerate(chunks):
        f = re.search(rf"^[ \t]*(?:-[ \t]*)?{field}:[ \t]*(.*?)[ \t]*$",
                      chunk, re.M)
        if f and f.group(1).strip("'\"") == match:
            new, n = re.subn(r"(^[ \t]*(?:-[ \t]*)?status:[ \t]*)\S+",
                             rf"\g<1>{status}", chunk, count=1, flags=re.M)
            if not n:
                raise ValueError(f"{what} '{match}' has no status line")
            chunks[i] = new
            hit = True
    if not hit:
        raise ValueError(f"no {what} '{match}' in {key}:")
    return text[:m.start(1)] + "".join(chunks) + text[m.end(1):]


def cmd_set_test(args):
    check_enum(args.status, TEST_STATUS, "test status")
    return update(args, lambda t: edit_item(
        t, "tests", "name", args.name, args.status, "test"))


def cmd_set_collaborator(args):
    check_enum(args.status, COLLAB_STATUS, "collaborator status")
    return update(args, lambda t: edit_item(
        t, "collaborators", "role", args.role, args.status, "collaborator"))


def set_top(text, key, line):
    """Replace the single-line top-level `key:` or append it."""
    new, n = re.subn(rf"(?m)^{key}:.*$", lambda _: line, text, count=1)
    if n:
        return new
    return text.rstrip("\n") + "\n" + line + "\n"


def drop_block(text, key):
    """Remove a top-level `key:` line and its indented body."""
    return re.sub(rf"(?m)^{key}:[ \t]*\n(?:[ \t]+.*\n?)*", "", text)


def cmd_commit_cycle(args):
    def edit(text):
        cyc = top_value(text, "cycle")
        n = int(cyc) + 1 if cyc and cyc.isdigit() else 1
        text = drop_block(text, "current_failing_test")
        text = set_top(text, "cycle", f"cycle: {n}")
        return set_top(text, "last_commit",
                       f"last_commit: {json.dumps(args.message)}")
    return update(args, edit)


def cmd_set_failing_test(args):
    def edit(text):
        text = drop_block(text, "current_failing_test")
        return (text.rstrip("\n") + "\ncurrent_failing_test:\n"
                f"  file: {args.test_file}\n  name: {args.name}\n")
    return update(args, edit)


def cmd_set_discovery_rounds(args):
    if args.n not in (0, 1):
        print("error: discovery_rounds must be 0 or 1", file=sys.stderr)
        return 1
    return update(args, lambda t: set_top(
        t, "discovery_rounds", f"discovery_rounds: {args.n}"))


def build_parser():
    p = argparse.ArgumentParser(prog="session.py", description=__doc__,
                                formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        sp = sub.add_parser(name, **kw)
        sp.set_defaults(fn=fn)
        if name != "validate":
            sp.add_argument("--file", help="session.yml path (default: "
                            "nearest .bdd/session.yml)")
        return sp

    v = add("validate", cmd_validate, help="check an existing session.yml")
    v.add_argument("path", nargs="?")
    sp = add("set-test", cmd_set_test, help="set a test's status")
    sp.add_argument("name")
    sp.add_argument("--status", required=True)
    sp = add("set-collaborator", cmd_set_collaborator,
             help="set a collaborator's status")
    sp.add_argument("role")
    sp.add_argument("--status", required=True)
    sp = add("set-failing-test", cmd_set_failing_test,
             help="record current_failing_test")
    sp.add_argument("--test-file", required=True)
    sp.add_argument("--name", required=True)
    sp = add("commit-cycle", cmd_commit_cycle,
             help="cycle += 1, set last_commit, clear current_failing_test")
    sp.add_argument("--message", required=True)
    sp = add("set-discovery-rounds", cmd_set_discovery_rounds,
             help="set discovery_rounds (0|1)")
    sp.add_argument("n", type=int)
    return p


def main():
    args = build_parser().parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
