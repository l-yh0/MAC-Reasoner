"""Helpers for instrumenting translated Z3 programs and collecting symbolic evidence."""

import z3
import re
import json
import subprocess
import tempfile
import os

# Inject this helper code ahead of the translated program to capture solver-derived evidence.
TRACK_CODE = '''from z3 import *
import sys

# Global registry for tracked solver instances
solver_pool = []


class TrackedSolver(Solver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        solver_pool.append(self)
        self._tracked_assertions = []
        self.set("unsat_core", True)

    def add(self, *assertions):
        """
        Override add() so each assertion is paired with a fresh tracking Boolean.
        """
        flattened = []
        for a in assertions:
            if isinstance(a, (list, tuple)):
                flattened.extend(a)
            else:
                flattened.append(a)
        for assertion in flattened:
            if assertion is not None and is_expr(assertion):
                tid = Bool(f"track_{len(self._tracked_assertions)}")
                super().assert_and_track(assertion, tid)
                self._tracked_assertions.append((tid, assertion))

    def assertions(self):
        return [a for _, a in self._tracked_assertions]


def extract_vars_from_assertions(assertions):
    seen = set()

    def walk(e):
        if is_const(e) and e.decl().kind() == Z3_OP_UNINTERPRETED:
            seen.add(e)
        for c in e.children():
            walk(c)
    for a in assertions:
        walk(a)
    return list(seen)


def extract_apps_from_assertions(assertions):
    """Collect all uninterpreted function applications with concrete args."""
    seen = []
    seen_set = set()

    def walk(e):
        if is_app(e) and e.num_args() > 0 and e.decl().kind() == Z3_OP_UNINTERPRETED:
            if e not in seen_set:
                seen.append(e)
                seen_set.add(e)
        for c in e.children():
            walk(c)
    for a in assertions:
        walk(a)
    return seen


def explain_solver_instance(solver, label=""):
    print(f"--- Checking Solver: {label or 'Tracked'} ---", file=sys.stderr)
    assertions = solver.assertions()

    # Collect the symbolic entities referenced by this solver instance.
    vars_in_use = extract_vars_from_assertions(assertions)
    apps_in_use = extract_apps_from_assertions(assertions)

    # Evaluate the branch and print the evidence needed by the Summarizer stage.
    result = solver.check()
    print(f"[Result] {result}", file=sys.stderr)

    if result == sat:
        m = solver.model()
        print("[Solution Constants]", file=sys.stderr)
        for v in vars_in_use:
            try:
                val = m.eval(v, model_completion=True)
                print(f"{v} = {val}", file=sys.stderr)
            except:
                print(f"{v} = Unbound", file=sys.stderr)
        if apps_in_use:
            print("[Solution Function Applications] (last 60 shown)",
                  file=sys.stderr)
            for app in apps_in_use[-60:]:
                try:
                    val = m.eval(app, model_completion=True)
                    print(f"{app} = {val}", file=sys.stderr)
                except:
                    print(f"{app} = Unbound", file=sys.stderr)

    elif result == unsat:
        print("[Unsatisfiable Core]", file=sys.stderr)
        try:
            core = solver.unsat_core()
            if core:
                outs = [
                    a for (tid, a) in solver._tracked_assertions if tid in core]
                for i, a in enumerate(outs):
                    print(f"  [{i+1}] {a}", file=sys.stderr)
            else:
                print("Core extraction unavailable", file=sys.stderr)
        except:
            print("Unable to analyze unsatisfiability reason", file=sys.stderr)
    else:
        print("[Undetermined]", file=sys.stderr)
        print(f"Reason: {solver.reason_unknown()}", file=sys.stderr)


def explain_all_tracked_solvers():
    if not solver_pool:
        print("No tracked Solver instances.", file=sys.stderr)
    for idx, s in enumerate(solver_pool):
        explain_solver_instance(s, label=f"Solver#{idx}")
'''


def track_solver(code: str):
    """Run the translated program with instrumentation and return solver-derived evidence."""
    code = code.replace("Solver()", "TrackedSolver()")
    program = TRACK_CODE + code + "\nexplain_all_tracked_solvers()"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmpfile:
        tmpfile.write(program)
        tmpfile_path = tmpfile.name
    timeout = 120
    try:
        result = subprocess.run(
            ["python", tmpfile_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return result.stderr
    except subprocess.TimeoutExpired:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return "Error: Execution timed out after {} seconds.".format(timeout)
    except subprocess.CalledProcessError as e:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return e.stderr
    except Exception as e:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return "Error: {}".format(str(e))
