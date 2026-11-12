"""
COMP3070 Coursework 1 - Z3-based exam timetabling solver
Group G

Reads an instance (.txt), prints "sat" + a timetable, or "unsat", and the
time of Z3's check in milliseconds. Full instructions: README.md and
Section 4 of the report.

HOW TO RUN  (Python 3 + "pip install z3-solver")
    python coursework01.py sat1.txt            solve one instance (main formulation)
    python coursework01.py                     solve every .txt in "test instances/"
    python coursework01.py --e1 --e2 --e4      switch on extra constraints
    python coursework01.py -f boolean sat1.txt choose a formulation (see below)
    python coursework01.py --solutions 10 sat2.txt   up to 10 different timetables
    python coursework01.py --explain           why each unsat instance is impossible
    python coursework01.py --selftest          automatic checks against brute force
    python coursework01.py --tests             targeted tests in constraint_tests.zip
    python coursework01.py --experiment        every experiment -> results/*.csv

CONSTRAINTS
  Main, always on (they decide the official sat/unsat answer):
    M1 one room and one slot per exam      M2 no room clashes
    M3 room capacity                       M4 no consecutive exams for a student
    M5 no simultaneous exams for a student
  Extra, off by default:
    E1 at most 2 exams per student per day (5 slots a day, or "Slots per day: N")
    E2 1 invigilator per 30 students (rounded up), 2 available per slot
    E3 fewest empty seats: the goal of -f optimize (not a hard rule)
    E4 rooms must have the facilities an exam requires ("Room r facilities: lab",
       "Exam e requirements: lab"; default: exam 0 needs the largest room)

FORMULATIONS (-f; section number in brackets)
    integer (6, main), symmetry (6), optimize (8), boolean (9),
    reference (11, brute force without Z3, ground truth for testing)
Comments like [report eq. 2.7] point to the matching formula in the report.

KNOWN BUGS: see the report, Section 4.7.
"""
from __future__ import annotations
from z3 import *
import re
import argparse
import csv
import math
import random
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

# =============================================================================
# 1. CONFIGURATION
# =============================================================================
"""Parameters for the extra constraints. The instance files contain no data
for invigilators, so those values are supplied here; the day length and
facilities may optionally be given in the file (see section 2).
All extras are OFF by default: the official sat/unsat answer uses M1-M5 only.
"""
@dataclass
class Config:
    # E1: max exams per student per day
    use_max_per_day: bool = False
    slots_per_day: int = 5                 # default; "Slots per day: N" overrides it
    max_exams_per_day: int = 2

    # E2: invigilators, 1 per 30 students (rounded up), 2 available per slot
    use_invigilators: bool = False
    invigilator_ratio: int = 30
    invigilators_per_slot: int = 2

    # E3: efficient room use (fewest empty seats) is the goal of the optimize
    #     formulation (section 8); it never relaxes M1, so it needs no switch.

    # E4: facility matching. Used only when the file has no facility lines:
    #     these exams need a "lab", and the largest room is the lab.
    use_facilities: bool = False
    default_lab_exams: Tuple[int, ...] = (0,)

    def active_extras(self) -> List[str]:
        """Short labels of the switched-on extras, for printing."""
        flags = [("E1", self.use_max_per_day), ("E2", self.use_invigilators),
                 ("E4", self.use_facilities)]
        return [name for name, on in flags if on]

# =============================================================================
# 2. INPUT  (module convenor's template, extended)
# =============================================================================
# The template's Instance fields and file layout are kept. Additions: blank
# lines, Windows line endings and a UTF-8 BOM are accepted; IDs are checked;
# and three optional metadata lines may appear among the enrolments:
#     Slots per day: 5
#     Room 1 facilities: lab, computers
#     Exam 0 requirements: lab
# Anything else is rejected with a clear error (malformed input is an input
# error, never an "unsat" answer).
class Instance:
    def __init__(self):
        self.number_of_students = 0
        self.number_of_exams = 0
        self.number_of_slots = 0
        self.number_of_rooms = 0
        self.room_capacities = []
        self.exams_to_students: List[Tuple[int, int]] = []
        self.slots_per_day: Optional[int] = None                 # optional metadata
        self.room_facilities: Dict[int, FrozenSet[str]] = {}     # optional metadata
        self.exam_requirements: Dict[int, FrozenSet[str]] = {}   # optional metadata


def parse_instance(text: str) -> Instance:
    """Parse the text of one instance file; raise ValueError if malformed."""
    lines = [l.strip() for l in text.lstrip("\ufeff").splitlines()]
    lines = [l for l in lines if l]                    # blank lines are ignored
    pos = 0

    def read_attribute(name):
        nonlocal pos
        line = lines[pos] if pos < len(lines) else "<end of file>"
        match = re.fullmatch(f'{name}:\\s*(\\d+)', line)
        if match:
            pos += 1
            return int(match.group(1))
        else:
            # FIX: the template lacked the f-prefix, so {line} was printed literally
            raise ValueError(f"Could not parse line {line!r}; expected the {name} attribute")

    def name_set(value):
        return frozenset(x.strip().lower() for x in value.split(",") if x.strip())

    instance = Instance()
    instance.number_of_students = read_attribute("Number of students")
    instance.number_of_exams = read_attribute("Number of exams")
    instance.number_of_slots = read_attribute("Number of slots")
    instance.number_of_rooms = read_attribute("Number of rooms")
    for r in range(instance.number_of_rooms):
        instance.room_capacities.append(read_attribute(f"Room {r} capacity"))

    E, S, R = instance.number_of_exams, instance.number_of_students, instance.number_of_rooms
    for l in lines[pos:]:
        if m := re.fullmatch(r"(\d+)\s+(\d+)", l):
            exam, student = int(m.group(1)), int(m.group(2))
            if not exam < E:
                raise ValueError(f"Line {l!r}: exam {exam} out of range 0..{E - 1}")
            if not student < S:
                raise ValueError(f"Line {l!r}: student {student} out of range 0..{S - 1}")
            instance.exams_to_students.append((exam, student))
        elif m := re.fullmatch(r"Slots per day:\s*(\d+)", l):
            if instance.slots_per_day is not None:
                raise ValueError(f"Line {l!r}: 'Slots per day' given twice")
            if int(m.group(1)) < 1:
                raise ValueError(f"Line {l!r}: slots per day must be at least 1")
            instance.slots_per_day = int(m.group(1))
        elif m := re.fullmatch(r"Room (\d+) facilities:(.*)", l):
            r = int(m.group(1))
            if not r < R:
                raise ValueError(f"Line {l!r}: room {r} out of range 0..{R - 1}")
            if r in instance.room_facilities:
                raise ValueError(f"Line {l!r}: facilities of room {r} given twice")
            instance.room_facilities[r] = name_set(m.group(2))
        elif m := re.fullmatch(r"Exam (\d+) requirements:(.*)", l):
            e = int(m.group(1))
            if not e < E:
                raise ValueError(f"Line {l!r}: exam {e} out of range 0..{E - 1}")
            if e in instance.exam_requirements:
                raise ValueError(f"Line {l!r}: requirements of exam {e} given twice")
            instance.exam_requirements[e] = name_set(m.group(2))
        else:
            raise ValueError(f"Failed to parse this line: {l!r}")
    return instance


def read_file(filename):
    with open(filename, encoding="utf-8") as f:
        return parse_instance(f.read())

