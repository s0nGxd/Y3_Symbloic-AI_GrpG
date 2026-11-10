# Run, understand and test the exam timetabling solver

Put the test sample `.txt` files in the same folder as `exam_timetabling.py`,
open the Python file in your editor and press **Run**. No arguments or PowerShell
variables are needed for the normal run.
It explains the methods and constraints, works through one timetable, compares
both methods on the lecturer instances, and runs the available constraint tests.

The coursework program is one Python file. This guide and the test data are
supporting documentation/input data, not additional Python modules.

## 1. One-time setup and input placement

Python 3 and Z3 must be installed. If the program asks you to install Z3, run
this once in the terminal belonging to your Python environment:

```text
python -m pip install z3-solver
```

Then press Run on `exam_timetabling.py` again. If your computer uses `py` rather
than `python`, use `py -m pip install z3-solver`. See the
[official Z3 repository](https://github.com/Z3Prover/z3#python).

Place the lecturer's `.txt` instances directly beside the Python file. Use this
flat layout when submitting or copying the project to another computer:

```text
submission/
    exam_timetabling.py
    sat1.txt
    sat2.txt
    ...
    sat10.txt
    unsat1.txt
    ...
    unsat10.txt
    constraint_tests.zip    (optional extra verification data)
```

The automatic run reads only the `.txt` files directly in the Python file's own
folder. It does not enter subfolders, search parent folders or other locations,
or fall back to the lecturer's ZIP archive. This is independent of the terminal's
working directory and does not depend on anyone's personal computer paths.
Every `.txt` file in that folder must contain a valid problem instance. Missing,
empty or invalid sample inputs produce a clear error, not a successful empty run.

Keep `constraint_tests.zip` beside the script to include the targeted tests.
If it is missing, that section is marked **SKIPPED**. Input data is still
required; running one Python file does not mean embedding the inputs in it.

## 2. Read the seven output sections

```text
1. RUN OVERVIEW
2. METHODS AND CONSTRAINTS
3. WORKED EXAMPLE
4. BASELINE COMPARISON
5. EXTENDED COMPARISON
6. CONSTRAINT TESTS
7. FINAL SUMMARY
```

Each section has a visible header and spacing. Repeated trials are condensed
into summary rows instead of printing every trial or timetable.

| Section | What to look for |
|---|---|
| Run overview | Input source, instance count, Python/Z3 versions and repetitions |
| Methods and constraints | Integer/Boolean methods and active rules for each profile |
| Worked example | Input summary, integer/full-model result, timetable, validation, cost and time |
| Baseline comparison | Both methods under M1-M5, checked against the original lecturer labels |
| Extended comparison | Both methods with all agreed rules, optimal costs and agreement checks |
| Constraint tests | Grouped checks against expected outcomes, including malformed input |
| Final summary | Passed, failed, inconclusive and skipped checks |

The example is `sat6.txt` when available; otherwise it is the first naturally
sorted input. For the supplied sat6, expect `sat`, three exam assignments and
**6 minimum unused seats**. Exact assignments may vary when several optima
exist. A short second-solution result follows the timetable.

Exam, room and slot identifiers are zero-based; printed days are one-based:

```text
Slots 0,1,2,3,4 -> Day 1
Slots 5,6,7,8,9 -> Day 2
```

Slots 4 and 5 remain consecutive under M4 even across days. The second-solution
query asks for another feasible timetable, which may have a worse E3 cost.

## 3. Profiles, expected results and timing

| Profile | Hard constraints | Objective |
|---|---|---|
| Baseline | M1-M5 | Find any feasible timetable |
| Extended/full | M1-M5, E1, E2, E4 | E3: minimise total unused seats |

E3 means efficient single-room use; the main model does not split an exam.
E1, E2 and E4 are the three added hard constraints.

E1 now permits **at most three exams per student per day**. Its single setting
is `MAX_EXAMS_PER_DAY = 3` near the top of the Python file. The preprocessing
bound, both formulations, independent validator and output use this setting.
Changing the daily limit later requires editing that setting and updating any
test cases whose expected answers depend on the limit.

With the default five-slot day, M4 already allows at most three exams, at slots
0, 2 and 4. E1 is therefore redundant under this default: it does not further
restrict M1-M5. It becomes independently restrictive with seven or more slots
per day, where four nonconsecutive exams could otherwise fit. Document this
relationship in the report; do not claim three independent added restrictions
for the default five-slot-day model.

The lecturer's filenames describe the baseline problem. Under five-slot days:

| Lecturer files | Baseline | Extended | Extended minimum unused seats |
|---|---|---|---|
| sat1 | sat | sat | 0 |
| sat2 | sat | sat | 1 |
| sat3 | sat | sat | 1 |
| sat4 | sat | sat | 1 |
| sat5 | sat | sat | 6 |
| sat6 | sat | sat | 6 |
| sat7 | sat | sat | 25 |
| sat8 | sat | sat | 6 |
| sat9 | sat | sat | 42 |
| sat10 | sat | sat | 24 |
| unsat1 through unsat10 | unsat | unsat | - |

Sat7, sat8 and sat9 are satisfiable again under the new three-exam daily limit.
Sat7/sat8 can accommodate the three exams a student needs in their five-slot
day. Under E1, two days permit at most six exams, so the students needing five
exams in sat9 no longer exceed its bound. All M1-M5 rules still apply.

Comparisons use five fresh runs per instance/method/profile and print medians.
With 20 inputs, this is 20 x 2 methods x 2 profiles x 5 runs = **400 solves**.
The example and targeted tests are additional checks.

`Build + solve` includes preprocessing, constraint construction and Z3 checking.
It excludes input reading, decoding, independent validation and printing. The
second-solution query has a separate timing. Headers do not enter the measured
solving time.

Baseline costs may differ because optimisation is disabled. Extended timetables
may differ while attaining the same minimum cost. Compare status and optimal
cost agreement; identical printed assignments are unnecessary.

| Reported state | Meaning |
|---|---|
| sat | A valid timetable exists; extended mode also optimises unused seats |
| unsat | No timetable satisfies the active hard rules |
| unknown / inconclusive | The solver has not established either conclusion |
| Validation not applicable | No timetable was returned to validate |
| E4 not exercised | No exam declares a special facility requirement |
| SKIPPED | An optional test resource is unavailable |

Malformed input is an input error, not mathematical unsatisfiability. A skipped
or inconclusive check must not be read as passed; the final summary separates
these outcomes.

## 4. Inputs and variables

Enrolment lines follow the template order **EXAM STUDENT**: `0 2` means student
2 takes exam 0. Supply the four count headers, then capacities in room order,
then enrolments and optional metadata.

| Quantity | Effect |
|---|---|
| Number of students | Valid IDs `0..N-1`; declaring students does not enrol them |
| Number of exams | Exams needing one assignment each, including empty exams |
| Number of slots | Ordered slots `0..T-1`; affects gaps, days and resources |
| Number of rooms | Rooms `0..R-1`; each needs a capacity line |
| Room capacities | Maximum exam enrolment; equality is allowed |
| Exam/student pairs | Define exam sizes and shared-student conflicts |
| Slots per day | Optional positive integer; default 5 |
| Maximum exams per student/day | `MAX_EXAMS_PER_DAY = 3` in the Python settings |
| Room facilities | Optional comma-separated set per room |
| Exam requirements | Optional comma-separated set per exam |
| Invigilator demand | Derived as `(distinct_exam_size + 29) // 30` |
| Room/slot decisions | Chosen by Z3 |

To grow an exam, add distinct enrolled students and keep IDs inside the declared
range. Increasing only the student header or repeating a pair does not change
exam size. Blank lines are accepted and duplicate pairs count once.

For example:

```text
Number of students: 2
Number of exams: 2
Number of slots: 3
Number of rooms: 2
Room 0 capacity: 1
Room 1 capacity: 2
0 0
1 0
1 1
Slots per day: 5
Room 0 facilities: computers
Room 1 facilities: lab, computers
Exam 0 requirements: computers
Exam 1 requirements: lab
```

This is satisfiable with zero unused seats. The shared student needs slots 0
and 2, exam 1 fits room 1, and facilities are compatible. Facility names are
case-insensitive sets. Missing sets default to empty, so the lecturer's original
files do not exercise special facility requirements.

E2 fixes one invigilator per 30 students and two available per slot. These are
not optional file headers. Staffing is interchangeable rather than named staff
rotas. An empty exam needs zero invigilators under the ceiling rule but still
occupies a room/slot.

## 5. Follow the source code

| Numbered source section | Responsibility |
|---|---|
| 1. Settings | Defaults and constraint descriptions |
| 2. Input | Instance data, parsing and file reading |
| 3. Preprocessing | Sizes, conflicts, eligible rooms and necessary bounds |
| 4. Integer model | Integer room and slot decisions |
| 5. Boolean model | Boolean assignment decisions |
| 6. Solving | Build/check/decode, cost and second-solution query |
| 7. Independent validation | Plain Python timetable checks |
| 8. Evaluation | Repeated comparisons and manifest checks |
| 9. Display and startup | Headers, summaries and automatic walkthrough |

The template's base `Instance` fields and input layout are retained. The parser,
models, optimisation, checker and presentation are additions. `parse_instance`,
`read_file`, `solve` and `validate_timetable` remain usable without launching
the walkthrough. Importing is silent; running the file starts the walkthrough.

```text
Read -> validate input -> derive data -> build selected model
     -> Z3 check/optimise -> decode -> independent validation -> display
```

Necessary bounds can establish impossibility early, but never establish
feasibility. For example, a student taking k exams needs at least `2*k-1` slots.
An early rejection is not a smallest-conflicting-rule explanation.

### Integer formulation

Let E be exams, R rooms, T the slot count, S_e students in exam e, n_e = |S_e|,
c_r room capacity, D slots/day, K = MAX_EXAMS_PER_DAY (currently 3), and
v_e = ceil(n_e / 30). F_e contains rooms
meeting capacity and, in extended mode, required facilities. Each exam has
integer decisions r_e (room) and t_e (slot).

| Rule | Mathematical requirement |
|---|---|
| M1 | r_e belongs to F_e and 0 <= t_e < T |
| M2 | For distinct e,f: t_e != t_f OR r_e != r_f |
| M3 | Every r in F_e has c_r >= n_e |
| M4/M5 | If S_e intersects S_f: t_e+1 < t_f OR t_f+1 < t_e |
| E1 | Per student/day d: count exams with dD <= t_e < (d+1)D; count <= K |
| E2 | Per slot t: sum v_e over exams with t_e=t is <= 2 |
| E3 | Minimise sum over exams of c_(r_e) - n_e |
| E4 | Required(e) is a subset of Facilities(r_e) |

The gap rule excludes simultaneous and consecutive exams. M2 can be omitted
for conflicting exams, whose slots already differ, and for exams with disjoint
eligible room sets.

### Boolean alternative

x[e,r,t] is true when exam e uses eligible room r in slot t. There are at most
E*R*T Boolean decisions; the integer formulation has 2*E primary decisions.

- M1: select exactly one assignment per exam.
- M2: at most one exam uses each room/slot.
- M3/E4: incompatible rooms have no assignment variables.
- M4/M5: at most one of a student's exams lies in each adjacent two-slot window;
  with a one-slot horizon, enforce same-slot exclusivity.
- E1: at most K of a student's assignments occur per day (currently K = 3).
- E2: sum v_e*x[e,r,t] over exams/rooms is at most 2 per slot.
- E3: minimise sum `(c_r-n_e)*x[e,r,t]` over assignments.

`PbEq`, `PbLe` and `AtMost` express exact weighted counts, weighted upper bounds
and cardinality limits. See [Z3 constraints](https://microsoft.github.io/z3guide/docs/logic/propositional-logic/).
Baseline uses `Solver`; extended mode uses
[`Optimize.minimize`](https://z3prover.github.io/api/html/classz3py_1_1_optimize.html).

Each integer timetable determines exactly one true Boolean assignment per
exam, and each exactly-one Boolean selection determines an integer timetable.
Corresponding constraints and costs match, so the feasible set and minimum
cost are equivalent.

The optimisations preserve those semantics: deduplicated enrolments/conflicts,
filtered rooms, necessary bounds, omitted redundant constraints, interval day
comparisons, and a cost expressed as unavoidable minimum waste plus nonnegative
extra waste. This simplifies the objective without greedily fixing rooms.

## 6. Test every constraint automatically

Section 6 of a normal run reads `constraint_tests.zip` and its `expected.json`.
There are 38 valid input instances and nine deliberately malformed inputs.
Each valid case is checked with both methods/profiles, including known minimum
costs and selected uniqueness results. No separate command or copied code is
needed.

The supplied manifest accounts for **161 checks**: 38 x 2 profiles x 2 methods,
plus nine parser-rejection checks. Expected rejection of malformed input passes
the test; accepting it fails.

| Rule/feature | Cases in the ZIP | Expected observation |
|---|---|---|
| M1 | 01-04 | Exactly one assignment; missing resource unsat; empty instance sat |
| M2 | 07-08 | One room/slot cannot host two exams; two rooms can |
| M3 | 05-06 | Exact capacity sat; no individually sufficient room unsat |
| M4 | 10-12 | A gap is needed, including conflicts from different students |
| M5 | 09 | Shared-student exams cannot share the only slot |
| E1 | 13, 14, 15, 15b | Three exams in one day pass; four in a seven-slot day fail; another/partial day can restore sat |
| E2 | 16-19 | Ceiling boundaries and separate concurrent exam demands |
| E3 | 20-21, 26 | Known minimum costs, including competing room requirements |
| E4 | 22-26, 28 | All required features must be in the assigned room |
| Input | 27, 29, invalid/ | Duplicates, whitespace/BOM and malformed input |
| Uniqueness | 01, 04, 20 | Unique minimal/empty timetable or another feasible one |

| Enrolment | Invigilators required |
|---|---|
| 0 | 0 |
| 1-30 | 1 |
| 31-60 | 2 |
| 61-90 | 3, exceeding the two available |

Three simultaneous one-student exams need three invigilators despite having
only three students altogether. Apply the ceiling to each exam, then sum.

Every returned timetable is checked using ordinary Python sets, counts and
sorted student slots. That checker establishes feasibility and recalculates
cost. Unsatisfiability and global optimality need the solver's conclusions or
small-case exhaustive reference checks.

Small generated problems can also be compared with exhaustive enumeration,
including feasibility and minimum unused-seat totals. Such checks supplement
the manifest cases. A finite test suite does not prove every possible unseen
input correct, and expected outcomes must match the configured daily limit.

For experiments, change one input property at a time and predict the result.
Manually audit each exam's assignment, room/slot uniqueness, room size, student
gaps/day counts, staffing per slot, facilities and unused-seat sum. Known small
optima give stronger E3 evidence than a room choice that merely looks sensible.

## 7. Optional compatibility interface

The old command-line interface remains available for scripts or individual
instances. It is unnecessary for normal automatic operation.

| Optional invocation/flag | Behaviour |
|---|---|
| No arguments | Complete organised walkthrough |
| Explicit instance path | Integer/full model on that file |
| `--encoding boolean` | Boolean model for an explicit instance |
| `--base` | M1-M5 only for an explicit instance |
| `--second-solution` | Check another feasible timetable for an explicit instance |
| `--compare` | Both methods/profiles on an explicitly supplied ZIP or folder |

`solve(instance, encoding="integer", extended=True, second_solution=False)`
returns result data without printing. `validate_timetable` returns concrete
unused-seat cost or rejects an invalid assignment. Existing API-based tests
can continue using them.

## 8. Use the evidence in the report

The brief allocates 30% to correctness/formulations, 20% to code quality and
explanations, and 50% to the report. Its 90-100 band expects exceptional work
throughout, research depth and a report approaching publishable quality.
Passing tests supports the submission; it does not certify that mark.

Prepare this evidence:

1. Define notation and give both full formulations, explaining correctness,
   equivalence and assumptions.
2. Record expected/actual lecturer outcomes and minimum costs. Explain why
   sat7/8/9 are satisfiable with the three-exam limit, and why E1 is redundant
   with M4 under five-slot days. Include boundary tests with longer days where
   E1 can independently exclude a timetable.
3. Compare matching constraints/objectives on the same machine and Z3 version.
   Record median times and state what those timings include.
4. Study controlled larger inputs, varying exams, slots, rooms, enrolment density
   and resource tightness. Separate preprocessing rejections from model search.
5. Discuss fixed staffing, the day assumption, no splitting, missing facility
   data in lecturer files and potentially long runs on harder inputs.
6. Connect findings to research and reference the template and Z3 documentation.
   Describe the group's contribution accurately.

The numbered output makes results easier to inspect. The report must still
interpret those results and explain the mathematics.

Coursework source: `COMP3070_Coursework1_(26-27)_revised_3Oct26.pdf`, supplied by
the module convenor.
