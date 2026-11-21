# -*- coding: utf-8 -*-
"""
COMP3070 Symbolic AI - Coursework 2
Workflow Satisfiability Problem (WSP) solver.

Problem (Appendix 1): given steps S, users U and constraints, find an
assignment pi : S -> U (every step gets exactly one user) that satisfies
every constraint, or report that none exists. If one exists, also report
whether it is the only one.

Requirements
    Python 3.9+, pip install ortools z3-solver
    (OR-Tools for approach A; Z3 only for approaches B, C and --explain.)

Use from Python (the CW2 template interface)
    from coursework02 import Solver, transform_output
    d = Solver("instances/example3.txt")          # dict: sat, sol, mul_sol, exe_time
    print(transform_output(d))
    Optional keyword arguments of Solver():
        silent=True        do not print the file name
        method='cpsat'     'cpsat' (A, default) | 'z3-bool' (B) | 'z3-int' (C)
        amk='pattern'      At-most-k encoding: 'pattern' (default) | 'users'
        timeout=None       seconds per solve; None = no limit (default)
        optimise=False     E4: return a solution with the fewest users

Use from the command line
    python coursework02.py FILES/FOLDERS [options]
        (no option)        solve and print each instance in the template format
        --test             compare every instance with its known answer
                           (-solution.txt or the Appendix 1 table) and run
                           the independent checker on every solution
        --explain          for unsat instances, print a minimal set of input
                           lines that clash (Z3 unsat core)
        --bench OUT.csv    benchmark: one CSV row per instance x approach;
                           use --methods a,b and --amks a,b to choose
        --method M --amk E --timeout T --optimise   as in Solver() above
    Examples
        python coursework02.py instances/example3.txt
        python coursework02.py instances additional-examples --test --timeout 60
        python coursework02.py instances --test --method z3-int --timeout 60
        python coursework02.py our-instances --test
        python coursework02.py instances/example2.txt --explain
        python coursework02.py instances --bench results.csv --methods cpsat,z3-int

Three solution approaches
    A  cpsat    OR-Tools CP-SAT, Boolean formulation  x[s, u] = 1 <=> pi(s) = u
    B  z3-bool  Z3, the identical Boolean formulation (fair solver comparison)
    C  z3-int   Z3, integer formulation               a[s] = u    <=> pi(s) = u
    (brute      exhaustive search; a testing oracle for tiny instances only)
At-most-k has two encodings: 'pattern' (user-independent, default) and
'users' (one helper per user).

Constraints
    Appendix 1:  C1 Authorisations    C2 Separation-of-duty   C3 Binding-of-duty
                 C4 At-most-k         C5 One-team
    Our extras (optional lines in an instance file):
                 E1 At-least-k k s...          E2 Max-workload L
                 E3 Conditional s1 u1 s2 u2    (if u1 does s1, u2 must not do s2)
                 E4 Minimise-users             (objective; also optimise=True)

File layout (sections)
    2 Instance data      3 Parser               4 Solver back-ends
    5 Boolean model      6 Integer model        7-8 Solve + uniqueness
    9 Solver()           10 transform_output    11 Independent checker
    12 Test runner       12b Benchmark          13 Command line

Credits
    - The Solver(filename, **kwargs) interface, the returned dict keys and
      the output strings follow the COMP3070 CW2 template (module convenor).
    - transform_output() is copied unchanged from the COMP3070 CW2 Helper.
    - The pattern (user-independent) idea for At-most-k follows the WSP
      literature on user-independent constraints (Karapetyan et al., 2019).
    Everything else is our own work.
"""

from __future__ import annotations

import argparse
import itertools
import os
import re
import sys
from dataclasses import dataclass, field
from time import perf_counter, time as currenttime
from typing import Dict, List, Optional, Set, Tuple

try:
    from ortools.sat.python import cp_model
except ImportError:  # lets the parser and checker run without OR-Tools
    cp_model = None
try:
    import z3
except ImportError:  # only needed for approaches B and C
    z3 = None


# =============================================================================
# Section 2 - Instance data class
# =============================================================================
@dataclass
class Instance:
    """All data of one WSP instance. Steps and users are 0-based internally.

    auth:       user -> set of steps the user may perform. A user with no
                entry may perform any step (Appendix 1). An empty set means
                the user may perform no step at all.
    sod:        pairs (s1, s2) that must get different users.
    bod:        pairs (s1, s2) that must get the same user.
    at_most_k:  (k, steps): at most k distinct users over those steps.
    one_team:   (steps, teams): all those steps go to members of one team.

    Extra constraints (our own, optional lines in the instance file):
    at_least_k:     (k, steps): at least k distinct users over those steps.
    max_workload:   L: no user performs more than L steps (None = no limit).
    conditional:    (s1, u1, s2, u2): if u1 does s1 then u2 must not do s2.
    minimise_users: find a solution that uses as few distinct users as possible.
    """

    n_steps: int
    n_users: int
    auth: Dict[int, Set[int]] = field(default_factory=dict)
    sod: List[Tuple[int, int]] = field(default_factory=list)
    bod: List[Tuple[int, int]] = field(default_factory=list)
    at_most_k: List[Tuple[int, List[int]]] = field(default_factory=list)
    one_team: List[Tuple[List[int], List[List[int]]]] = field(default_factory=list)
    at_least_k: List[Tuple[int, List[int]]] = field(default_factory=list)
    max_workload: Optional[int] = None
    conditional: List[Tuple[int, int, int, int]] = field(default_factory=list)
    minimise_users: bool = False
    # (kind, index) -> original input line, used to explain unsat answers
    source: Dict[Tuple[str, int], str] = field(default_factory=dict)
    # (kind, index) -> position of that line in the file, to keep file order
    line_no: Dict[Tuple[str, int], int] = field(default_factory=dict)

    def is_authorised(self, s: int, u: int) -> bool:
        """True if user u is allowed to perform step s (constraint C1)."""
        return u not in self.auth or s in self.auth[u]

    def candidates(self) -> List[List[int]]:
        """For every step, the users allowed to perform it under C1."""
        return [[u for u in range(self.n_users) if self.is_authorised(s, u)]
                for s in range(self.n_steps)]


# =============================================================================
# Section 3 - Parser
# =============================================================================
_HEADER = re.compile(r"#\s*(steps|users|constraints)\s*:\s*(\d+)", re.IGNORECASE)
_STEP = re.compile(r"s(\d+)", re.IGNORECASE)
_USER = re.compile(r"u(\d+)", re.IGNORECASE)
_FIRST_INT = re.compile(r"^\s*(\d+)")
_TEAM = re.compile(r"\(([^)]*)\)")
_TOKEN = re.compile(r"([su])(\d+)", re.IGNORECASE)