# =============================================================================
# 3. PREPROCESSING
# =============================================================================
# Turns the raw (exam, student) pairs into the data the formulation needs,
# so the Z3 model itself only contains real choices.
@dataclass
class Problem:
    name: str
    config: Config
    num_students: int
    exams: range
    slots: range
    rooms: range
    capacity: List[int]
    students_of: List[FrozenSet[int]]
    size: List[int]
    conflicts: List[Tuple[int, int]]
    conflicts_of: List[FrozenSet[int]]
    slots_per_day: int
    day_groups: List[FrozenSet[int]]      # E1: exam sets of students with > max exams
    invigilators_needed: List[int]        # E2
    facilities: List[FrozenSet[str]]      # E4: facilities of each room
    allowed_rooms: Dict[int, FrozenSet[int]]   # E4: exam -> rooms with all it requires
    facilities_from_file: bool            # E4: False -> the default lab rule is used

    def day_of(self, slot: int) -> int:
        return slot // self.slots_per_day

    def num_days(self) -> int:
        return math.ceil(len(self.slots) / self.slots_per_day)


def preprocess(instance: Instance, config: Config, name: str = "") -> Problem:
    """Derive sizes, conflict pairs, per-day groups, invigilator needs and
    the rooms each exam may use under E4."""
    E = instance.number_of_exams
    R = instance.number_of_rooms

    # Students per exam (a repeated enrolment counts once; exams with no
    # listed students get an empty set). IDs were range-checked when reading.
    students = [set() for _ in range(E)]
    for exam, student in instance.exams_to_students:
        students[exam].add(student)
    students_of = [frozenset(s) for s in students]
    size = [len(s) for s in students_of]

    # Conflict pairs: exams that share at least one student
    exams_of_student: Dict[int, List[int]] = {}
    for e in range(E):
        for s in students_of[e]:
            exams_of_student.setdefault(s, []).append(e)
    pairs = set()
    for exam_list in exams_of_student.values():
        for i in range(len(exam_list)):
            for j in range(i + 1, len(exam_list)):
                a, b = sorted((exam_list[i], exam_list[j]))
                pairs.add((a, b))
    conflicts = sorted(pairs)
    conflicts_of = [set() for _ in range(E)]
    for a, b in conflicts:
        conflicts_of[a].add(b)
        conflicts_of[b].add(a)

    # E1: only students with more exams than the daily maximum can break it;
    #     students with the same set of exams give the same rule, so keep one
    day_groups = sorted({frozenset(ex) for ex in exams_of_student.values()
                         if len(ex) > config.max_exams_per_day}, key=sorted)

    # E2: invigilators needed per exam
    invigilators_needed = [math.ceil(size[e] / config.invigilator_ratio) for e in range(E)]

    # E4: facilities from the file, or the default "exam 0 needs the lab, and
    #     the largest room (lowest index on ties) is the lab"
    from_file = bool(instance.room_facilities or instance.exam_requirements)
    if from_file:
        facilities = [instance.room_facilities.get(r, frozenset()) for r in range(R)]
        requirements = dict(instance.exam_requirements)
    else:
        facilities = [frozenset() for _ in range(R)]
        if R > 0:
            lab = max(range(R), key=lambda r: (instance.room_capacities[r], -r))
            facilities[lab] = frozenset({"lab"})
        requirements = {e: frozenset({"lab"}) for e in config.default_lab_exams if 0 <= e < E}
    allowed_rooms = {e: frozenset(r for r in range(R) if need <= facilities[r])
                     for e, need in sorted(requirements.items()) if need}

    return Problem(
        name=name, config=config, num_students=instance.number_of_students,
        exams=range(E), slots=range(instance.number_of_slots), rooms=range(R),
        capacity=list(instance.room_capacities),
        students_of=students_of, size=size,
        conflicts=conflicts, conflicts_of=[frozenset(c) for c in conflicts_of],
        slots_per_day=instance.slots_per_day or config.slots_per_day,
        day_groups=day_groups, invigilators_needed=invigilators_needed,
        facilities=facilities, allowed_rooms=allowed_rooms, facilities_from_file=from_file,
    )

# =============================================================================
# 4. RESULT FORMAT  (every formulation returns the same shape)
# =============================================================================
@dataclass(frozen=True)
class Placement:
    """Where one exam goes: its slot and its (single) room."""
    slot: int
    room: int


@dataclass
class Result:
    """What every formulation returns, so results are directly comparable."""
    formulation: str
    status: str                                
    timetable: Dict[int, Placement] = field(default_factory=dict)
    solve_ms: float = 0.0                         
    build_ms: float = 0.0                         
    num_variables: Optional[int] = None
    num_constraints: Optional[int] = None
    notes: Dict[str, object] = field(default_factory=dict)


def timed(fn: Callable, *args, **kwargs):
    """Run fn and return (its return value, elapsed milliseconds).
    Wrap ONLY solver.check() (or opt.check()) with this for solve_ms."""
    start = time.perf_counter()
    value = fn(*args, **kwargs)
    return value, (time.perf_counter() - start) * 1000.0

# =============================================================================
# 5. INDEPENDENT CHECKER  (plain Python, no Z3: verifies every timetable)  [report 4.6]
# =============================================================================
def check_timetable(p: Problem, timetable: Dict[int, Placement]) -> List[str]:
    """Return a list of human-readable violations ([] means valid).

    Implemented separately from every Z3 model, so a modelling bug in a
    formulation cannot hide itself here.
    """
    cfg = p.config
    v: List[str] = []

    # M1: every exam exactly once, in a valid slot and a valid room
    for e in p.exams:
        if e not in timetable:
            v.append(f"M1: exam {e} is not timetabled")
    for e, pl in timetable.items():
        if e not in p.exams:
            v.append(f"M1: unknown exam {e} in timetable")
            continue
        if pl.slot not in p.slots:
            v.append(f"M1: exam {e} is in invalid slot {pl.slot}")
        if pl.room not in p.rooms:
            v.append(f"M1: exam {e} is in invalid room {pl.room}")
    if v:
        return v                 # later checks assume a complete, well-formed table

    # M2: at most one exam per (room, slot)
    used: Dict[Tuple[int, int], int] = {}
    for e in p.exams:
        key = (timetable[e].slot, timetable[e].room)
        if key in used:
            v.append(f"M2: exams {used[key]} and {e} both in room {key[1]}, slot {key[0]}")
        else:
            used[key] = e

    # M3: capacity
    for e in p.exams:
        cap = p.capacity[timetable[e].room]
        if p.size[e] > cap:
            v.append(f"M3: exam {e} has {p.size[e]} students but room capacity {cap}")

    # M4 / M5: conflicting exams
    for a, b in p.conflicts:
        gap = abs(timetable[a].slot - timetable[b].slot)
        if gap == 0:
            v.append(f"M5: exams {a} and {b} share a student and are at the same time")
        elif gap == 1:
            v.append(f"M4: exams {a} and {b} share a student and are back-to-back")

    # E1: max exams per student per day
    if cfg.use_max_per_day:
        for s in range(p.num_students):
            per_day: Dict[int, int] = {}
            for e in p.exams:
                if s in p.students_of[e]:
                    day = p.day_of(timetable[e].slot)
                    per_day[day] = per_day.get(day, 0) + 1
            for day, count in per_day.items():
                if count > cfg.max_exams_per_day:
                    v.append(f"E1: student {s} has {count} exams on day {day}")

    # E2: invigilators per slot
    if cfg.use_invigilators:
        for t in p.slots:
            need = sum(p.invigilators_needed[e] for e in p.exams if timetable[e].slot == t)
            if need > cfg.invigilators_per_slot:
                v.append(f"E2: slot {t} needs {need} invigilators "
                         f"(only {cfg.invigilators_per_slot} available)")

    # E3 is a goal (fewest empty seats), not a validity rule.

    # E4: the room provides every facility the exam requires
    if cfg.use_facilities:
        for e, allowed in p.allowed_rooms.items():
            if timetable[e].room not in allowed:
                v.append(f"E4: exam {e} is in room {timetable[e].room}, "
                         f"which lacks a required facility")

    return v

# =============================================================================
# 6. MAIN FORMULATION: INTEGER MODEL  [report Section 2; symmetry breaking: 3.2]
# =============================================================================
FORMULATIONS: Dict[str, Callable[[Problem], Result]] = {}


