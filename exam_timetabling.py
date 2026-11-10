"""COMP3070 CW1 - Group G: exam timetabling with two Z3 formulations.

Install once: python -m pip install z3-solver
Then press Run in your editor, or run: python exam_timetabling.py
The automatic walkthrough reads the .txt samples in this file's own folder.
Optional command-line arguments remain available with --help.

The lecturer's CW1 template supplies the original Instance fields and text
layout (enrolment lines are EXAM STUDENT). The solver, input extensions,
independent checker and comparison runner are additions to that template.

M1: exactly one room and slot per exam. M2: no room/slot clashes.
M3: sufficient room capacity. M4: no consecutive exams for a student.
M5: no simultaneous exams for a student. M4 also applies across days.
E1: at most MAX_EXAMS_PER_DAY exams per student per day (see settings below).
E2: ceil(exam size / 30) invigilators per exam, two available per slot.
E3: minimise total unused seats; exams remain in exactly one room.
E4: an exam's required facilities must be provided by its room.
Baseline uses M1-M5 only; the full model includes E1-E4.

After the original room-capacity headers, optional lines may be interleaved
with enrolments, e.g.:
    Slots per day: 5
    Room 0 facilities: computers, lab
    Exam 1 requirements: computers
Facility names are case-insensitive. Unspecified facility sets are empty.
Original exam, student, room and slot identifiers are zero-based.

Integer formulation: room[e], slot[e] are bounded integer decisions.
Boolean formulation: x[e,r,t] selects one eligible room/slot per exam;
cardinality constraints enforce exclusivity, student gaps and daily limits.
Both minimise sum(capacity[room[e]] - size[e]) under the same hard rules.
API reference: https://z3prover.github.io/api/html/namespacez3py.html
Optimisation: https://microsoft.github.io/z3guide/docs/optimization/intro/
"""

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path
import platform
import re
from statistics import median
from time import perf_counter
from types import SimpleNamespace
import zipfile

try:
    import z3
except ImportError:
    raise SystemExit("Install Z3 first: python -m pip install z3-solver") from None


# =============================================================================
# 1. SETTINGS - the automatic run needs no command-line arguments
# =============================================================================
REPEATS = 5
MAX_EXAMS_PER_DAY = 3  # E1: change this setting to adjust the daily limit everywhere.
WORKED_EXAMPLE = "sat6.txt"
ENCODINGS = ("integer", "boolean")
CONSTRAINTS = {
    "M1": "Exactly one room and one slot per exam",
    "M2": "No room clashes within a slot",
    "M3": "The assigned room fits all enrolled students",
    "M4": "No consecutive exams for a student, including across days",
    "M5": "No simultaneous exams for a student",
    "E1": f"At most {MAX_EXAMS_PER_DAY} exams per student per day (default: five slots/day)",
    "E2": "One invigilator per 30 students, rounded up per exam; two per slot",
    "E3": "OBJECTIVE: minimise total unused seats; no room splitting",
    "E4": "The assigned room provides all facilities required by the exam",
}


# =============================================================================
# 2. INPUT - the lecturer's Instance fields and optional metadata
# =============================================================================
class Instance:
    def __init__(self):
        self.number_of_students = 0
        self.number_of_exams = 0
        self.number_of_slots = 0
        self.number_of_rooms = 0
        self.room_capacities = []
        self.exams_to_students = []
        self.slots_per_day = 5
        self.room_facilities = {}
        self.exam_requirements = {}