def _steps(text: str) -> List[int]:
    """All step numbers in text, converted to 0-based."""
    return [int(n) - 1 for n in _STEP.findall(text)]


def _users(text: str) -> List[int]:
    """All user numbers in text, converted to 0-based."""
    return [int(n) - 1 for n in _USER.findall(text)]


def parse_instance(path: str) -> Instance:
    """Read an instance file in the Appendix 1 format.

    Follows the format rules: keywords are case-insensitive, extra spaces
    are ignored, and numbers are extracted with patterns (s12, u7) rather
    than by splitting on single spaces.
    """
    header: Dict[str, int] = {}
    body: List[str] = []
    with open(path, encoding="utf-8-sig") as f:   # tolerate a byte-order mark
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m = _HEADER.match(line)
            if m:
                header[m.group(1).lower()] = int(m.group(2))
            else:
                body.append(line)

    inst = Instance(n_steps=header["steps"], n_users=header["users"])

    for number, line in enumerate(body):
        known = set(inst.source)
        keyword, _, rest = line.partition(" ")
        keyword = keyword.lower()

        if keyword in ("authorisations", "authorizations"):
            u = _users(rest)[0]
            inst.auth[u] = set(_steps(rest))
            inst.source["auth", u] = line

        elif keyword == "separation-of-duty":
            s1, s2 = _steps(rest)
            inst.source["sod", len(inst.sod)] = line
            inst.sod.append((s1, s2))

        elif keyword == "binding-of-duty":
            s1, s2 = _steps(rest)
            inst.source["bod", len(inst.bod)] = line
            inst.bod.append((s1, s2))

        elif keyword == "at-most-k":
            k = int(_FIRST_INT.match(rest).group(1))
            inst.source["at-most-k", len(inst.at_most_k)] = line
            inst.at_most_k.append((k, _steps(rest)))

        elif keyword == "one-team":
            steps_part = rest.split("(", 1)[0]
            teams = [_users(t) for t in _TEAM.findall(rest)]
            inst.source["one-team", len(inst.one_team)] = line
            inst.one_team.append((_steps(steps_part), teams))

        # --- extra constraints (our own) ---
        elif keyword == "at-least-k":
            k = int(_FIRST_INT.match(rest).group(1))
            inst.source["at-least-k", len(inst.at_least_k)] = line
            inst.at_least_k.append((k, _steps(rest)))

        elif keyword == "max-workload":
            inst.max_workload = int(_FIRST_INT.match(rest).group(1))
            inst.source["max-workload", 0] = line

        elif keyword == "conditional":
            (_, s1), (_, u1), (_, s2), (_, u2) = _TOKEN.findall(rest)
            inst.source["conditional", len(inst.conditional)] = line
            inst.conditional.append((int(s1) - 1, int(u1) - 1,
                                     int(s2) - 1, int(u2) - 1))

        elif keyword in ("minimise-users", "minimize-users"):
            inst.minimise_users = True

        else:
            raise ValueError(f"{path}: unknown constraint line: {line!r}")

        for tag in set(inst.source) - known:      # the tag this line created
            inst.line_no[tag] = number

    return inst


# =============================================================================
# Section 4 - Solver back-ends (CP-SAT and Z3) behind one small interface
# =============================================================================
# The Boolean model (Section 5) only talks to a back-end through these
# methods, so approaches A and B build *exactly the same* model and differ
# only in the solver underneath. That makes the A-vs-B comparison fair.

def _now_ms() -> float:
    """High-resolution clock in milliseconds (perf_counter), so sub-millisecond
    solves are measured instead of rounding to 0 ms."""
    return perf_counter() * 1000