def register(name: str):
    """Decorator: @register("main") makes a formulation selectable with -f main.
    The FIRST registered formulation is the default."""
    def wrap(fn):
        FORMULATIONS[name] = fn
        return fn
    return wrap

# Optional time limit for every formulation (used by the experiments)
TIMEOUT_MS: Optional[int] = None


@dataclass
class IntVars:
    """The decision variables of the integer formulation."""
    slot: list                 # slot[e] = the slot of exam e
    room: list                 # room[e] = the room of exam e

    def count(self) -> int:
        return len(self.slot) + len(self.room)


def twin_rooms(p: Problem) -> List[Tuple[int, int]]:
    """Pairs of interchangeable rooms (same capacity and, when E4 is on, the
    same facilities), each room paired with the next one of its kind."""
    kinds: Dict[Tuple[int, FrozenSet[str]], List[int]] = {}
    for r in p.rooms:
        key = (p.capacity[r], p.facilities[r] if p.config.use_facilities else frozenset())
        kinds.setdefault(key, []).append(r)
    return [(rs[i], rs[i + 1]) for rs in kinds.values() for i in range(len(rs) - 1)]


def build_integer_model(p: Problem, s, track: bool = False, symmetry: bool = False):
    """Add the integer formulation (M1-M5 + switched-on extras) to solver s.
    Works for both Solver() and Optimize().

    Notation (also used in the report):
      E, T, R      exams, slots 0..|T|-1, rooms 0..|R|-1
      n(e), c(r)   students in exam e, capacity of room r
      C            pairs {e, f} of exams that share a student
      slot_e, room_e   the decision variables

    Returns (variables, number of constraints). With track=True each rule
    is added behind its own on/off switch, for the unsat explanation, and
    a third value maps every switch name to a readable label."""
    cfg = p.config
    num_slots, num_rooms = len(p.slots), len(p.rooms)
    items: List[Tuple[str, object]] = []          # (label, constraint)

    def add(label: str, *cs):
        items.extend((label, c) for c in cs)

    # Decision variables   [report eq. 2.5]
    v = IntVars(slot=[Int(f"slot_{e}") for e in p.exams],
                room=[Int(f"room_{e}") for e in p.exams])
    slot, room = v.slot, v.room

    # M1  for all e: 0 <= slot_e <= |T|-1  and  0 <= room_e <= |R|-1   [report eq. 2.6]
    #     one variable holds one value, so "exactly one" holds by construction
    for e in p.exams:
        add(f"M1 (exam {e} gets a valid slot and room)",
            slot[e] >= 0, slot[e] <= num_slots - 1, room[e] >= 0, room[e] <= num_rooms - 1)

    # M2  for all e < f with {e, f} not in C:  room_e = room_f  ->  slot_e != slot_f
    #     [report eq. 2.7]
    #     Pairs in C are skipped: M5 already puts them in different slots.
    for e in p.exams:
        for f in p.exams:
            if e < f and f not in p.conflicts_of[e]:
                add(f"M2 (exams {e} and {f} not in the same room at the same time)",
                    Implies(room[e] == room[f], slot[e] != slot[f]))

    # M3  for all e, r with n(e) > c(r):  room_e != r   [report eq. 2.8]
    for e in p.exams:
        small = [r for r in p.rooms if p.size[e] > p.capacity[r]]
        if small:
            add(f"M3 (exam {e} with {p.size[e]} students avoids rooms that are too small)",
                *[room[e] != r for r in small])

    for e, f in p.conflicts:
        # M4  for all {e, f} in C:  slot_e != slot_f + 1  and  slot_f != slot_e + 1
        #     [report eq. 2.9]
        add(f"M4 (exams {e} and {f} share a student: not back-to-back)",
            slot[e] != slot[f] + 1, slot[f] != slot[e] + 1)
        # M5  for all {e, f} in C:  slot_e != slot_f   [report eq. 2.10]
        add(f"M5 (exams {e} and {f} share a student: not at the same time)",
            slot[e] != slot[f])

    # E1  for every student's exam set G with |G| > K, and every day d:
    #       sum over e in G of [ d*s <= slot_e <= d*s + s - 1 ]  <=  K
    #     (s = slots per day, K = max exams per day; students with the same
    #      exams give the same rule, so each set G is added once)
    #     [report eq. 2.11]
    if cfg.use_max_per_day:
        spd = p.slots_per_day                  # from the file, or the default of 5
        for group in p.day_groups:
            for day in range(p.num_days()):
                first, last = day * spd, day * spd + spd - 1
                add(f"E1 (students taking exams {sorted(group)}: at most "
                    f"{cfg.max_exams_per_day} on day {day})",
                    Sum([If(And(slot[e] >= first, slot[e] <= last), 1, 0)
                         for e in sorted(group)]) <= cfg.max_exams_per_day)

    # E2  for all t:  sum over e of [ slot_e = t ] * inv(e)  <=  I   [report eq. 2.12]
    #     inv(e) = ceil(n(e) / 30) invigilators, I = 2 available per slot
    if cfg.use_invigilators:
        for t in p.slots:
            terms = [If(slot[e] == t, p.invigilators_needed[e], 0)
                     for e in p.exams if p.invigilators_needed[e] > 0]
            if terms:
                add(f"E2 (slot {t} needs at most {cfg.invigilators_per_slot} invigilators)",
                    Sum(terms) <= cfg.invigilators_per_slot)

    # E3  efficient room use is a goal, not a rule: see section 8.

    # E4  for all e with requirements, all r lacking one of them:  room_e != r
    #     (allowed_rooms[e] = rooms that provide every facility e requires)
    #     [report eq. 2.13]
    if cfg.use_facilities:
        for e, allowed in p.allowed_rooms.items():
            forbidden = [r for r in p.rooms if r not in allowed]
            if forbidden:
                add(f"E4 (exam {e} needs a room with its required facilities)",
                    *[room[e] != r for r in forbidden])

    # SB  symmetry breaking (only for the "symmetry" formulation):
    #     for every pair of interchangeable rooms a < b and every slot t:
    #       (some exam uses room b in slot t)  ->  (some exam uses room a in slot t)
    #     Any timetable can be turned into one that obeys this by swapping
    #     twin rooms within a slot, so no answer is lost; only the duplicate
    #     timetables that differ by such a swap are removed.
    #     [report 3.2, eqs. S1-S2]
    if symmetry:
        uses = lambda r, t: Or([And(slot[e] == t, room[e] == r) for e in p.exams])
        for a, b in twin_rooms(p):
            for t in p.slots:
                add(f"SB (rooms {a} and {b} are interchangeable: room {a} first in slot {t})",
                    Implies(uses(b, t), uses(a, t)))

    if not track:
        s.add(*[c for _, c in items])
        return v, len(items)

    # Tracked: one switch per labelled rule, "switch -> rule"
    groups: Dict[str, list] = {}
    for label, c in items:
        groups.setdefault(label, []).append(c)
    labels = {}
    for i, (label, cs) in enumerate(groups.items()):
        name = f"track_{i}"
        s.add(Implies(Bool(name), And(cs) if len(cs) > 1 else cs[0]))
        labels[name] = label
    return v, len(items), labels


def read_timetable(m, p: Problem, v: IntVars) -> Dict[int, Placement]:
    """Turn a Z3 model into exam -> Placement(slot, room)."""
    val = lambda x: m.eval(x, model_completion=True).as_long()
    return {e: Placement(val(v.slot[e]), val(v.room[e])) for e in p.exams}