def parse_instance(text):
    """Read the template format plus optional metadata; ignore blank lines."""
    lines = iter((n, line.strip()) for n, line in
                 enumerate(text.lstrip('\ufeff').splitlines(), 1) if line.strip())

    def read_attribute(name):
        try:
            n, line = next(lines)
        except StopIteration:
            raise ValueError(f"Missing {name} attribute") from None
        match = re.fullmatch(rf"{re.escape(name)}:\s*(\d+)", line)
        if not match:
            raise ValueError(f"Line {n}: expected '{name}: <non-negative integer>'")
        return int(match[1])

    instance = Instance()
    for attribute in ("students", "exams", "slots", "rooms"):
        setattr(instance, f"number_of_{attribute}",
                read_attribute(f"Number of {attribute}"))
    instance.room_capacities = [read_attribute(f"Room {r} capacity")
                               for r in range(instance.number_of_rooms)]
    enrolments, metadata = set(), set()
    for n, line in lines:
        pair = re.fullmatch(r"(\d+)\s+(\d+)", line)
        day = re.fullmatch(r"Slots per day:\s*(\d+)", line)
        facility = re.fullmatch(r"(Room|Exam) (\d+) (facilities|requirements):\s*(.*)", line)
        if pair:
            exam, student = map(int, pair.groups())
            if not (exam < instance.number_of_exams and student < instance.number_of_students):
                raise ValueError(f"Line {n}: exam or student identifier out of range")
            enrolments.add((exam, student))
            continue
        if day:
            key = ("Slots per day",)
            instance.slots_per_day = int(day[1])
            if instance.slots_per_day == 0:
                raise ValueError(f"Line {n}: slots per day must be positive")
        elif facility:
            kind, identifier, field, values = facility.groups()
            identifier = int(identifier)
            expected = "facilities" if kind == "Room" else "requirements"
            count = instance.number_of_rooms if kind == "Room" else instance.number_of_exams
            if field != expected or identifier >= count:
                raise ValueError(f"Line {n}: invalid facility metadata")
            key = (kind, identifier)
            target = instance.room_facilities if kind == "Room" else instance.exam_requirements
            target[identifier] = {value.strip().lower() for value in values.split(',')
                                  if value.strip()}
        else:
            raise ValueError(f"Line {n}: unrecognised input: {line}")
        if key in metadata:
            raise ValueError(f"Line {n}: duplicate metadata")
        metadata.add(key)
    instance.exams_to_students = sorted(enrolments)
    return instance


def read_file(filename):
    return parse_instance(Path(filename).read_text(encoding="utf-8-sig"))