class CpSatBackend:
    """Back-end for approach A: OR-Tools CP-SAT."""

    def __init__(self):
        if cp_model is None:
            raise ImportError("OR-Tools is not installed: pip install ortools")
        self.model = cp_model.CpModel()
        self.solver = None

    def new_bool(self, name: str = ""):
        """A fresh Boolean variable."""
        return self.model.NewBoolVar(name)

    def neg(self, lit):
        """The negation of a literal."""
        return lit.Not()

    def exactly_one(self, lits) -> None:
        """Exactly one of the literals is true."""
        self.model.AddExactlyOne(lits)

    def at_most_one(self, lits) -> None:
        """At most one of the literals is true."""
        self.model.AddAtMostOne(lits)

    def clause(self, lits) -> None:
        """At least one of the literals is true (a clause)."""
        self.model.AddBoolOr(lits)

    def implies(self, a, b) -> None:
        """If a is true then b is true."""
        self.model.AddImplication(a, b)

    def equal(self, a, b) -> None:
        """a and b take the same truth value."""
        self.model.Add(a == b)

    def false(self, a) -> None:
        """Literal a is false."""
        self.model.Add(a == 0)

    def sum_le(self, lits, k: int) -> None:
        """At most k of the literals are true."""
        if lits:
            self.model.Add(sum(lits) <= k)

    def sum_ge(self, lits, k: int) -> None:
        """At least k of the literals are true (a contradiction if fewer than k exist)."""
        if len(lits) < k:                  # can never reach k: contradiction
            self.clause([self.false_lit()])
        elif k > 0:
            self.model.Add(sum(lits) >= k)

    def false_lit(self):
        """A literal that is always false."""
        v = self.new_bool()
        self.false(v)
        return v

    def minimise(self, lits) -> None:
        """Objective (E4): make as few of the literals true as possible."""
        self.model.Minimize(sum(lits))

    def solve(self, timeout: Optional[float]) -> str:
        """Returns 'sat' | 'unsat' | 'unknown' (time limit reached).

        CP-SAT catches Ctrl+C and just stops the search; an early stop that
        is not a time-out is turned back into KeyboardInterrupt."""
        self.solver = cp_model.CpSolver()
        if timeout:
            self.solver.parameters.max_time_in_seconds = timeout
        status = self.solver.Solve(self.model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return "sat"
        if status == cp_model.INFEASIBLE:
            return "unsat"
        if status == cp_model.MODEL_INVALID:
            raise RuntimeError("CP-SAT model is invalid: " + self.model.Validate())
        if timeout is None or self.solver.WallTime() < 0.95 * timeout:
            raise KeyboardInterrupt
        return "unknown"

    def value(self, lit) -> bool:
        """Truth value of a literal in the last solution found."""
        return self.solver.BooleanValue(lit)


def _z3_check(solver, timeout: Optional[float]) -> str:
    """Run a Z3 check: 'sat' | 'unsat' | 'unknown' (time limit reached)."""
    if timeout:
        solver.set("timeout", int(timeout * 1000))
    start = currenttime()
    result = solver.check()
    if result == z3.sat:
        return "sat"
    if result == z3.unsat:
        return "unsat"
    if timeout and currenttime() - start >= 0.95 * timeout:
        return "unknown"
    reason = solver.reason_unknown()
    if "cancel" in reason or "interrupt" in reason:   # Ctrl+C
        raise KeyboardInterrupt
    raise RuntimeError("Z3 returned unknown: " + reason)


class Z3Backend:
    """Back-end for approach B: the Z3 SMT solver, Boolean variables."""

    def __init__(self, optimise: bool = False):
        if z3 is None:
            raise ImportError("Z3 is not installed: pip install z3-solver")
        # z3.Optimize is only needed for E4 (minimise users); it is slower
        # than z3.Solver for plain satisfiability, so it is used only then.
        self.solver = z3.Optimize() if optimise else z3.Solver()
        self.model = None
        self._count = 0

    def new_bool(self, name: str = ""):
        """A fresh Boolean variable."""
        self._count += 1
        return z3.Bool(name or f"aux{self._count}")

    def neg(self, lit):
        """The negation of a literal."""
        return z3.Not(lit)

    def exactly_one(self, lits) -> None:
        """Exactly one of the literals is true."""
        self.solver.add(z3.PbEq([(l, 1) for l in lits], 1))

    def at_most_one(self, lits) -> None:
        """At most one of the literals is true."""
        self.solver.add(z3.PbLe([(l, 1) for l in lits], 1))

    def clause(self, lits) -> None:
        """At least one of the literals is true (a clause)."""
        lits = list(lits)
        self.solver.add(lits[0] if len(lits) == 1 else z3.Or(lits))

    def implies(self, a, b) -> None:
        """If a is true then b is true."""
        self.solver.add(z3.Implies(a, b))

    def equal(self, a, b) -> None:
        """a and b take the same truth value."""
        self.solver.add(a == b)

    def false(self, a) -> None:
        """Literal a is false."""
        self.solver.add(z3.Not(a))

    def sum_le(self, lits, k: int) -> None:
        """At most k of the literals are true."""
        if lits:
            self.solver.add(z3.PbLe([(l, 1) for l in lits], k))

    def sum_ge(self, lits, k: int) -> None:
        """At least k of the literals are true (a contradiction if fewer than k exist)."""
        if len(lits) < k:                  # can never reach k: contradiction
            self.solver.add(z3.BoolVal(False))
        elif k > 0:
            self.solver.add(z3.PbGe([(l, 1) for l in lits], k))

    def minimise(self, lits) -> None:
        """Objective (E4): make as few of the literals true as possible."""
        self.solver.minimize(z3.Sum([z3.If(l, 1, 0) for l in lits]))

    def solve(self, timeout: Optional[float]) -> str:
        """Solve: 'sat' | 'unsat' | 'unknown' (time limit reached); keeps the model."""
        status = _z3_check(self.solver, timeout)
        if status == "sat":
            self.model = self.solver.model()
        return status

    def value(self, lit) -> bool:
        """Truth value of a literal in the last solution found."""
        return z3.is_true(self.model.eval(lit, model_completion=True))


# =============================================================================
# Section 5 - Boolean formulation (approach A = CP-SAT, approach B = Z3)
# =============================================================================
class BooleanModel:
    """x[s, u] = 1  <=>  user u performs step s.

    Efficiency: x[s, u] is only created when C1 allows u to do s, so C1 is
    enforced by the absence of the variable rather than by extra rules.
    """

    def __init__(self, inst: Instance, backend, amk: str = "pattern"):
        self.inst = inst
        self.b = backend
        self.amk = amk
        self.cands = inst.candidates()
        self.sod_pairs = {tuple(sorted(p)) for p in inst.sod}
        self.M: Dict[Tuple[int, int], object] = {}
        self.x: Dict[Tuple[int, int], object] = {
            (s, u): backend.new_bool(f"x_s{s + 1}_u{u + 1}")
            for s in range(inst.n_steps) for u in self.cands[s]
        }

    def lit(self, s: int, u: int):
        """The variable x[s, u], or None if C1 forbids u from doing s."""
        return self.x.get((s, u))

    # --- one function per constraint ------------------------------------
    def add_base(self) -> None:
        """Every step is performed by exactly one (authorised) user."""
        for s in range(self.inst.n_steps):
            self.b.exactly_one([self.x[s, u] for u in self.cands[s]])

    def add_sod(self) -> None:
        """C2: for every user u, x[s1,u] + x[s2,u] <= 1."""
        for s1, s2 in self.inst.sod:
            for u in set(self.cands[s1]) & set(self.cands[s2]):
                self.b.at_most_one([self.x[s1, u], self.x[s2, u]])

    def add_bod(self) -> None:
        """C3: for every user u, x[s1,u] = x[s2,u].

        If u is authorised for only one of the two steps, u cannot take
        that step either, because the other step could not follow.
        """
        for s1, s2 in self.inst.bod:
            for u in set(self.cands[s1]) | set(self.cands[s2]):
                a, b = self.lit(s1, u), self.lit(s2, u)
                if a is not None and b is not None:
                    self.b.equal(a, b)
                else:
                    self.b.false(a if a is not None else b)

    def add_at_most_k(self) -> None:
        """C4 dispatcher: two alternative encodings of At-most-k."""
        if self.amk == "users":
            self.add_at_most_k_users()
        else:
            self.add_at_most_k_pattern()

    def add_at_most_k_users(self) -> None:
        """C4, user-based encoding: helper y[u] = 'u performs some step
        in T'; sum(y) <= k. Needs one helper per candidate user, so it
        grows with the number of users."""
        for k, steps in self.inst.at_most_k:
            users = {u for s in steps for u in self.cands[s]}
            y = {u: self.b.new_bool() for u in users}
            for s in steps:
                for u in self.cands[s]:
                    self.b.implies(self.x[s, u], y[u])
            self.b.sum_le(list(y.values()), k)

    def same_user(self, s1: int, s2: int):
        """Helper M[s1,s2]: if true, s1 and s2 must get the same user.

        Encoded as: M and x[a,u] -> x[b,u] for every candidate u of a.
        (If u cannot do b at all, the clause becomes: not (M and x[a,u]).)
        Created once per pair and shared by all constraints.
        """
        a, b = min(s1, s2), max(s1, s2)
        if (a, b) not in self.M:
            m = self.b.new_bool(f"M_s{a + 1}_s{b + 1}")
            for u in self.cands[a]:
                xb = self.lit(b, u)
                clause = [self.b.neg(m), self.b.neg(self.x[a, u])]
                self.b.clause(clause + ([xb] if xb is not None else []))
            if (a, b) in self.sod_pairs:   # redundant: SoD steps never share
                self.b.false(m)
            self.M[a, b] = m
        return self.M[a, b]

    def add_at_most_k_pattern(self) -> None:
        """C4, user-independent (pattern) encoding.

        Walk the steps of T in order. Step T[i] is a 'first' if no earlier
        step of T has the same user; the number of distinct users equals
        the number of firsts. T[0] is always a first, so we require
        (number of firsts among T[1:]) <= k - 1.
        Clause per step: first[i] OR M[T[0],T[i]] OR ... OR M[T[i-1],T[i]].
        Size depends only on |T|, not on the number of users.
        """
        for k, steps in self.inst.at_most_k:
            T = list(dict.fromkeys(steps))       # drop duplicates, keep order
            firsts = []
            for i in range(1, len(T)):
                f = self.b.new_bool()
                self.b.clause([f] + [self.same_user(T[j], T[i])
                                     for j in range(i)])
                firsts.append(f)
            self.b.sum_le(firsts, k - 1)

    def add_one_team(self) -> None:
        """C5: choose exactly one team t_i; a step in T given to u forces
        u's team to be the chosen one. Users in no team cannot take T."""
        for steps, teams in self.inst.one_team:
            t = [self.b.new_bool() for _ in teams]
            self.b.exactly_one(t)
            team_of = {u: i for i, team in enumerate(teams) for u in team}
            for s in steps:
                for u in self.cands[s]:
                    if u in team_of:
                        self.b.implies(self.x[s, u], t[team_of[u]])
                    else:
                        self.b.false(self.x[s, u])

    # --- extra constraints (our own) -------------------------------------
    def users_doing(self, steps) -> Dict[int, object]:
        """Helper z[u] for every user who could do a step in `steps`, with
        z[u] -> u really performs one of those steps (one clause per user)."""
        z = {}
        for u in sorted({u for s in steps for u in self.cands[s]}):
            z[u] = self.b.new_bool()
            self.b.clause([self.b.neg(z[u])] +
                          [self.x[s, u] for s in steps if (s, u) in self.x])
        return z

    def add_at_least_k(self) -> None:
        """E1: at least k distinct users over T.

        z[u] may only be true if u really does a step in T (the opposite
        link to C4's helper), and at least k of the z[u] must be true.
        """
        for k, steps in self.inst.at_least_k:
            self.b.sum_ge(list(self.users_doing(steps).values()), k)

    def add_max_workload(self) -> None:
        """E2: for every user u, sum over s of x[s,u] <= L."""
        L = self.inst.max_workload
        if L is None:
            return
        for u in range(self.inst.n_users):
            lits = [self.x[s, u] for s in range(self.inst.n_steps)
                    if (s, u) in self.x]
            if len(lits) > L:
                self.b.sum_le(lits, L)

    def add_conditional(self) -> None:
        """E3: x[s1,u1] + x[s2,u2] <= 1, i.e. not (u1 does s1 and u2 does s2)."""
        for s1, u1, s2, u2 in self.inst.conditional:
            a, b = self.lit(s1, u1), self.lit(s2, u2)
            if a is not None and b is not None:   # else it can never happen
                self.b.at_most_one([a, b])

    def add_minimise_users(self) -> None:
        """E4 (objective): z[u] >= x[s,u]; minimise sum of z[u]."""
        if not self.inst.minimise_users:
            return
        used = {}
        for (s, u), xv in self.x.items():
            if u not in used:
                used[u] = self.b.new_bool()
            self.b.implies(xv, used[u])
        self.b.minimise(list(used.values()))

    def build(self) -> "BooleanModel":
        """Add every constraint type. C1 is already built into self.x."""
        self.add_base()
        self.add_sod()
        self.add_bod()
        self.add_at_most_k()
        self.add_one_team()
        self.add_at_least_k()
        self.add_max_workload()
        self.add_conditional()
        self.add_minimise_users()
        return self

    # --- solving -------------------------------------------------------
    def solve(self, timeout: Optional[float]) -> str:
        """Solve with the chosen back-end: 'sat' | 'unsat' | 'unknown'."""
        return self.b.solve(timeout)

    def assignment(self) -> List[int]:
        """Read back pi(s) for every step from the solved model."""
        return [next(u for u in self.cands[s] if self.b.value(self.x[s, u]))
                for s in range(self.inst.n_steps)]

    def block(self, pi: List[int]) -> None:
        """Uniqueness: forbid this exact assignment (blocking clause)."""
        self.b.clause([self.b.neg(self.x[s, pi[s]]) for s in range(len(pi))])


# =============================================================================
# Section 6 - Integer formulation (approach C = Z3)
# =============================================================================
def _any(terms):
    """z3.Or that also accepts a single term."""
    terms = list(terms)
    return terms[0] if len(terms) == 1 else z3.Or(terms)


class Z3IntegerModel:
    """a[s] = u  <=>  user u performs step s (one integer per step).

    Compared with the Boolean model: C2 and C3 become one line each
    (a[s1] != a[s2], a[s1] == a[s2]), while C4 and C5 need helpers.

    Every rule is added through _add(tag, ...), where tag names the input
    line it comes from, e.g. ('sod', 3). Normally _add just asserts the
    rule; with track=True the rules are collected per tag instead, so that
    explain_unsat() can switch whole input lines on and off.
    """

    def __init__(self, inst: Instance, amk: str = "pattern", track: bool = False):
        if z3 is None:
            raise ImportError("Z3 is not installed: pip install z3-solver")
        self.inst = inst
        self.amk = amk
        self.track = track
        self.groups: Dict[Tuple[str, int], list] = {}
        self.cands = inst.candidates()
        optimise = inst.minimise_users and not track
        self.solver = z3.Optimize() if optimise else z3.Solver()
        self.model = None
        self._count = 0
        self.a = [z3.Int(f"a_s{s + 1}") for s in range(inst.n_steps)]

    def new_bool(self):
        """A fresh helper Boolean with a unique name."""
        self._count += 1
        return z3.Bool(f"aux{self._count}")

    def _add(self, tag, *exprs) -> None:
        """Assert exprs, or (track=True) file them under their input line."""
        if self.track and tag is not None:
            self.groups.setdefault(tag, []).extend(exprs)
        else:
            self.solver.add(*exprs)

    def add_base_auth(self) -> None:
        """Base + C1: a[s] takes one of the users authorised for s.

        Tracking mode states the same thing per Authorisations line
        (a[s] != u for every step s not listed for u), so a core can name
        the exact lines involved."""
        if not self.track:
            for s in range(self.inst.n_steps):
                self._add(None, _any(self.a[s] == u for u in self.cands[s]))
            return
        for s in range(self.inst.n_steps):
            self._add(None, self.a[s] >= 0, self.a[s] < self.inst.n_users)
        for u, allowed in self.inst.auth.items():
            banned = [self.a[s] != u for s in range(self.inst.n_steps)
                      if s not in allowed]
            if banned:
                self._add(("auth", u), *banned)

    def add_sod(self) -> None:
        """C2: a[s1] != a[s2]."""
        for i, (s1, s2) in enumerate(self.inst.sod):
            self._add(("sod", i), self.a[s1] != self.a[s2])

    def add_bod(self) -> None:
        """C3: a[s1] == a[s2]."""
        for i, (s1, s2) in enumerate(self.inst.bod):
            self._add(("bod", i), self.a[s1] == self.a[s2])

    def firsts(self, tag, steps, exact: bool):
        """Pattern helper: f[i] for every step of T after the first.

        Always:      f[i] OR T[i] shares a user with an earlier step of T,
                     so the number of firsts is at least the number of users.
        exact=True:  also f[i] -> T[i] differs from every earlier step,
                     so the number of firsts equals the number of users.
        In this model 'same user' is just an equality between two integers,
        so no M helper is needed.
        """
        T = list(dict.fromkeys(steps))
        fs = []
        for i in range(1, len(T)):
            f = self.new_bool()
            same = [self.a[T[j]] == self.a[T[i]] for j in range(i)]
            self._add(tag, z3.Or([f] + same))
            if exact:
                self._add(tag, z3.Implies(f, z3.Not(z3.Or(same))))
            fs.append(f)
        return fs

    def add_at_most_k(self) -> None:
        """C4, same two encodings as the Boolean model.

        users:   y[u] <- (a[s] == u) for s in T; sum(y) <= k.
        pattern: sum(first) <= k - 1 (see firsts()).
        """
        for n, (k, steps) in enumerate(self.inst.at_most_k):
            tag = ("at-most-k", n)
            if self.amk == "users":
                users = {u for s in steps for u in self.cands[s]}
                y = {u: self.new_bool() for u in users}
                for s in steps:
                    for u in self.cands[s]:
                        self._add(tag, z3.Implies(self.a[s] == u, y[u]))
                self._add(tag, z3.PbLe([(v, 1) for v in y.values()], k))
            else:
                fs = self.firsts(tag, steps, exact=False)
                if fs:
                    self._add(tag, z3.PbLe([(f, 1) for f in fs], k - 1))

    def add_one_team(self) -> None:
        """C5: team index t in [0, r); a[s] == u forces t == team of u;
        users in no team cannot take steps in T."""
        for n, (steps, teams) in enumerate(self.inst.one_team):
            tag = ("one-team", n)
            t = z3.Int(f"team{n}")
            self._add(tag, t >= 0, t < len(teams))
            team_of = {u: i for i, team in enumerate(teams) for u in team}
            for s in steps:
                for u in self.cands[s]:
                    if u in team_of:
                        self._add(tag, z3.Implies(self.a[s] == u, t == team_of[u]))
                    else:
                        self._add(tag, self.a[s] != u)

    # --- extra constraints (our own) -------------------------------------
    def add_at_least_k(self) -> None:
        """E1: (1 + number of exact firsts) >= k. In the integer model the
        pattern form is the natural one: 'different user' is just !=."""
        for n, (k, steps) in enumerate(self.inst.at_least_k):
            tag = ("at-least-k", n)
            fs = self.firsts(tag, steps, exact=True)
            if k - 1 > len(fs):
                self._add(tag, z3.BoolVal(False))
            elif k > 1:
                self._add(tag, z3.PbGe([(f, 1) for f in fs], k - 1))

    def add_max_workload(self) -> None:
        """E2: for every user u, sum over s of If(a[s] == u, 1, 0) <= L."""
        L = self.inst.max_workload
        if L is None:
            return
        for u in sorted({u for c in self.cands for u in c}):
            steps = [s for s in range(self.inst.n_steps) if u in self.cands[s]]
            if len(steps) > L:
                self._add(("max-workload", 0),
                          z3.Sum([z3.If(self.a[s] == u, 1, 0) for s in steps]) <= L)

    def add_conditional(self) -> None:
        """E3: a[s1] == u1 -> a[s2] != u2."""
        for n, (s1, u1, s2, u2) in enumerate(self.inst.conditional):
            self._add(("conditional", n),
                      z3.Implies(self.a[s1] == u1, self.a[s2] != u2))

    def add_minimise_users(self) -> None:
        """E4 (objective): minimise the number of 'firsts' over all steps.
        At the optimum every first is a genuinely new user, so this equals
        the number of distinct users. (Skipped in tracking mode.)"""
        if self.inst.minimise_users and not self.track:
            fs = self.firsts(None, range(self.inst.n_steps), exact=False)
            self.solver.minimize(z3.Sum([z3.If(f, 1, 0) for f in fs]))

    def build(self) -> "Z3IntegerModel":
        """Add every constraint type (C1-C5, then E1-E4)."""
        self.add_base_auth()
        self.add_sod()
        self.add_bod()
        self.add_at_most_k()
        self.add_one_team()
        self.add_at_least_k()
        self.add_max_workload()
        self.add_conditional()
        self.add_minimise_users()
        return self

    def solve(self, timeout: Optional[float]) -> str:
        """Solve: 'sat' | 'unsat' | 'unknown' (time limit reached); keeps the model."""
        status = _z3_check(self.solver, timeout)
        if status == "sat":
            self.model = self.solver.model()
        return status

    def assignment(self) -> List[int]:
        """Read back pi(s) = a[s] for every step from the solved model."""
        return [self.model.eval(self.a[s], model_completion=True).as_long()
                for s in range(self.inst.n_steps)]

    def block(self, pi: List[int]) -> None:
        """Uniqueness: at least one step must get a different user."""
        self.solver.add(_any(self.a[s] != pi[s] for s in range(len(pi))))


# =============================================================================
# Sections 7-8 - Solve, extract, uniqueness check (shared by all approaches)
# =============================================================================
@dataclass
class Result:
    """Outcome of one solve, independent of which approach produced it.

    status is 'sat', 'unsat' or 'unknown' (time limit reached). 'unknown'
    is never reported as unsat.
    """
    status: str
    assignment: Optional[List[int]] = None
    unique: Optional[bool] = None
    time_ms: float = 0.0
    unique_ms: Optional[float] = None


def solve_with(make_model, inst: Instance, check_unique: bool = True,
               timeout: Optional[float] = None) -> Result:
    """Build a model, solve it, read the answer and check uniqueness.

    Time covers model building + first solve (as in the template); the
    uniqueness check runs after the clock stops.
    """
    start = _now_ms()
    if any(not c for c in inst.candidates()):  # a step nobody may do
        return Result("unsat", time_ms=_now_ms() - start)
    if inst.n_steps == 0:                      # nothing to assign
        return Result("sat", assignment=[], unique=True,
                      time_ms=_now_ms() - start, unique_ms=0.0)

    model = make_model().build()
    status = model.solve(timeout)
    time_ms = _now_ms() - start
    if status != "sat":
        return Result(status, time_ms=time_ms)

    pi = model.assignment()
    unique = unique_ms = None
    if check_unique:
        start = _now_ms()
        model.block(pi)
        unique = {"unsat": True, "sat": False}.get(model.solve(timeout))
        unique_ms = _now_ms() - start
    return Result("sat", assignment=pi, unique=unique, time_ms=time_ms,
                  unique_ms=unique_ms)


class BruteForceModel:
    """Testing oracle: tries every assignment and keeps those verify()
    accepts. Exponential (|candidates| ^ steps), so only for tiny instances
    (refuses more than 2 million assignments). Used to produce and check the
    expected answers of our own extra-constraint instances."""

    LIMIT = 2_000_000

    def __init__(self, inst: Instance, amk: str = "pattern"):
        self.inst = inst
        self.cands = inst.candidates()
        self.blocked: Set[Tuple[int, ...]] = set()
        self.found: Optional[Tuple[int, ...]] = None

    def build(self) -> "BruteForceModel":
        """Refuse search spaces that are too large to enumerate."""
        size = 1
        for c in self.cands:
            size *= len(c)
        if size > self.LIMIT:
            raise ValueError(f"brute force: {size} assignments is too many")
        return self

    def solve(self, timeout: Optional[float]) -> str:
        """Try every assignment (skipping blocked ones); with E4 keep the one with the fewest users."""
        best = None
        for pi in itertools.product(*self.cands):
            if pi in self.blocked or verify(self.inst, list(pi)):
                continue
            if not self.inst.minimise_users:
                self.found = pi
                return "sat"
            if best is None or len(set(pi)) < len(set(best)):
                best = pi
        self.found = best
        return "sat" if best else "unsat"

    def assignment(self) -> List[int]:
        """The assignment found by the last solve."""
        return list(self.found)

    def block(self, pi: List[int]) -> None:
        """Uniqueness: skip this exact assignment in later solves."""
        self.blocked.add(tuple(pi))


METHODS = {
    # A: CP-SAT, Boolean formulation (main approach, default)
    "cpsat": lambda inst, amk: BooleanModel(inst, CpSatBackend(), amk),
    # B: Z3, the identical Boolean formulation
    "z3-bool": lambda inst, amk: BooleanModel(
        inst, Z3Backend(optimise=inst.minimise_users), amk),
    # C: Z3, integer formulation
    "z3-int": lambda inst, amk: Z3IntegerModel(inst, amk),
    # Testing oracle for tiny instances (not a submitted approach)
    "brute": lambda inst, amk: BruteForceModel(inst, amk),
}


def solve_instance(inst: Instance, method: str = "cpsat", amk: str = "pattern",
                   check_unique: bool = True, timeout: Optional[float] = None,
                   **_) -> Result:
    """Solve with one of the approaches in METHODS."""
    return solve_with(lambda: METHODS[method](inst, amk), inst,
                      check_unique=check_unique, timeout=timeout)


def explain_unsat(inst: Instance, timeout: Optional[float] = None) -> Optional[List[str]]:
    """Why is an instance unsatisfiable? Returns a minimal set of input
    lines that already clash on their own (a minimal unsat core), or None
    if the instance is satisfiable.

    Each input line becomes one switch p_i (p_i -> its rules) in the
    tracked integer model. Z3 returns an unsat core of switches; it is then
    shrunk by deletion: drop one line at a time and keep it dropped if the
    rest is still unsat. The result names lines in the file, so a user can
    see what would have to change.
    """
    m = Z3IntegerModel(inst, track=True).build()
    if timeout:
        m.solver.set("timeout", int(timeout * 1000))
    switch = {tag: z3.Bool(f"line_{tag[0]}_{tag[1]}") for tag in m.groups}
    for tag, exprs in m.groups.items():
        m.solver.add(z3.Implies(switch[tag], z3.And(exprs)))
    result = m.solver.check(*switch.values())
    if result == z3.sat:
        return None
    if result != z3.unsat:
        raise TimeoutError("could not decide within the time limit")
    by_name = {str(p): tag for tag, p in switch.items()}
    core = [by_name[str(p)] for p in m.solver.unsat_core()]
    for tag in list(core):                       # deletion-based minimisation
        rest = [t for t in core if t != tag]
        if m.solver.check(*[switch[t] for t in rest]) == z3.unsat:
            core = rest                          # unknown: keep the line
    core.sort(key=lambda tag: inst.line_no.get(tag, 0))   # file order
    return [inst.source[tag] for tag in core]


# =============================================================================
# Section 9 - Solver() interface (CW2 template)
# =============================================================================
def Solver(filename, **kwargs):
    """Solve one instance file and return the dict the template expects.

    kwargs:
        silent (bool):  do not print the file name (default False).
        method (str):   'cpsat' (A, default), 'z3-bool' (B) or 'z3-int' (C).
        amk (str):      At-most-k encoding, 'pattern' (default) or 'users'.
        timeout (float): seconds per solve; None (default) = no limit.
        optimise (bool): E4, return a solution with the fewest users.
    """
    if not kwargs.get("silent", False):
        print(filename)

    inst = parse_instance(filename)
    if kwargs.get("optimise"):
        inst.minimise_users = True          # E4 switched on from the caller
    result = solve_instance(inst, **kwargs)

    d = dict(sat="unsat", sol="", mul_sol="", exe_time=f"{round(result.time_ms)}ms")
    if result.status == "unknown":
        d["sat"] = "unknown"           # only possible when a timeout is set
    elif result.status == "sat":
        d["sat"] = "sat"
        d["sol"] = [f"s{s + 1}: u{u + 1}" for s, u in enumerate(result.assignment)]
        d["mul_sol"] = {True: "this is the only solution",
                        False: "other solutions exist"}.get(result.unique,
                                                            "uniqueness unknown")
    return d


# =============================================================================
# Section 10 - Output helper (copied unchanged from the CW2 Helper)
# =============================================================================
# Copied unchanged from the COMP3070 CW2 Helper (module convenor): turns the
# dict returned by Solver() into the expected printed output.
def transform_output(d):
    crlf = '\r\n'
    s = []
    s = ''.join(kk + crlf for kk in d['sol'])
    s = d['sat'] + crlf + s + d['mul_sol']
    s = crlf + s + crlf + str(d['exe_time']) if 'exe_time' in d else s
    return s


# =============================================================================
# Section 11 - Independent checker (no solver involved)
# =============================================================================
def verify(inst: Instance, pi: List[int]) -> List[str]:
    """Check an assignment against every constraint directly.

    Returns a list of violations; an empty list means pi is a valid solution.
    """
    errors: List[str] = []
    if len(pi) != inst.n_steps:
        return [f"expected {inst.n_steps} steps, got {len(pi)}"]
    for s, u in enumerate(pi):
        if not 0 <= u < inst.n_users:
            errors.append(f"s{s + 1}: user u{u + 1} does not exist")
        elif not inst.is_authorised(s, u):
            errors.append(f"C1: u{u + 1} is not authorised for s{s + 1}")
    for s1, s2 in inst.sod:
        if pi[s1] == pi[s2]:
            errors.append(f"C2: s{s1 + 1} and s{s2 + 1} share u{pi[s1] + 1}")
    for s1, s2 in inst.bod:
        if pi[s1] != pi[s2]:
            errors.append(f"C3: s{s1 + 1} and s{s2 + 1} have different users")
    for k, steps in inst.at_most_k:
        used = {pi[s] for s in steps}
        if len(used) > k:
            errors.append(f"C4: {len(used)} users > k={k} on {len(steps)} steps")
    for steps, teams in inst.one_team:
        used = {pi[s] for s in steps}
        if not any(used <= set(team) for team in teams):
            errors.append("C5: steps are not all inside one team")
    for k, steps in inst.at_least_k:
        used = {pi[s] for s in steps}
        if len(used) < k:
            errors.append(f"E1: {len(used)} users < k={k} on {len(steps)} steps")
    if inst.max_workload is not None:
        for u in set(pi):
            if pi.count(u) > inst.max_workload:
                errors.append(f"E2: u{u + 1} does {pi.count(u)} steps "
                              f"> L={inst.max_workload}")
    for s1, u1, s2, u2 in inst.conditional:
        if pi[s1] == u1 and pi[s2] == u2:
            errors.append(f"E3: u{u1 + 1} does s{s1 + 1} and u{u2 + 1} does s{s2 + 1}")
    return errors


# =============================================================================
# Section 12 - Test runner
# =============================================================================
# Appendix 1 table: example number -> (sat?, unique?)
APPENDIX_ANSWERS = {
    1: (True, False), 2: (False, None), 3: (True, True), 4: (False, None),
    5: (True, True), 6: (False, None), 7: (True, True), 8: (False, None),
    9: (True, False), 10: (True, False), 11: (True, False), 12: (True, False),
    13: (False, None), 14: (False, None), 15: (False, None),
    16: (True, False), 17: (True, False), 18: (False, None), 19: (False, None),
}


def expected_answer(path: str) -> Tuple[Optional[bool], Optional[bool], Optional[int]]:
    """Known (sat?, unique?, min_users?) for an instance file.

    From its -solution.txt (first line 'sat'/'unsat'; our own files may add
    '# unique: yes|no' and '# min-users: k'), or from the Appendix 1 table
    for exampleN.txt. Unknown parts are None.
    """
    sol_file = path[:-4] + "-solution.txt"
    if os.path.exists(sol_file):
        with open(sol_file, encoding="utf-8") as f:
            lines = [l.strip().lower() for l in f if l.strip()]
        notes = dict(l[1:].split(":", 1) for l in lines if l.startswith("#"))
        notes = {k.strip(): v.strip() for k, v in notes.items()}
        unique = {"yes": True, "no": False}.get(notes.get("unique"))
        min_users = int(notes["min-users"]) if "min-users" in notes else None
        return lines[0] == "sat", unique, min_users
    m = re.fullmatch(r"example(\d+)\.txt", os.path.basename(path))
    if m and int(m.group(1)) in APPENDIX_ANSWERS:
        return APPENDIX_ANSWERS[int(m.group(1))] + (None,)
    return None, None, None


def instance_files(paths: List[str]) -> List[str]:
    """Expand folders into their instance files (skipping -solution files)."""
    files: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                files += [os.path.join(root, n) for n in names
                          if n.endswith(".txt") and not n.endswith("-solution.txt")]
        else:
            files.append(p)
    key = lambda f: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", f)]
    return sorted(files, key=key)


def run_tests(paths: List[str], **kwargs) -> bool:
    """Solve every instance, compare with the known answer and verify."""
    passed = failed = unknown = 0
    for path in instance_files(paths):
        d = Solver(path, silent=True, **kwargs)
        if d["sat"] == "unknown":
            unknown += 1
            print(f"TIME  -     {d['exe_time']:>8}  {path}", flush=True)
            continue
        exp_sat, exp_unique, exp_min = expected_answer(path)
        problems = []
        got_sat = d["sat"] == "sat"
        if exp_sat is not None and got_sat != exp_sat:
            problems.append(f"expected {'sat' if exp_sat else 'unsat'}")
        if got_sat:
            pi = [int(_USER.search(line).group(1)) - 1 for line in d["sol"]]
            problems += verify(parse_instance(path), pi)
            got_unique = d["mul_sol"] == "this is the only solution"
            if exp_unique is not None and got_unique != exp_unique:
                problems.append("uniqueness differs from the expected answer")
            if exp_min is not None and len(set(pi)) != exp_min:
                problems.append(f"uses {len(set(pi))} users, expected {exp_min}")
        status = "FAIL" if problems else "ok"
        passed += not problems
        failed += bool(problems)
        print(f"{status:4} {d['sat']:5} {d['exe_time']:>8}  {path}"
              + (f"  <- {'; '.join(problems)}" if problems else ""), flush=True)
    print(f"\n{passed} passed, {failed} failed, {unknown} timed out")
    return failed == 0


# =============================================================================
# Section 12b - Benchmark mode (data for the report's Evaluation section)
# =============================================================================
BENCH_FIELDS = ["file", "folder", "method", "amk", "optimise", "status",
                "expected", "correct", "checker_ok", "unique", "users_used",
                "time_ms", "unique_ms", "runs", "timeouts", "steps", "users",
                "constraints"]


def _median(values: List[float]) -> Optional[float]:
    """Median of the values, ignoring None (None if there are none)."""
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def _write_bench_meta(out_csv: str, timeout: float) -> None:
    """Record the test environment next to the CSV (report: setup paragraph)."""
    import datetime
    import platform
    lines = [f"date: {datetime.datetime.now().isoformat(timespec='seconds')}",
             f"machine: {platform.platform()} ({platform.machine()})",
             f"python: {platform.python_version()}",
             f"time limit per solve: {timeout} s",
             "repeats: 5 if the first run < 1 s, else 3; 1 if it timed out",
             "status: decided if any run decided; timed-out runs counted in 'timeouts'",
             "time_ms: median over the deciding runs of model building + first solve",
             "unique_ms: median of the uniqueness check (block + re-solve)"]
    try:
        import ortools
        lines.append(f"ortools: {ortools.__version__}")
    except ImportError:
        pass
    if z3 is not None:
        lines.append(f"z3: {z3.get_version_string()}")
    with open(out_csv + ".meta.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run_bench(paths: List[str], out_csv: str, methods: List[str],
              amks: List[str], optimise: bool = False,
              timeout: float = 60.0) -> None:
    """Run every instance x method x encoding and append one CSV row each.

    Repeats: 5 runs if the first takes under 1 s (small times are noisy),
    otherwise 3; a run that hits the time limit is not repeated. Times are
    medians. Resumable: rows already in out_csv are skipped, so a long run
    can be stopped with Ctrl+C and started again.
    """
    import csv
    done = set()
    if os.path.exists(out_csv):
        with open(out_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            old_rows, old_fields = list(reader), reader.fieldnames or []
        if old_fields != BENCH_FIELDS:            # older CSV: upgrade columns
            with open(out_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=BENCH_FIELDS)
                w.writeheader()
                w.writerows({k: r.get(k, "") for k in BENCH_FIELDS} for r in old_rows)
        done = {(r["file"], r["method"], r["amk"], r["optimise"]) for r in old_rows}
    _write_bench_meta(out_csv, timeout)
    new_file = not os.path.exists(out_csv)

    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BENCH_FIELDS)
        if new_file:
            writer.writeheader()
        for path in instance_files(paths):
            inst0 = parse_instance(path)
            exp_sat, _, _ = expected_answer(path)
            for method in methods:
                for amk in (["-"] if method == "brute" else amks):
                    key = (path, method, amk, str(int(optimise)))
                    if key in done:
                        continue
                    runs: List[Result] = []
                    status = None
                    while True:
                        inst = parse_instance(path)
                        inst.minimise_users |= optimise
                        try:
                            r = solve_instance(inst, method=method,
                                               amk=amk if amk != "-" else "pattern",
                                               timeout=timeout)
                        except ValueError:          # brute force: too large
                            status = "skipped"
                            break
                        runs.append(r)
                        if r.status == "unknown":
                            break
                        if len(runs) >= (5 if runs[0].time_ms < 1000 else 3):
                            break
                    # Runs can differ (parallel search is not deterministic):
                    # an instance counts as decided if any run decided it;
                    # timed-out runs are counted in 'timeouts'.
                    decided = [r for r in runs if r.status in ("sat", "unsat")]
                    last = decided[-1] if decided else (runs[-1] if runs else None)
                    status = status or last.status
                    sat = status == "sat"
                    row = dict(
                        file=path, folder=os.path.dirname(path), method=method,
                        amk=amk, optimise=int(optimise), status=status,
                        expected="" if exp_sat is None else ("sat" if exp_sat else "unsat"),
                        correct="" if exp_sat is None or status not in ("sat", "unsat")
                        else int(sat == exp_sat),
                        checker_ok=int(not verify(inst0, last.assignment)) if sat else "",
                        unique="" if not sat or last.unique is None else int(last.unique),
                        users_used=len(set(last.assignment)) if sat else "",
                        time_ms=round(_median([r.time_ms for r in (decided or runs)]), 3)
                        if runs else "",
                        unique_ms=round(_median([r.unique_ms for r in decided]), 3) if sat else "",
                        runs=len(runs),
                        timeouts=sum(r.status == "unknown" for r in runs),
                        steps=inst0.n_steps, users=inst0.n_users,
                        constraints=len(inst0.source))
                    writer.writerow(row)
                    f.flush()
                    note = f" ({row['timeouts']} timed out)" if row["timeouts"] and decided else ""
                    print(f"{method:8} {amk:8} {status:8} {row['time_ms']!s:>9} ms"
                          f"  x{len(runs)}{note}  {path}", flush=True)


# =============================================================================
# Section 13 - Command line
# =============================================================================
def main(argv: Optional[List[str]] = None) -> int:
    """Command-line entry point; see the module docstring for usage."""
    parser = argparse.ArgumentParser(description="WSP solver (COMP3070 CW2)")
    parser.add_argument("paths", nargs="+", help="instance files or folders")
    parser.add_argument("--method", default="cpsat", choices=sorted(METHODS))
    parser.add_argument("--amk", default="pattern", choices=["pattern", "users"],
                        help="At-most-k encoding (default: pattern)")
    parser.add_argument("--timeout", type=float, default=None,
                        help="seconds per solve (default: no limit)")
    parser.add_argument("--optimise", action="store_true",
                        help="E4: find a solution with the fewest users")
    parser.add_argument("--test", action="store_true",
                        help="check every instance against its known answer")
    parser.add_argument("--explain", action="store_true",
                        help="for unsat instances, print a minimal set of clashing lines")
    parser.add_argument("--bench", metavar="OUT.csv",
                        help="benchmark mode: append one row per run to OUT.csv")
    parser.add_argument("--methods", default="cpsat",
                        help="benchmark: comma-separated approaches (e.g. cpsat,z3-bool,z3-int)")
    parser.add_argument("--amks", default="pattern",
                        help="benchmark: comma-separated At-most-k encodings (pattern,users)")
    args = parser.parse_args(argv)
    opts = dict(method=args.method, amk=args.amk, timeout=args.timeout,
                optimise=args.optimise)

    try:
        if args.test:
            return 0 if run_tests(args.paths, **opts) else 1
        if args.bench:
            run_bench(args.paths, args.bench, args.methods.split(","),
                      args.amks.split(","), optimise=args.optimise,
                      timeout=args.timeout or 60.0)
            return 0
        if args.explain:
            for path in instance_files(args.paths):
                try:
                    core = explain_unsat(parse_instance(path), args.timeout)
                except TimeoutError as e:
                    print(f"{path}: {e}")
                    continue
                print(f"{path}: " + ("satisfiable" if core is None else
                      "unsat because of these lines together:"))
                for line in core or []:
                    print("    " + line)
            return 0
        for path in instance_files(args.paths):
            print(transform_output(Solver(path, **opts)), flush=True)
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C).")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