def solve_integer_model(p: Problem, name: str, symmetry: bool) -> Result:
    t0 = time.perf_counter()
    s = Solver()
    if TIMEOUT_MS:
        s.set("timeout", TIMEOUT_MS)
    v, n = build_integer_model(p, s, symmetry=symmetry)
    build_ms = (time.perf_counter() - t0) * 1000

    status, solve_ms = timed(s.check)              # step 2 of the brief: only this is timed

    timetable = read_timetable(s.model(), p, v) if status == sat else {}
    return Result(name, str(status), timetable, solve_ms, build_ms,
                  num_variables=v.count(), num_constraints=n)


@register("integer")
def solve_integer(p: Problem) -> Result:
    return solve_integer_model(p, "integer", symmetry=False)


@register("symmetry")
def solve_symmetry(p: Problem) -> Result:
    """Alternative: the integer model plus symmetry breaking (SB)."""
    return solve_integer_model(p, "symmetry", symmetry=True)


# =============================================================================
# 7. MULTIPLE SOLUTIONS  [report 4.4, eq. 4.1]
# =============================================================================
# After each solution, add a "blocking clause" saying: at least one exam must
# get a different slot or room than in this solution. Then check again.
# Repeat until unsat (all solutions found) or the limit is reached.
def enumerate_solutions(p: Problem, limit: int = 1000,
                        symmetry: bool = False) -> Tuple[List[Dict[int, Placement]], bool, float]:
    """Return (solutions found, complete?, total ms). With symmetry=True the
    timetables that differ only by swapping twin rooms are counted once."""
    s = Solver()
    v, _ = build_integer_model(p, s, symmetry=symmetry)
    solutions = []
    start = time.perf_counter()
    while len(solutions) < limit and s.check() == sat:
        tt_ = read_timetable(s.model(), p, v)
        solutions.append(tt_)
        if not p.exams:                       # nothing to vary: exactly one solution
            break
        differs = []
        for e in p.exams:
            differs += [v.slot[e] != tt_[e].slot, v.room[e] != tt_[e].room]
        s.add(Or(differs))
    complete = len(solutions) < limit or s.check() == unsat
    return solutions, complete, (time.perf_counter() - start) * 1000


# =============================================================================
# 8. ALTERNATIVE: OPTIMISATION, the best timetable  [report 3.3, eqs. O1-O3]
# =============================================================================
# Same hard constraints (M1-M5 + switched-on extras), plus two goals,
# minimised in priority order (lexicographic):
#   1. finish the exam period as early as possible:
#        minimise last,  where  last >= slot_e  for all e,  0 <= last <= |T|-1
#   2. E3, efficient room use: fewest empty seats
#        minimise  sum over e of ( c(room_e) - n(e) )
# The upper bound on `last` is needed: with Z3 5.3.3, minimising a variable
# that had only lower bounds produced models that broke the constraints
# (found by the independent checker). With the bound, Optimize's models are
# valid, and each optimum is re-proved below with a plain Solver.
def timetable_metrics(p: Problem, timetable: Dict[int, Placement]) -> Tuple[int, int]:
    """(last slot used, total empty seats) of a timetable."""
    if not timetable:
        return -1, 0
    last = max(pl.slot for pl in timetable.values())
    wasted = sum(p.capacity[pl.room] - p.size[e] for e, pl in timetable.items())
    return last, wasted


def add_objectives(p: Problem, s, v: IntVars):
    """Add the goal variables to solver s; return (last slot, empty seats)."""
    if not p.exams:
        return IntVal(0), IntVal(0)
    last = Int("last_slot")
    s.add(*[last >= v.slot[e] for e in p.exams], last <= len(p.slots) - 1)
    seats = [If(v.room[e] == r, p.capacity[r], 0) for e in p.exams for r in p.rooms]
    wasted = Sum(seats) - sum(p.size) if seats else IntVal(0)   # no rooms: unsat anyway
    return last, wasted


def prove_optimal(p: Problem, last_value: int, wasted_value: int) -> str:
    """Ask a fresh plain Solver for a strictly better timetable:
    last < L*, or last = L* and wasted < W*. 'unsat' proves the optimum."""
    s = Solver()
    if TIMEOUT_MS:
        s.set("timeout", TIMEOUT_MS)
    v, _ = build_integer_model(p, s)
    last, wasted = add_objectives(p, s, v)
    s.add(Or(last < last_value, And(last == last_value, wasted < wasted_value)))
    return str(s.check())


@register("optimize")
def solve_optimize(p: Problem) -> Result:
    t0 = time.perf_counter()
    o = Optimize()
    if TIMEOUT_MS:
        o.set("timeout", TIMEOUT_MS)
    v, n = build_integer_model(p, o)
    last, wasted = add_objectives(p, o, v)
    o.minimize(last)                         # goal 1 (higher priority)
    o.minimize(wasted)                       # goal 2 (E3)
    build_ms = (time.perf_counter() - t0) * 1000

    status, solve_ms = timed(o.check)        # the whole optimisation happens here

    timetable = read_timetable(o.model(), p, v) if status == sat else {}
    res = Result("optimize", str(status), timetable, solve_ms, build_ms,
                 num_variables=v.count() + (1 if p.exams else 0),
                 num_constraints=n + (len(p.exams) + 1 if p.exams else 0))
    if timetable:
        res.notes["last_slot"], res.notes["wasted_seats"] = timetable_metrics(p, timetable)
        start = time.perf_counter()
        res.notes["optimality"] = prove_optimal(p, res.notes["last_slot"], res.notes["wasted_seats"])
        res.notes["optimality_ms"] = (time.perf_counter() - start) * 1000
    return res


# =============================================================================
# 9. ALTERNATIVE: BOOLEAN (PSEUDO-BOOLEAN) MODEL  [report 3.1, eqs. B1-B11]
# =============================================================================
# One True/False variable per possible placement instead of two integers per
# exam:
#   x_{e,t,r} = True  iff exam e is in slot t and room r
#       only rooms that fit get a variable (M3 is built in: rooms that are
#       too small get no variable at all)
#   z_{e,t}   = True  iff exam e is in slot t   (z_{e,t} <-> OR_r x_{e,t,r})
# The rules become counting ("pseudo-Boolean") constraints over these
# variables, which Z3 handles with PbEq / AtMost / PbLe.
# [report eq. B1]
def room_options(p: Problem, e: int) -> List[int]:
    """Rooms big enough for exam e (M3)."""
    return [r for r in p.rooms if p.capacity[r] >= p.size[e]]