# =============================================================================
# 3. PREPROCESSING - facts shared by both formulations
# =============================================================================
def prepare_instance(instance, extended):
    """Compute exam sizes, conflicts, room choices and necessary resource bounds."""
    exams = range(instance.number_of_exams)
    rooms = range(instance.number_of_rooms)
    slots = range(instance.number_of_slots)
    students = [set() for _ in exams]
    by_student = defaultdict(set)
    for e, student in instance.exams_to_students:
        students[e].add(student)
        by_student[student].add(e)
    # Repeated student exam sets impose identical constraints; build them once.
    groups = sorted({tuple(sorted(group)) for group in by_student.values() if len(group) > 1})
    conflicts = {pair for group in groups for pair in combinations(group, 2)}
    sizes = [len(group) for group in students]
    demand = [(size + 29) // 30 for size in sizes]
    eligible = [{r for r in rooms if instance.room_capacities[r] >= sizes[e]
                 and (not extended or
                      (demand[e] <= 2 and instance.exam_requirements.get(e, set())
                       <= instance.room_facilities.get(r, set())))} for e in exams]
    days = range((len(slots) + instance.slots_per_day - 1) // instance.slots_per_day)
    # Necessary bounds avoid constructing a model for provably impossible inputs.
    # k exams for one student need at least 2*k-1 slots, even across days.
    impossible = (any(not choices for choices in eligible)
                  or len(exams) > len(rooms) * len(slots)
                  or any(2 * len(group) - 1 > len(slots) for group in groups)
                  or (extended and (sum(demand) > 2 * len(slots)
                                    or any(len(group) > MAX_EXAMS_PER_DAY * len(days)
                                           for group in groups))))
    return SimpleNamespace(exams=exams, rooms=rooms, slots=slots, groups=groups,
                           conflicts=conflicts, sizes=sizes, demand=demand,
                           eligible=eligible, days=days, impossible=impossible)


# =============================================================================
# 4. INTEGER FORMULATION - one room and one slot variable per exam
# =============================================================================
def build_integer_model(instance, data, engine, extended):
    room = [z3.Int(f"room_{e}") for e in data.exams]
    slot = [z3.Int(f"slot_{e}") for e in data.exams]

    # M1/M3: choose one valid slot and one capacity-compatible room; E4 if active.
    for e in data.exams:
        engine.add(slot[e] >= 0, slot[e] < len(data.slots),
                   z3.Or([room[e] == r for r in sorted(data.eligible[e])]))

    # M2: exams sharing students already have different slots, so skip those pairs.
    for a, b in combinations(data.exams, 2):
        if (a, b) not in data.conflicts and data.eligible[a] & data.eligible[b]:
            engine.add(z3.Or(slot[a] != slot[b], room[a] != room[b]))

    # M4/M5: a shared student's exams must differ by at least two slots.
    for a, b in sorted(data.conflicts):
        engine.add(z3.Or(slot[a] + 1 < slot[b], slot[b] + 1 < slot[a]))

    at = ([[slot[e] == t for t in data.slots] for e in data.exams]
          if extended and sum(data.demand) > 2 else [])

    def in_day(e, d):
        # Interval bounds avoid integer division inside the solver.
        return z3.And(slot[e] >= d * instance.slots_per_day,
                      slot[e] < (d + 1) * instance.slots_per_day)

    def in_room(e, r):
        return room[e] == r

    def decode(model):
        return [(e, model.eval(room[e]).as_long(), model.eval(slot[e]).as_long())
                for e in data.exams]

    def block(timetable):
        return z3.Or([z3.Or(room[e] != r, slot[e] != t) for e, r, t in timetable])

    return at, in_day, in_room, decode, block


# =============================================================================
# 5. BOOLEAN FORMULATION - exactly one eligible (exam, room, slot) assignment
# =============================================================================
def build_boolean_model(instance, data, engine, extended):
    x = [{r: [z3.Bool(f"x_{e}_{r}_{t}") for t in data.slots]
          for r in sorted(data.eligible[e])} for e in data.exams]

    # M1/M3/E4: exactly one choice; incompatible rooms have no variables.
    for e in data.exams:
        choices = [(v, 1) for row in x[e].values() for v in row]
        engine.add(z3.PbEq(choices, 1) if choices else z3.BoolVal(False))

    # M2: at most one exam uses a particular room/slot.
    for r in data.rooms:
        for t in data.slots:
            occupied = [x[e][r][t] for e in data.exams if r in x[e]]
            if len(occupied) > 1:
                engine.add(z3.AtMost(*occupied, 1))

    at = [[z3.Or([row[t] for row in x[e].values()]) for t in data.slots]
          for e in data.exams]
    # M4/M5: at most one of a student's exams in each two-slot window.
    for group in data.groups:
        for t in range(max(1, len(data.slots) - 1)):
            window = [at[e][u] for e in group
                      for u in range(t, min(t + 2, len(data.slots)))]
            if window:
                engine.add(z3.AtMost(*window, 1))

    def in_day(e, d):
        return z3.Or(at[e][d * instance.slots_per_day:(d + 1) * instance.slots_per_day])

    def in_room(e, r):
        return z3.Or(x[e][r])

    def decode(model):
        return [(e, r, t) for e in data.exams for r, row in x[e].items()
                for t, v in enumerate(row) if z3.is_true(model.eval(v))]

    def block(timetable):
        return z3.Or([z3.Not(x[e][r][t]) for e, r, t in timetable])

    return at, in_day, in_room, decode, block


# =============================================================================
# 6. SOLVING - shared extras, objective, result decoding and alternative solution
# =============================================================================
def _build_model(instance, encoding, extended):
    """Build either formulation; keep the existing four-value interface."""
    if encoding not in ENCODINGS:
        raise ValueError("Encoding must be 'integer' or 'boolean'")
    data = prepare_instance(instance, extended)
    engine = z3.Optimize() if extended else z3.Solver()
    if data.impossible:
        engine.add(z3.BoolVal(False))
        return engine, None, None, z3.IntVal(0)

    builder = build_integer_model if encoding == "integer" else build_boolean_model
    at, in_day, in_room, decode, block = builder(instance, data, engine, extended)
    if extended:
        # E1: students at or below the daily maximum cannot exceed it.
        for group in data.groups:
            if len(group) > MAX_EXAMS_PER_DAY:
                for d in data.days:
                    engine.add(z3.PbLe([(in_day(e, d), 1) for e in group], MAX_EXAMS_PER_DAY))
        # E2: round up separately for each concurrent exam, then sum demand.
        if sum(data.demand) > 2:
            for t in data.slots:
                engine.add(z3.PbLe([(at[e][t], data.demand[e])
                                   for e in data.exams if data.demand[e]], 2))

    # E3: separate unavoidable waste from extra waste to reduce objective terms.
    minimum = [min(instance.room_capacities[r] for r in data.eligible[e]) - data.sizes[e]
               for e in data.exams]
    waste = z3.Sum([z3.IntVal(sum(minimum))] +
                   [z3.If(in_room(e, r), instance.room_capacities[r] - data.sizes[e] - minimum[e], 0)
                    for e in data.exams for r in sorted(data.eligible[e])
                    if instance.room_capacities[r] - data.sizes[e] > minimum[e]])
    if extended:
        engine.minimize(waste)  # E3 is a preference, so it cannot destroy feasibility.
    return engine, decode, block, waste


def solve(instance, encoding="integer", extended=True, second_solution=False):
    """Solve without printing; timings include model building/checking, not I/O."""
    start = perf_counter()
    engine, decode, block, waste = _build_model(instance, encoding, extended)
    status = engine.check()
    result = dict(status=str(status), timetable=[], wasted_seats=None,
                  elapsed_ms=(perf_counter() - start) * 1000)
    if status == z3.unknown:
        result["reason"] = engine.reason_unknown()
    if status != z3.sat:
        return result
    timetable = decode(engine.model())
    result["timetable"] = timetable
    result["wasted_seats"] = validate_timetable(instance, timetable, extended)
    if engine.model().eval(waste).as_long() != result["wasted_seats"]:
        raise AssertionError("Objective differs from independently calculated seat waste")
    if second_solution:
        start = perf_counter()
        other = z3.Solver()
        other.add(*engine.assertions())  # Check ALL feasible timetables, without E3.
        other.add(block(timetable))
        second_status = other.check()
        result.update(second_status=str(second_status), second_timetable=[],
                      second_elapsed_ms=(perf_counter() - start) * 1000)
        if second_status == z3.sat:
            result["second_timetable"] = decode(other.model())
            validate_timetable(instance, result["second_timetable"], extended)
        elif second_status == z3.unknown:
            result["second_reason"] = other.reason_unknown()
    return result


# =============================================================================
# 7. INDEPENDENT VALIDATION - plain Python checks, separate from Z3
# =============================================================================
def validate_timetable(instance, timetable, extended=True):
    """Independently check concrete assignments without using Z3; return waste."""
    def require(condition, message):
        if not condition:
            raise AssertionError(f"Invalid timetable: {message}")

    require(len(timetable) == instance.number_of_exams and
            {e for e, _, _ in timetable} == set(range(instance.number_of_exams)), "M1")
    students = [set() for _ in range(instance.number_of_exams)]
    for e, student in instance.exams_to_students:
        students[e].add(student)
    occupied, student_slots, load = set(), defaultdict(list), Counter()
    waste = 0
    for e, r, t in timetable:
        require(0 <= r < instance.number_of_rooms and 0 <= t < instance.number_of_slots, "M1")
        require((r, t) not in occupied, "M2")
        occupied.add((r, t))
        size = len(students[e])
        require(size <= instance.room_capacities[r], "M3")
        if extended:
            require(instance.exam_requirements.get(e, set()) <=
                    instance.room_facilities.get(r, set()), "E4")
        waste += instance.room_capacities[r] - size
        load[t] += (size + 29) // 30
        for student in students[e]:
            student_slots[student].append(t)
    for times in student_slots.values():
        times.sort()
        require(all(b - a > 1 for a, b in zip(times, times[1:])), "M4/M5")
        if extended:
            require(all(n <= MAX_EXAMS_PER_DAY for n in Counter(t // instance.slots_per_day
                                                              for t in times).values()), "E1")
    if extended:
        require(all(n <= 2 for n in load.values()), "E2")
    return waste


# =============================================================================
# 8. EVALUATION - input discovery, repeated comparisons and constraint tests
# =============================================================================
def natural_key(name):
    """Put sat2 before sat10, independently of ZIP/directory listing order."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", str(name))]


def discover_inputs(directory):
    """Find test samples beside the script or in a 'test instances' subfolder."""
    directory = Path(directory)
    for target in (directory, directory / "test instances"):
        if target.is_dir() and any(p.is_file() and not p.name.startswith(".")
                                   for p in target.glob("*.txt")):
            return target
    raise FileNotFoundError(f"No .txt test samples beside the Python file in {directory}. "
                            "Place the sample .txt files in the same folder as exam_timetabling.py.")


def load_instances(path):
    """Read a folder or ZIP directly. Invalid or empty lecturer data is an error."""
    path = Path(path)
    if path.is_dir():
        raw = [(p.name, p.read_text(encoding="utf-8-sig"))
               for p in path.glob("*.txt") if p.is_file() and not p.name.startswith(".")]
    else:
        with zipfile.ZipFile(path) as archive:
            raw = [(name, archive.read(name).decode("utf-8-sig"))
                   for name in archive.namelist()
                   if name.lower().endswith(".txt") and not Path(name).name.startswith(".")]
    if not raw:
        raise ValueError(f"No .txt instances found in {path}")
    instances = []
    for name, text in sorted(raw, key=lambda item: natural_key(item[0])):
        try:
            instances.append((name, parse_instance(text)))
        except ValueError as error:
            raise ValueError(f"{name}: {error}") from error
    return instances


def expected_status(name):
    label = re.fullmatch(r"(sat|unsat)\d+\.txt", Path(name).name)
    return label[1] if label else None


def repeated_solve(instance, encoding, extended, repeats):
    """Return a representative result, median timing and repeat consistency."""
    runs = [solve(instance, encoding, extended) for _ in range(repeats)]
    result = dict(runs[0])
    result["elapsed_ms"] = median(run["elapsed_ms"] for run in runs)
    signatures = {(run["status"], run["wasted_seats"] if extended else None) for run in runs}
    result["consistent"] = len(signatures) == 1
    if any(run["status"] == "unknown" for run in runs):
        result["status"] = "unknown"
        result["wasted_seats"] = None
        result["reason"] = next(run.get("reason", "inconclusive solver result")
                                for run in runs if run["status"] == "unknown")
    return result


def comparison_state(results, expected, extended):
    if any(result["status"] == "error" for result in results):
        return "FAIL"
    if any(result["status"] == "unknown" for result in results):
        return "INCONCLUSIVE"
    signatures = {(r["status"], r["wasted_seats"] if extended else None) for r in results}
    if len(signatures) != 1 or not all(r["consistent"] for r in results):
        return "FAIL"
    if not extended and expected and results[0]["status"] != expected:
        return "FAIL"
    return "PASS"


def evaluate_profile(instances, extended, counts, repeats=REPEATS):
    """One readable row per instance; printing stays outside all measured work."""
    if extended:
        print("Active: M1-M5 + E1/E2/E4. Objective E3: minimum unused seats.")
        print(f"{'Instance':12} {'Integer':8} {'Boolean':8} {'Cost I/B':11} {'Median ms I/B':19} Check")
    else:
        print("Active: M1-M5. Added rules and optimisation OFF.")
        print(f"{'Instance':12} {'Expected':8} {'Integer':8} {'Boolean':8} {'Median ms I/B':19} Check")
    print("-" * 79)
    outcomes = {}
    for name, instance in instances:
        results = []
        for encoding in ENCODINGS:
            try:
                results.append(repeated_solve(instance, encoding, extended, repeats))
            except (ValueError, AssertionError, z3.Z3Exception) as error:
                results.append(dict(status="error", reason=str(error), elapsed_ms=0,
                                    wasted_seats=None, consistent=False))
        integer, boolean = results
        state = comparison_state(results, expected_status(name), extended)
        counts[state] += 1
        outcomes[name] = integer["status"]
        times = f"{integer['elapsed_ms']:.3f} / {boolean['elapsed_ms']:.3f}"
        if extended:
            costs = " / ".join(str(r["wasted_seats"]) if r["wasted_seats"] is not None else "-"
                               for r in results)
            print(f"{Path(name).name:12} {integer['status']:8} {boolean['status']:8} "
                  f"{costs:11} {times:19} {state}")
        else:
            print(f"{Path(name).name:12} {expected_status(name) or '-':8} "
                  f"{integer['status']:8} {boolean['status']:8} {times:19} {state}")
        for encoding, result in zip(ENCODINGS, results):
            if result["status"] in ("unknown", "error"):
                print(f"  {encoding}: {result.get('reason', 'inconclusive solver result')}")
    print("I/B = Integer / Boolean; timings include preprocessing, model construction and check.")
    print("All sat timetables are independently validated; unsat/unknown validation is N/A.")
    if extended and not any(any(inst.exam_requirements.values()) for _, inst in instances):
        print("E4 NOT EXERCISED here: these inputs declare no special facility requirements.")
    return outcomes


def test_result_state(result, case, extended):
    """Judge one manifest expectation, keeping uncertainty separate from failure."""
    if result["status"] == "unknown" or result.get("second_status") == "unknown":
        return "INCONCLUSIVE"
    mode = "extended" if extended else "base"
    if result["status"] != case[mode]:
        return "FAIL"
    if result["status"] == "sat":
        if extended and result["wasted_seats"] != case["minimum_unused_seats"]:
            return "FAIL"
        if "second_status" in case and result.get("second_status") != case["second_status"]:
            return "FAIL"
    return "PASS"


def run_constraint_tests(path):
    """Check manifest expectations, including deliberate parser errors, without extraction."""
    counts, groups, details = Counter(), defaultdict(Counter), []
    if not path.is_file():
        print(f"SKIPPED: optional {path.name} is not beside the Python file.")
        counts["SKIPPED"] += 1
        return counts
    try:
        with zipfile.ZipFile(path) as archive:
            cases = json.loads(archive.read("expected.json"))["cases"]
            if not isinstance(cases, list) or not cases:
                raise ValueError("Expected a non-empty cases list")
            for case in cases:
                labels = re.findall(r"\b(?:M[1-5]|E[1-4])\b", case.get("focus", ""))
                group = labels[0] if labels else "Input / edges"
                raw = archive.read(case["file"]).decode("utf-8-sig")
                try:
                    instance = parse_instance(raw)
                except ValueError as error:
                    state = "PASS" if case.get("parse_error") else "FAIL"
                    counts[state] += 1
                    groups[group][state] += 1
                    if state == "FAIL":
                        details.append(f"{case['file']}: unexpected input error: {error}")
                    continue
                if case.get("parse_error"):
                    counts["FAIL"] += 1
                    groups[group]["FAIL"] += 1
                    details.append(f"{case['file']}: malformed input was accepted")
                    continue
                for extended, mode in ((False, "base"), (True, "extended")):
                    for encoding in ENCODINGS:
                        state = "PASS"
                        try:
                            result = solve(instance, encoding, extended,
                                           second_solution="second_status" in case)
                            state = test_result_state(result, case, extended)
                        except (ValueError, AssertionError, z3.Z3Exception) as error:
                            state = "FAIL"
                            details.append(f"{case['file']} / {mode} / {encoding}: {error}")
                        if state != "PASS":
                            details.append(f"{case['file']} / {mode} / {encoding}: {state}")
                        counts[state] += 1
                        groups[group][state] += 1
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        counts["FAIL"] += 1
        details.append(f"Cannot complete constraint tests: {error}")
    print("Both methods and both profiles; malformed inputs must be rejected.")
    print(f"{'Test group':16} {'Passed':>7} {'Failed':>7} {'Inconclusive':>13}")
    order = list(CONSTRAINTS) + ["Input / edges"]
    for group in order:
        if group not in groups:
            continue
        totals = groups[group]
        print(f"{group:16} {totals['PASS']:7} {totals['FAIL']:7} {totals['INCONCLUSIVE']:13}")
    for detail in details:
        print(f"  {detail}")
    print(f"Constraint checks: {sum(counts.values())} checks; {counts['PASS']} passed, "
          f"{counts['FAIL']} failed, {counts['INCONCLUSIVE']} inconclusive.")
    return counts


def compare(archive):
    """Compatibility entry point for explicit ZIP/folder comparisons."""
    instances, counts = load_instances(archive), Counter()
    print(f"Python {platform.python_version()} | Z3 {z3.get_version_string()} | median of {REPEATS} runs")
    for extended in (False, True):
        print_section("EXTENDED COMPARISON" if extended else "BASELINE COMPARISON")
        evaluate_profile(instances, extended, counts)
    passed = not (counts["FAIL"] or counts["INCONCLUSIVE"])
    print("PASS: baseline labels, valid timetables and encoding agreement." if passed else
          "FAIL/INCONCLUSIVE: inspect the comparison rows above.")
    return passed


# =============================================================================
# 9. DISPLAY AND STARTUP - the only section that explains progress to the user
# =============================================================================
def print_section(title):
    print("\n" + "=" * 79)
    print(title)
    print("=" * 79)


def print_timetable(instance, timetable):
    sizes = Counter(e for e, student in set(instance.exams_to_students))
    print(f"{'Exam':>4} {'Room':>5} {'Slot':>5} {'Day':>5} {'Students':>9} {'Capacity':>9}")
    for e, r, t in sorted(timetable, key=lambda row: (row[2], row[1], row[0])):
        print(f"{e:4} {r:5} {t:5} {t // instance.slots_per_day + 1:5} "
              f"{sizes[e]:9} {instance.room_capacities[r]:9}")


def print_result(instance, result, extended):
    print(result["status"])
    if result["status"] == "sat":
        print_timetable(instance, result["timetable"])
        print(f"{'Minimum unused seats' if extended else 'Unused seats'}: {result['wasted_seats']}")
        print("Independent validation: PASS (all active hard constraints).")
    else:
        print("Independent timetable validation: N/A (no timetable).")
        if result["status"] == "unknown":
            print(f"Reason: {result.get('reason', 'solver could not decide')}")
    print(f"Build + solve: {result['elapsed_ms']:.3f} ms")
    if "second_status" in result:
        descriptions = {"sat": "another feasible timetable exists (its cost may differ)",
                        "unsat": "unique feasible timetable", "unknown": "INCONCLUSIVE"}
        print(f"Second solution: {descriptions[result['second_status']]} "
              f"({result['second_elapsed_ms']:.3f} ms)")
        if result["second_status"] == "unknown":
            print(f"Reason: {result.get('second_reason', 'solver could not decide')}")


def run_walkthrough(directory=None):
    """No-argument entry point: explain, demonstrate, compare and verify."""
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent
    counts = Counter()
    print_section("1. RUN OVERVIEW")
    try:
        source = discover_inputs(directory)
        instances = load_instances(source)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}")
        return 2
    print("COMP3070 Coursework 1 - Group G")
    print(f"Input source: {source}\nInstances: {len(instances)}")
    print(f"Python {platform.python_version()} | Z3 {z3.get_version_string()}")
    print(f"Methods: Integer and Boolean | Comparison timing: median of {REPEATS} fresh runs")

    print_section("2. METHODS AND CONSTRAINTS")
    print("Integer: one room variable and one slot variable per exam.")
    print("Boolean: exactly one eligible (exam, room, slot) assignment per exam.")
    print("Baseline: M1-M5. Full/extended: M1-M5 + E1/E2/E4, with objective E3.\n")
    for code, description in CONSTRAINTS.items():
        print(f"  {code}: {description}")
    if all((inst.slots_per_day + 1) // 2 <= MAX_EXAMS_PER_DAY for _, inst in instances):
        print("E1 is implied by M4 for these day lengths; the no-consecutive rule already limits the load.")
    print("Missing facility requirements are empty; E4 then has nothing to restrict.")

    name, instance = next(((name, inst) for name, inst in instances
                           if Path(name).name == WORKED_EXAMPLE), instances[0])
    print_section(f"3. WORKED EXAMPLE - {Path(name).name}")
    print(f"Students: {instance.number_of_students} | Exams: {instance.number_of_exams} | "
          f"Slots: {instance.number_of_slots} | Rooms: {instance.number_of_rooms}")
    print(f"Room capacities: {instance.room_capacities} | Slots/day: {instance.slots_per_day}")
    print("Method: INTEGER | Profile: FULL (M1-M5, E1/E2/E4; minimise E3)")
    print("Flow: read -> preprocess -> build model -> solve -> decode -> validate.\n")
    try:
        example = solve(instance, second_solution=True)
        print_result(instance, example, extended=True)
        state = ("INCONCLUSIVE" if example["status"] == "unknown" or
                 example.get("second_status") == "unknown" else "PASS")
        counts[state] += 1
    except (ValueError, AssertionError, z3.Z3Exception) as error:
        counts["FAIL"] += 1
        print(f"FAIL: {error}")
    if not any(instance.exam_requirements.values()):
        print("E4 NOT EXERCISED in this example: no special facilities are required.")

    print_section("4. BASELINE COMPARISON")
    baseline = evaluate_profile(instances, False, counts)
    print_section("5. EXTENDED COMPARISON")
    extended = evaluate_profile(instances, True, counts)
    for name, instance in instances:
        if baseline[name] == "sat" and extended[name] == "unsat":
            data = prepare_instance(instance, True)
            if any(len(group) > MAX_EXAMS_PER_DAY * len(data.days) for group in data.groups):
                print(f"Expected E1 change: {Path(name).name} needs more than {MAX_EXAMS_PER_DAY} exams/day "
                      f"for a student ({instance.slots_per_day} slots/day).")

    print_section("6. CONSTRAINT TESTS")
    counts.update(run_constraint_tests(directory / "constraint_tests.zip"))

    print_section("7. FINAL SUMMARY")
    for state, label in (("PASS", "Passed"), ("FAIL", "Failed"),
                         ("INCONCLUSIVE", "Inconclusive"), ("SKIPPED", "Skipped")):
        print(f"{label:13}: {counts[state]}")
    print("Counts cover the example, one check per instance/profile, and manifest expectations.")
    if counts["FAIL"] or counts["INCONCLUSIVE"]:
        print("Overall: FAIL / INCONCLUSIVE - review the sections above.")
        return 1
    if counts["SKIPPED"]:
        print("Overall: completed with SKIPPED checks; available checks passed.")
    else:
        print("Overall: PASS - all checks completed successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", type=Path, help="optional instance; no arguments runs the walkthrough")
    parser.add_argument("--encoding", choices=ENCODINGS, default="integer")
    parser.add_argument("--base", action="store_true", help="M1-M5 only")
    parser.add_argument("--compare", action="store_true", help="compare both methods/profiles on a ZIP or folder")
    parser.add_argument("--second-solution", action="store_true", help="check for another feasible timetable")
    args = parser.parse_args()
    if args.path is None:
        if args.base or args.encoding != "integer" or args.compare or args.second_solution:
            parser.error("Supply an instance with options, or press Run with no arguments for all sections")
        return run_walkthrough()
    try:
        if args.compare:
            if args.base or args.encoding != "integer" or args.second_solution:
                parser.error("--compare runs both encodings and modes; use it on its own")
            return 0 if compare(args.path) else 1
        instance = read_file(args.path)
        result = solve(instance, args.encoding, not args.base, args.second_solution)
        print_result(instance, result, not args.base)
        return 1 if result["status"] == "unknown" or result.get("second_status") == "unknown" else 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
