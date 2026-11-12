# COMP3070 Coursework 1: Z3 Exam Timetabling Solver (Group G)

`coursework01.py` is the whole solver: one Python 3 file that uses the Z3 SMT solver.

## Setup

```
pip install z3-solver
python coursework01.py --selftest      # should end with ALL PASSED
```

Keep `coursework01.py` next to the `test instances` folder (sat1–10, unsat1–10). On a Mac, use `python3` if `python` is not found.

## Run commands

| Command | What it does |
|---|---|
| `python coursework01.py "test instances/sat1.txt"` | Solve one file: prints `sat` + timetable + time, or `unsat` + time |
| `python coursework01.py` | Solve every file in `test instances` |
| `python coursework01.py --quiet` | One summary line per file (answer, time, model size, verdict) |
| `python coursework01.py --e1 --e2 --e4` | Switch on extra rules (any combination; off by default) |
| `python coursework01.py -f boolean ...` | Choose a formulation: `integer` (default), `symmetry`, `boolean`, `optimize`, `reference` |
| `python coursework01.py --solutions 10 "test instances/sat2.txt"` | Find up to 10 different timetables |
| `python coursework01.py --explain` | For each unsat file, show the rules that clash |
| `python coursework01.py --selftest` | 12 automatic checks against brute force |
| `python coursework01.py --tests` | 603 targeted checks from `constraint_tests.zip` |
| `python coursework01.py --experiment` | Every experiment for the report, saved in `results/*.csv` |

## Rules

| Rule | Meaning |
|---|---|
| M1 | Each exam in exactly one slot and one room |
| M2 | No two exams in the same room at the same time |
| M3 | The room is big enough |
| M4 | No consecutive exams for a student |
| M5 | No simultaneous exams for a student |
| E1 (`--e1`) | At most 2 exams per student per day (5 slots a day, or `Slots per day: N` in the file) |
| E2 (`--e2`) | 1 invigilator per 30 students, rounded up; 2 available per slot |
| E3 | Fewest empty seats: the goal of `-f optimize` (no room splitting) |
| E4 (`--e4`) | The room must have every facility the exam needs (`Room 1 facilities: lab`, `Exam 0 requirements: lab`); files without these lines use "exam 0 needs the lab, the largest room" |

The official sat/unsat answer uses M1–M5 only.

## Formulations

- **integer** (main): `slot_e` and `room_e` per exam.
- **symmetry**: integer model plus symmetry breaking for identical rooms.
- **boolean**: one true/false variable per (exam, slot, room), counting constraints.
- **optimize**: earliest last slot, then fewest empty seats; each optimum is re-proved with a plain Solver.
- **reference**: brute force, not Z3; ground truth for testing.

## Files

```
coursework01.py         the solver (submit)
constraint_tests.zip    targeted test cases used by --tests
test instances/         the 20 sample files
results/                created by --experiment
README.md               this guide
```

## Known bugs and limitations

- With Z3 5.3.3, minimising an objective variable with only lower bounds made `Optimize` return invalid timetables; the checker caught it, and adding an upper bound fixed it.
- The integer model slows to seconds on large tight instances (60–80 exams); the Boolean model and symmetry breaking are faster there.
- Optimisation reaches the 10 s limit from 15 exams (loose) and 30 exams (tight).
- Brute force is exponential, so it only works on small files.