@register("boolean")
def solve_boolean(p: Problem) -> Result:
    cfg = p.config
    t0 = time.perf_counter()
    s = Solver()
    if TIMEOUT_MS:
        s.set("timeout", TIMEOUT_MS)
    num_slots = len(p.slots)

    x: Dict[Tuple[int, int, int], object] = {}
    by_exam: Dict[int, list] = {e: [] for e in p.exams}
    by_exam_slot: Dict[Tuple[int, int], list] = {}
    by_slot_room: Dict[Tuple[int, int], list] = {}
    for e in p.exams:
        for t in p.slots:
            for r in room_options(p, e):
                b = Bool(f"x_{e}_{t}_{r}")
                x[(e, t, r)] = b
                by_exam[e].append(b)
                by_exam_slot.setdefault((e, t), []).append(b)
                by_slot_room.setdefault((t, r), []).append(b)
    z = {(e, t): Bool(f"z_{e}_{t}") for e in p.exams for t in p.slots}
    cons = []

    # M1 (+M3)  for all e:  sum over t, r of x_{e,t,r} = 1   [report eq. B4]
    #           (only options that fit exist, so M3 holds by construction)
    for e in p.exams:
        cons.append(PbEq([(b, 1) for b in by_exam[e]], 1) if by_exam[e] else BoolVal(False))

    # link      for all e, t:  z_{e,t} <-> OR over r of x_{e,t,r}   [report eq. B5]
    for (e, t), zb in z.items():
        xs = by_exam_slot.get((e, t), [])
        cons.append(zb == Or(xs) if xs else Not(zb))

    # M2  for all t, r:  sum over e of x_{e,t,r}  <=  1   [report eq. B6]
    for bs in by_slot_room.values():
        if len(bs) > 1:
            cons.append(AtMost(*bs, 1))

    # M4 + M5  for all {e, f} in C and every pair of neighbouring slots t, t+1:
    #            z_{e,t} + z_{e,t+1} + z_{f,t} + z_{f,t+1}  <=  1
    #          (e and f never share a slot or sit in neighbouring slots)
    #     [report eqs. B7-B8]
    for e, f in p.conflicts:
        if num_slots == 1:
            cons.append(AtMost(z[(e, 0)], z[(f, 0)], 1))
        for t in range(num_slots - 1):
            cons.append(AtMost(z[(e, t)], z[(e, t + 1)], z[(f, t)], z[(f, t + 1)], 1))

    # E1  for every student exam set G and day d:  sum of z_{e,t} (e in G, t in d)  <=  K
    #     [report eq. B9]
    if cfg.use_max_per_day:
        for group in p.day_groups:
            for day in range(p.num_days()):
                day_slots = [t for t in p.slots if p.day_of(t) == day]
                cons.append(PbLe([(z[(e, t)], 1) for e in sorted(group) for t in day_slots],
                                 cfg.max_exams_per_day))

    # E2  for all t:  sum over e of inv(e) * z_{e,t}  <=  I   [report eq. B10]
    if cfg.use_invigilators:
        for t in p.slots:
            terms = [(z[(e, t)], p.invigilators_needed[e]) for e in p.exams if p.invigilators_needed[e] > 0]
            if terms:
                cons.append(PbLe(terms, cfg.invigilators_per_slot))

    # E4  for all e with requirements:  every x_{e,t,r} with r lacking a
    #     required facility is False   [report eq. B11]
    if cfg.use_facilities:
        for e, allowed in p.allowed_rooms.items():
            bad = [b for (e2, t, r), b in x.items() if e2 == e and r not in allowed]
            if bad:
                cons.append(Not(Or(bad)))

    s.add(*cons)
    build_ms = (time.perf_counter() - t0) * 1000

    status, solve_ms = timed(s.check)

    timetable = {}
    if status == sat:
        m = s.model()
        for (e, t, r), b in x.items():
            if is_true(m.eval(b, model_completion=True)):
                timetable[e] = Placement(t, r)
    return Result("boolean", str(status), timetable, solve_ms, build_ms,
                  num_variables=len(x) + len(z), num_constraints=len(cons))


# =============================================================================
# 10. UNSAT EXPLANATION  [report 4.5]
# =============================================================================
# Every rule of the integer model sits behind its own switch. Z3 is asked to
# solve with all switches on; when the answer is unsat, unsat_core() names a
# set of switches that already makes it impossible. We then try leaving out
# each rule in turn and keep it out whenever the rest is still unsat, which
# leaves a small set of rules that clash ("why is this file impossible?").
RULE_ORDER = ["M1", "M2", "M3", "M4", "M5", "E1", "E2", "E4"]


def explain_unsat(p: Problem) -> Optional[List[str]]:
    """None if a timetable exists; otherwise the clashing rules, readable."""
    s = Solver()
    if TIMEOUT_MS:
        s.set("timeout", TIMEOUT_MS)
    _, _, labels = build_integer_model(p, s, track=True)
    switch = {name: Bool(name) for name in labels}
    if s.check([switch[n] for n in labels]) != unsat:
        return None
    names = [str(b) for b in s.unsat_core()]
    i = 0
    while i < len(names):                        # try to drop rule i
        trial = names[:i] + names[i + 1:]
        if s.check([switch[n] for n in trial]) == unsat:
            core = {str(b) for b in s.unsat_core()}
            names = [n for n in trial if n in core]
        else:
            i += 1                               # rule i is needed
    found = [labels[n] for n in names]
    return sorted(found, key=lambda lab: (RULE_ORDER.index(lab.split()[0]), lab))


def rules_in(explanation: List[str]) -> str:
    """'M1, M3' from a list of labels."""
    codes = {lab.split()[0] for lab in explanation}
    return ", ".join(c for c in RULE_ORDER if c in codes)


# =============================================================================
# 11. BRUTE-FORCE REFERENCE  (not Z3: ground truth for small instances)  [report 4.6]
# =============================================================================
def _candidates(p: Problem, e: int):
    """All (slot, room) options for exam e that pass the per-exam rules
    (M1 ranges, M3 capacity, E4 facilities)."""
    options = [r for r in p.rooms if p.capacity[r] >= p.size[e]]
    if p.config.use_facilities and e in p.allowed_rooms:
        options = [r for r in options if r in p.allowed_rooms[e]]
    for t in p.slots:
        for r in options:
            yield t, r


def _compatible(p, e, t, r, placed, slot_invig, student_day):
    """Can exam e go to slot t and room r, given the exams placed so far?"""
    for f, (u, q) in placed.items():
        if u == t and r == q:
            return False                                        # M2
        if f in p.conflicts_of[e] and abs(u - t) <= 1:
            return False                                        # M4 / M5
    if p.config.use_max_per_day:                                # E1
        day = p.day_of(t)
        for s in p.students_of[e]:
            if student_day.get((s, day), 0) + 1 > p.config.max_exams_per_day:
                return False
    if p.config.use_invigilators:                               # E2
        if slot_invig.get(t, 0) + p.invigilators_needed[e] > p.config.invigilators_per_slot:
            return False
    return True


def search(p: Problem, count: bool = False, limit: int = 10**7, deadline: Optional[float] = None,
           visit: Optional[Callable[[Dict[int, Placement]], None]] = None):
    """Return (first timetable or None, number of timetables found).
    With count=True every timetable is visited (and passed to `visit`).
    Raises TimeoutError if `deadline` (a time.perf_counter() value) passes."""
    order = sorted(p.exams, key=lambda e: -len(p.conflicts_of[e]))   # hardest first
    cands = {e: list(_candidates(p, e)) for e in p.exams}
    placed, slot_invig, student_day = {}, {}, {}
    found = {"first": None, "n": 0}

    def bt(i):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError
        if i == len(order):
            found["n"] += 1
            timetable = {e: Placement(t, r) for e, (t, r) in placed.items()}
            if found["first"] is None:
                found["first"] = timetable
            if visit is not None:
                visit(timetable)
            return not count or found["n"] >= limit
        e = order[i]
        for t, r in cands[e]:
            if not _compatible(p, e, t, r, placed, slot_invig, student_day):
                continue
            placed[e] = (t, r)
            slot_invig[t] = slot_invig.get(t, 0) + p.invigilators_needed[e]
            for s in p.students_of[e]:
                student_day[(s, p.day_of(t))] = student_day.get((s, p.day_of(t)), 0) + 1
            stop = bt(i + 1)
            slot_invig[t] -= p.invigilators_needed[e]
            for s in p.students_of[e]:
                student_day[(s, p.day_of(t))] -= 1
            del placed[e]
            if stop:
                return True
        return False

    bt(0)
    return found["first"], found["n"]


@register("reference")  # registered after the Z3 formulation(s), so not the default
def solve_reference(p: Problem) -> Result:
    """Exhaustive search; only practical for small instances."""
    deadline = time.perf_counter() + TIMEOUT_MS / 1000 if TIMEOUT_MS else None
    start = time.perf_counter()
    try:
        first, _ = search(p, deadline=deadline)
    except TimeoutError:
        return Result("reference", "unknown", {}, solve_ms=(time.perf_counter() - start) * 1000)
    ms = (time.perf_counter() - start) * 1000
    return Result("reference", "sat" if first is not None else "unsat", first or {}, solve_ms=ms)


def reference_optimum(p: Problem) -> Optional[Tuple[int, int]]:
    """Best (last slot, empty seats) over ALL timetables, by exhaustive search
    (no Z3): ground truth for the optimize formulation. None if unsat."""
    best: Dict[str, Tuple[int, int]] = {}

    def visit(timetable):
        value = timetable_metrics(p, timetable)
        if "v" not in best or value < best["v"]:          # tuples compare lexicographically
            best["v"] = value

    search(p, count=True, visit=visit)
    return best.get("v")

# =============================================================================
# 12. OUTPUT AND RUNNER
# =============================================================================
def print_result(p: Problem, res: Result) -> None:
    """Required output order: sat/unsat, the timetable, then time in ms."""
    print(res.status)
    if res.status == "sat":
        print(f"  {'Slot':>4}  {'Room':>5}  {'Exam':>4}  Students")
        for e, pl in sorted(res.timetable.items(), key=lambda kv: (kv[1].slot, kv[1].room, kv[0])):
            print(f"  {pl.slot:>4}  {pl.room:>5}  {e:>4}  {p.size[e]}")
    print(f"Time: {res.solve_ms:.3f} ms")
    if "last_slot" in res.notes:
        proof = {"unsat": "proved optimal", "sat": "NOT optimal", "unknown": "optimality not proved"}
        print(f"Objective: last slot used = {res.notes['last_slot']}, "
              f"empty seats = {res.notes['wasted_seats']} "
              f"({proof.get(res.notes['optimality'], res.notes['optimality'])})")


def expected_from_name(path: str) -> Optional[str]:
    base = os.path.basename(path).lower()
    if base.startswith("unsat"):
        return "unsat"
    if base.startswith("sat"):
        return "sat"
    return None


def natural_key(path: str):
    """Sort sat2 before sat10."""
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", os.path.basename(path))]


def collect_files(paths: List[str]) -> List[str]:
    files = []
    for path in paths:
        if os.path.isdir(path):
            files += [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
        elif os.path.isfile(path):
            files.append(path)
        else:
            print(f'File not found: {path}  (give a real file, e.g. "test instances/sat2.txt")')
    return sorted(files, key=natural_key)


def run_file(path: str, formulation: str, config: Config, repeat: int = 1) -> Tuple[Problem, Result, List[str]]:
    """Solve one instance `repeat` times; report the median check() time."""
    p = preprocess(read_file(path), config, name=os.path.basename(path))
    solver = FORMULATIONS[formulation]
    runs = [solver(p) for _ in range(max(1, repeat))]
    res = runs[0]
    res.solve_ms = statistics.median(r.solve_ms for r in runs)
    res.build_ms = statistics.median(r.build_ms for r in runs)
    statuses = {r.status for r in runs}
    if len(statuses) > 1:
        res.notes["inconsistent_status"] = sorted(statuses)
    violations = check_timetable(p, res.timetable) if res.status == "sat" else []
    return p, res, violations


def run_batch(files: List[str], formulation: str, config: Config, repeat: int, quiet: bool) -> int:
    """Run every file, print a summary table, return the number of problems found.

    'Expected' comes from the filename (satN / unsatN) and is only meaningful
    for M1-M5; with extras switched on, a changed answer is reported as a
    FLIP rather than an error (E1, E2 and E4 can make sat -> unsat). Every sat
    timetable is still checked, and an optimum that a Solver can beat counts
    as a problem.
    """
    extras = config.active_extras()
    print(f"Formulation: {formulation}   Extras: {', '.join(extras) or 'none'}   "
          f"Repeats: {repeat}\n")
    rows, problems = [], 0
    for path in files:
        p, res, viol = run_file(path, formulation, config, repeat)
        if not quiet:
            print(f"== {p.name}")
            print_result(p, res)
            for msg in viol:
                print("  VIOLATION:", msg)
            print()
        exp = expected_from_name(path)
        if viol:
            verdict = "INVALID TIMETABLE"
        elif res.notes.get("optimality") == "sat":
            verdict = "NOT OPTIMAL"
        elif exp is None:
            verdict = "-"
        elif res.status == exp:
            verdict = "ok"
        elif not extras:
            verdict = "WRONG"
        else:
            verdict = "flip (extras)"      # an extra rule changed the answer
        if verdict in ("WRONG", "INVALID TIMETABLE", "NOT OPTIMAL") or "inconsistent_status" in res.notes:
            problems += 1
        rows.append((p.name, exp or "?", res.status, res.build_ms, res.solve_ms,
                     res.num_variables, res.num_constraints, verdict))

    print(f"{'File':<12}{'Expected':<10}{'Got':<9}{'Build ms':>10}{'Solve ms':>10}"
          f"{'Vars':>7}{'Cons':>7}  Verdict")
    for name, exp, got, b, s, nv, nc, verdict in rows:
        print(f"{name:<12}{exp:<10}{got:<9}{b:>10.3f}{s:>10.3f}"
              f"{'-' if nv is None else nv:>7}{'-' if nc is None else nc:>7}  {verdict}")
    print(f"\n{len(rows)} file(s), {problems} problem(s)")
    return problems


# =============================================================================
# 13. EXPERIMENTS  (results/*.csv for the report)  [report Section 5]
# =============================================================================
def generate_instance(num_exams: int, seed: int, tight: bool = False) -> Instance:
    """Random instance for scaling tests (same seed -> same instance).
    4 students per exam, each student takes 1-3 exams, rooms = exams / 4,
    capacities 15-60. Loose: slots = exams. Tight: slots = exams / 2, which
    is near the sat/unsat boundary and much harder to search."""
    rng = random.Random(seed)
    inst = Instance()
    inst.number_of_exams = num_exams
    inst.number_of_students = 4 * num_exams
    inst.number_of_slots = math.ceil(num_exams / 2) if tight else num_exams
    inst.number_of_rooms = max(2, math.ceil(num_exams / 4))
    inst.room_capacities = [rng.randint(15, 60) for _ in range(inst.number_of_rooms)]
    pairs = set()
    for st in range(inst.number_of_students):
        for e in rng.sample(range(num_exams), min(num_exams, rng.randint(1, 3))):
            pairs.add((e, st))
    inst.exams_to_students = sorted(pairs)
    return inst


CONFIGS = {
    "core": Config(),
    "E1": Config(use_max_per_day=True),
    "E2": Config(use_invigilators=True),
    "E4": Config(use_facilities=True),
    "all": Config(use_max_per_day=True, use_invigilators=True, use_facilities=True),
}


def write_csv(path: str, rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  saved {path} ({len(rows)} rows)")


def run_experiments(files: List[str], repeat: int, timeout_s: float, quick: bool) -> int:
    """Run every experiment and save CSV files in results/ next to this file."""
    global TIMEOUT_MS
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    TIMEOUT_MS = int(timeout_s * 1000)
    print(f"Experiments: {len(files)} files, {repeat} repeat(s), timeout {timeout_s:g}s\n")

    # 1. Sample instances x constraint sets x formulations
    print("[1/3] Sample instances")
    rows = []
    plan = [(f, c) for f in ("integer", "symmetry", "boolean", "optimize", "reference")
            for c in CONFIGS]
    for formulation, cname in plan:
        for path in files:
            p, res, viol = run_file(path, formulation, CONFIGS[cname], repeat)
            last, wasted = timetable_metrics(p, res.timetable)
            rows.append({"file": p.name[:-4], "expected_core": expected_from_name(path) or "",
                         "constraints": cname, "formulation": formulation,
                         "status": res.status, "valid": "yes" if res.status == "sat" and not viol
                         else ("NO" if viol else ""),
                         "build_ms": round(res.build_ms, 3), "solve_ms": round(res.solve_ms, 3),
                         "variables": res.num_variables if res.num_variables is not None else "",
                         "constraints_count": res.num_constraints if res.num_constraints is not None else "",
                         "last_slot": last if res.timetable else "",
                         "wasted_seats": wasted if res.timetable else "",
                         "optimality": res.notes.get("optimality", ""),
                         "optimality_ms": round(res.notes["optimality_ms"], 3)
                         if "optimality_ms" in res.notes else ""})
        print(f"  {formulation:<9} {cname:<9} done")
    write_csv(os.path.join(out, "samples.csv"), rows)

    # 2. Multiple solutions: Z3 blocking-clause enumeration vs exhaustive count
    print("[2/3] Multiple solutions")
    rows = []
    small = [f for f in files if expected_from_name(f) == "sat" and
             os.path.basename(f)[:-4] in ("sat1", "sat2", "sat3", "sat4", "sat5", "sat6", "sat7", "sat8")]
    cap = 200 if quick else 2000
    for path in small:
        p = preprocess(read_file(path), Config(), os.path.basename(path))
        sols, complete, ms = enumerate_solutions(p, limit=cap)
        sym, sym_complete, sym_ms = enumerate_solutions(p, limit=cap, symmetry=True)
        bad = sum(1 for t in sols + sym if check_timetable(p, t))
        ref_start = time.perf_counter()
        _, ref_n = search(p, count=True)
        ref_ms = (time.perf_counter() - ref_start) * 1000
        rows.append({"file": p.name[:-4], "z3_solutions": len(sols), "z3_complete": complete,
                     "z3_ms": round(ms, 1), "invalid_found": bad,
                     "true_count": ref_n, "reference_count_ms": round(ref_ms, 1),
                     "symmetry_solutions": len(sym), "symmetry_complete": sym_complete,
                     "symmetry_ms": round(sym_ms, 1)})
        print(f"  {p.name:<10} Z3 {len(sols)}{'' if complete else '+ (capped)'}  true {ref_n}"
              f"  with symmetry breaking {len(sym)}{'' if sym_complete else '+ (capped)'}")
    write_csv(os.path.join(out, "solutions.csv"), rows)

    # 2b. Why each unsat file is impossible (core rules, E1 alone, all extras)
    print("[2b] Unsat explanations")
    rows = []
    for cname in ("core", "E1", "all"):
        for path in files:
            p = preprocess(read_file(path), CONFIGS[cname], os.path.basename(path))
            start = time.perf_counter()
            why = explain_unsat(p)
            ms = (time.perf_counter() - start) * 1000
            if why is None:
                continue
            rows.append({"constraints": cname, "file": p.name[:-4], "rules": rules_in(why),
                         "core_size": len(why), "explanation": "; ".join(why), "ms": round(ms, 1)})
            print(f"  {cname:<5} {p.name:<12} {rules_in(why)}")
    write_csv(os.path.join(out, "explain.csv"), rows)

    # 3. Scaling on random instances (core constraints)
    print("[3/3] Scaling on random instances")
    rows = []
    sizes = [5, 10, 20, 40] if quick else [5, 10, 15, 20, 30, 40, 60, 80]
    for family in ("loose", "tight"):
        for n in sizes:
            for seed in (1, 2):
                inst = generate_instance(n, seed, tight=(family == "tight"))
                p = preprocess(inst, Config(), f"{family}_{n}_{seed}")
                for formulation in ("integer", "symmetry", "boolean", "optimize", "reference"):
                    res = FORMULATIONS[formulation](p)
                    viol = check_timetable(p, res.timetable) if res.status == "sat" else []
                    rows.append({"family": family, "exams": n, "seed": seed,
                                 "students": inst.number_of_students,
                                 "slots": inst.number_of_slots, "rooms": inst.number_of_rooms,
                                 "conflict_pairs": len(p.conflicts), "formulation": formulation,
                                 "status": "timeout" if res.status == "unknown" else res.status,
                                 "valid": "NO" if viol else ("yes" if res.status == "sat" else ""),
                                 "build_ms": round(res.build_ms, 3),
                                 "solve_ms": round(res.solve_ms, 3)})
                print(f"  {family} {n:>3} exams, seed {seed}: " +
                      ", ".join(f"{r['formulation']} {r['status']} {r['solve_ms']:.0f}ms"
                                for r in rows[-5:]))
    write_csv(os.path.join(out, "scaling.csv"), rows)
    TIMEOUT_MS = None
    print("\nDone. Send the results/ folder for the summary tables.")
    return 0


# =============================================================================
# 14. SELF-TEST AND COMMAND LINE
# =============================================================================
def default_instance_folder() -> str:
    """Look for the instances folder next to this file (either spelling)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("test_instances", "test instances", "instances"):
        path = os.path.join(here, name)
        if os.path.isdir(path):
            return path
    return here


def self_test() -> int:
    """Check the foundation (parser, preprocessing, checker, reference) against
    results worked out by hand / by exhaustive search. Needs the 20 samples."""
    folder = default_instance_folder()
    files = collect_files([folder])
    names = [os.path.basename(f)[:-4] for f in files]
    failures = []

    def expect(label, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected {want}\n         got      {got}")
            failures.append(label)

    def load(name, **cfg):
        return preprocess(read_file(os.path.join(folder, name + ".txt")), Config(**cfg), name)

    def unsat_names(**cfg):
        out = []
        for f, n in zip(files, names):
            p = preprocess(read_file(f), Config(**cfg), n)
            first, _ = search(p)
            if first is None:
                out.append(n)
            elif check_timetable(p, first):
                failures.append(f"checker rejected reference solution for {n}")
        return out

    print(f"Self-test using {len(files)} files in {folder}\n")
    p = load("sat2")
    expect("parser + preprocessing: sat2 sizes and conflicts",
           (p.size, p.conflicts), ([2, 1], [(0, 1)]))
    expect("checker accepts a valid sat2 timetable",
           check_timetable(p, {0: Placement(0, 0), 1: Placement(2, 0)}), [])
    expect("checker catches back-to-back exams (M4)",
           [m[:2] for m in check_timetable(p, {0: Placement(0, 0), 1: Placement(1, 0)})], ["M4"])
    all_unsat = [f"unsat{i}" for i in range(1, 11)]
    expect("M1-M5: exactly the 10 unsat files are unsat", unsat_names(), all_unsat)
    expect("E1 max 2 exams/day (5 slots/day): sat7, sat8, sat9 become unsat",
           [n for n in unsat_names(use_max_per_day=True) if n.startswith("sat")],
           ["sat7", "sat8", "sat9"])
    expect("E2 invigilators + E4 lab (default rule): still exactly the 10 unsat files",
           unsat_names(use_invigilators=True, use_facilities=True), all_unsat)
    agree = []
    for f, n in zip(files, names):
        for cname in ("core", "all"):
            p = preprocess(read_file(f), CONFIGS[cname], n)
            ref = solve_reference(p).status
            for form in ("integer", "symmetry", "boolean", "optimize"):
                r = FORMULATIONS[form](p)
                if r.status != ref or (r.status == "sat" and check_timetable(p, r.timetable)):
                    agree.append(f"{form}/{cname}/{n}")
    expect("all four Z3 formulations agree with brute force (core and all extras)", agree, [])
    optimum = []
    for n in ("sat1", "sat2", "sat3", "sat4", "sat5", "sat6", "sat7", "sat8"):
        r = solve_optimize(load(n))
        got = (r.notes.get("last_slot"), r.notes.get("wasted_seats"), r.notes.get("optimality"))
        want = reference_optimum(load(n)) + ("unsat",)
        if got != want:
            optimum.append(f"{n}: got {got}, exhaustive search gives {want}")
    expect("optimize: best (last slot, empty seats) equals the exhaustive optimum, and is proved",
           optimum, [])
    bad_inputs = {"unknown line": "x", "student out of range": "1 5",
                  "duplicate day length": "Slots per day: 5\nSlots per day: 5",
                  "room out of range": "Room 3 facilities: lab"}
    header = "Number of students: 2\nNumber of exams: 2\nNumber of slots: 3\nNumber of rooms: 1\nRoom 0 capacity: 5\n"
    accepted = []
    for label, body in bad_inputs.items():
        try:
            parse_instance(header + body)
            accepted.append(label)
        except ValueError:
            pass
    expect("parser rejects malformed input", accepted, [])
    q = preprocess(parse_instance(header + "0 0\nRoom 0 facilities: Lab\nExam 1 requirements: lab, computers"),
                   Config(use_facilities=True), "facilities")
    expect("E4 reads facilities from the file (case-insensitive, all needs in one room)",
           (q.facilities_from_file, q.allowed_rooms), (True, {1: frozenset()}))
    expect("unsat explanation: unsat1 is impossible because of M1 + M3",
           rules_in(explain_unsat(load("unsat1")) or []), "M1, M3")
    counts = {n: search(load(n), count=True)[1] for n in ("sat1", "sat2", "sat3", "sat4", "sat5", "sat8")}
    expect("solution counts (for the multiple-solutions feature)",
           counts, {"sat1": 1, "sat2": 2, "sat3": 2, "sat4": 1, "sat5": 2, "sat8": 162})
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


def run_tests(path: str) -> int:
    """Targeted constraint tests (constraint_tests.zip or an unpacked folder).
    expected.json lists, for every valid case, the answer under the core
    rules and under all extras, the optimum (last slot, empty seats) and
    sometimes the number of timetables; these expectations were computed
    by exhaustive search (no Z3). Files under invalid/ must be rejected."""
    import json, zipfile
    if zipfile.is_zipfile(path):
        z = zipfile.ZipFile(path)
        read = lambda name: z.read(name).decode("utf-8")
        names = z.namelist()
    else:
        read = lambda name: open(os.path.join(path, name), encoding="utf-8").read()
        names = [os.path.relpath(os.path.join(d, f), path).replace(os.sep, "/")
                 for d, _, fs in os.walk(path) for f in fs]
    manifest = json.loads(read("expected.json"))
    passed, failed = 0, []

    def check(ok, label):
        nonlocal passed
        if ok:
            passed += 1
        else:
            failed.append(label)

    for case in manifest["cases"]:
        inst = parse_instance(read(case["file"]))
        for cname in ("core", "all"):
            p = preprocess(inst, CONFIGS[cname], case["file"])
            for form in ("integer", "symmetry", "boolean", "optimize"):
                r = FORMULATIONS[form](p)
                label = f"{case['file']} [{cname}, {form}]"
                check(r.status == case[cname], f"{label}: {r.status}, expected {case[cname]}")
                if r.status == "sat":
                    check(not check_timetable(p, r.timetable), f"{label}: invalid timetable")
                if form == "optimize" and r.status == "sat" and f"optimum_{cname}" in case:
                    got = [r.notes["last_slot"], r.notes["wasted_seats"]]
                    check(got == case[f"optimum_{cname}"] and r.notes["optimality"] == "unsat",
                          f"{label}: optimum {got}, expected {case[f'optimum_{cname}']}")
        if "solutions_core" in case:
            p = preprocess(inst, CONFIGS["core"], case["file"])
            sols, _, _ = enumerate_solutions(p, limit=case["solutions_core"] + 1)
            check(len(sols) == case["solutions_core"],
                  f"{case['file']}: {len(sols)} timetables, expected {case['solutions_core']}")
    invalid = sorted(n for n in names if n.startswith("invalid/") and n.endswith(".txt"))
    for name in invalid:
        try:
            parse_instance(read(name))
            check(False, f"{name}: malformed input was accepted")
        except ValueError:
            check(True, name)
    print(f"Constraint tests: {len(manifest['cases'])} valid cases, {len(invalid)} malformed inputs")
    for label in failed:
        print("  FAIL", label)
    print(f"{passed} passed, {len(failed)} failed")
    return 1 if failed else 0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Z3 exam timetabling solver (COMP3070 CW1)")
    ap.add_argument("paths", nargs="*",
                    help="instance file(s) and/or folder(s); default: test_instances/")
    ap.add_argument("-f", "--formulation", default=None,
                    help="which formulation to run (default: the first Z3 one)")
    ap.add_argument("--e1", action="store_true", help="E1 max 2 exams per student per day")
    ap.add_argument("--e2", action="store_true", help="E2 invigilators (1 per 30, 2 per slot)")
    ap.add_argument("--e4", action="store_true", help="E4 rooms must have the facilities an exam requires")
    ap.add_argument("--repeat", type=int, default=1, help="runs per file; median time reported")
    ap.add_argument("--quiet", action="store_true", help="summary table only")
    ap.add_argument("--selftest", action="store_true", help="check the foundation code")
    ap.add_argument("--tests", nargs="?", const="constraint_tests.zip", metavar="ZIP",
                    help="run the targeted tests in constraint_tests.zip (or a folder)")
    ap.add_argument("--explain", action="store_true",
                    help="for every unsat instance, show which rules clash")
    ap.add_argument("--solutions", type=int, metavar="N",
                    help="find up to N different timetables with Z3 (multiple solutions)")
    ap.add_argument("--experiment", action="store_true",
                    help="run all experiments and save CSV files in results/")
    ap.add_argument("--quick", action="store_true", help="smaller, faster --experiment")
    ap.add_argument("--timeout", type=float, default=10, help="seconds per solve in --experiment")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.selftest:
        return self_test()
    if args.tests:
        path = args.tests
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.tests)
        if not os.path.exists(path):
            print(f"Test archive not found: {args.tests}")
            return 1
        return run_tests(path)
    config = Config(use_max_per_day=args.e1, use_invigilators=args.e2,
                    use_facilities=args.e4)
    files = collect_files(args.paths or [default_instance_folder()])
    if not files:
        print("No .txt instance files found.")
        return 1

    if args.experiment:
        return run_experiments(files, 1 if args.quick else max(args.repeat, 5), args.timeout, args.quick)

    if args.solutions:
        for path in files:
            p = preprocess(read_file(path), config, os.path.basename(path))
            sols, complete, ms = enumerate_solutions(p, args.solutions)
            more = "" if complete else f" (stopped at the limit of {args.solutions})"
            print(f"{p.name}: {len(sols)} solution(s){more} in {ms:.1f} ms")
            if len(files) == 1:
                for i, t in enumerate(sols[:10], 1):
                    print(f"  #{i}: " + "  ".join(f"exam {e}->slot {pl.slot}, room {pl.room}"
                                                  for e, pl in sorted(t.items())))
                if len(sols) > 10:
                    print(f"  ... and {len(sols) - 10} more")
        return 0

    if args.explain:
        for path in files:
            p = preprocess(read_file(path), config, os.path.basename(path))
            why = explain_unsat(p)
            if why is None:
                print(f"{p.name}: sat (nothing to explain)")
            else:
                print(f"{p.name}: unsat because these {len(why)} rule(s) clash ({rules_in(why)}):")
                for lab in why:
                    print(f"    {lab}")
        return 0

    z3_formulations = [name for name in FORMULATIONS if name != "reference"]
    formulation = args.formulation or (z3_formulations[0] if z3_formulations else None)
    if formulation is None:
        print("No Z3 formulation registered (see section 6).")
        return 1
    if formulation not in FORMULATIONS:
        print(f"Unknown formulation '{formulation}'. Available: {', '.join(FORMULATIONS)}")
        return 1

    if len(files) == 1 and not args.quiet:
        p, res, viol = run_file(files[0], formulation, config, args.repeat)
        print_result(p, res)
        for msg in viol:
            print("VIOLATION:", msg)
        return 1 if viol else 0
    return 1 if run_batch(files, formulation, config, args.repeat, args.quiet) else 0


if __name__ == "__main__":
    sys.exit(main())
