# COMP3070 Coursework 1: Examination Timetabling

**Group G | Python and Z3 | One Python program file**

Open [exam_timetabling.py](exam_timetabling.py) in your Python editor and press
**Run**. No arguments, PowerShell variables or manual ZIP extraction are needed
for the normal run. The current repository already supplies the samples in its
local `test instances` folder.
It explains the methods and constraints, works through one timetable, compares
both methods on the lecturer instances, and runs the available constraint tests.

The coursework program is one Python file. This guide and the test data are
supporting documentation/input data, not additional Python modules.

For Moodle, the minimal submission is **two files**:

- [exam_timetabling.py](submission/exam_timetabling.py), the complete solver.
- [Symbolic_AI_CW1_Report.pdf](submission/Symbolic_AI_CW1_Report.pdf), the report.

The [editable Word report](report/Symbolic_AI_CW1_Report.docx) is retained for
editing and is not an additional required upload. Separate experiment scripts,
CSV/JSON logs, a tests folder and Python cache files are not required by the
brief or the solver. Development experiment materials are archived outside this
repository; their methods and findings remain explained in the report.

This guide describes the current policy: **E1 permits three exams per student
per day**, E2 provides **two invigilators per slot**, and E3 minimises unused
seats while preserving **one room per exam**.

## Contents

1. [Setup and input placement](#1-one-time-setup-and-input-placement)
2. [The seven output sections](#2-read-the-seven-output-sections)
3. [Profiles, expected results and timing](#3-profiles-expected-results-and-timing)
4. [Inputs and variables](#4-inputs-and-variables)
5. [Source structure and mathematical formulations](#5-follow-the-source-code)
6. [Automatic tests and special scenarios](#6-test-every-constraint-automatically)
7. [Optional command-line and Python interfaces](#7-optional-compatibility-interface)
8. [Report preparation](#8-use-the-evidence-in-the-report)
9. [Limitations and future work](#9-limitations-and-future-work)
10. [Sources and attribution](#10-sources-and-attribution)

## 1. One-time setup and input placement

Python 3 and Z3 must be installed. If the program asks you to install Z3, run
this once in the terminal belonging to your Python environment:

```text
python -m pip install z3-solver
```

Then press Run on `exam_timetabling.py` again. If your computer uses `py` rather
than `python`, use `py -m pip install z3-solver`. See the
[official Z3 repository](https://github.com/Z3Prover/z3#python).

The current repository layout is:

```text
project/
    exam_timetabling.py
    README.md
    constraint_tests.zip    Optional local verification data
    test instances/
        sat1.txt ... sat10.txt
        unsat1.txt ... unsat10.txt
    submission/
        exam_timetabling.py
        Symbolic_AI_CW1_Report.pdf
    report/
        Symbolic_AI_CW1_Report.docx
```

Use the root copy for the normal editor **Run** walkthrough, which has the local
sample data beside it. The `submission` folder contains only the two upload
files; its solver copy does not contain or embed the input data. From the
project folder, it can still solve an external input directly:

```text
python submission/exam_timetabling.py "test instances/sat6.txt"
```

For an unseen instance, replace that path with the supplied `.txt` file. No
other Python module, CSV file or test script is needed. Z3 must still be
installed. Running the submission copy with **no arguments** requires placing
valid sample `.txt` files beside that copy or in its own `test instances`
subfolder; it does not search the parent project folder.

For no-argument operation, the implementation checks these two script-relative
locations in order:

1. Non-hidden `.txt` files directly beside `exam_timetabling.py`.
2. If none are found there, non-hidden `.txt` files in its local
   `test instances` subfolder.

The first location containing `.txt` files is selected; the locations are not
combined. This is independent of the terminal's working directory. There is
no recursive, parent-folder, Downloads or PC-wide search, no personal absolute
path, and no automatic fallback to the lecturer's ZIP archive.

A flat layout is also supported for a local working copy. These input files
support execution and verification; they are separate from the minimal Moodle
uploads:

```text
working-copy/
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

Every `.txt` file in the selected location must contain a problem instance.
A text log beside the script would also be read as input, so save output logs
with a different extension. Missing, empty or invalid samples produce a clear
error, not a successful empty run. The program does not silently skip a malformed
selected input and search another location.

Keep `constraint_tests.zip` beside the script to include the targeted tests.
If it is missing, that section is marked **SKIPPED**. Input data is still
required; running one Python file does not mean embedding the inputs in it.

Keep the supplementary ZIP intact. Extracting its deliberately malformed
examples into the ordinary input location would make them input errors instead
of expected parser-rejection tests.

The current walkthrough was verified with **Python 3.12.9 and Z3 5.3.3**. Record
the versions printed by your own run when collecting experimental results.

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

The current output separates timing rather than treating all work as the
solver check:

| Timing | Includes |
|---|---|
| `Model construction` / `build_ms` | Preprocessing and constraint/objective construction |
| `Z3 check only` / `check_ms` | The call to `engine.check()` only, including optimisation in full mode |
| `Build + solve` / `Build+check` / `elapsed_ms` | Construction plus checking |
| Second-solution timing | The separate blocked-assignment feasibility query |
| Optimality-verification timing | The optional fresh strict-better query |

Input reading, decoding, independent timetable validation and printing are
outside the primary build/check total. Headers do not enter measured solving
time. The comparison tables show paired **Build+check ms I/B** and **Check ms
I/B** columns. Each reported timing is its own median over the repeated calls;
adding separately computed medians need not reproduce the total's median.

Baseline costs may differ because optimisation is disabled. Extended timetables
may differ while attaining the same minimum cost. Compare status and optimal
cost agreement; identical printed assignments are unnecessary.

### What PASS and I/B mean

`I/B` means **Integer / Boolean**. Costs are unused seats, and both timing
columns are milliseconds. A dash indicates that no timetable/cost was returned.

**PASS does not mean sat.** A comparison row passes when repeated results are
consistent and both encodings agree on status; full-model rows also compare
minimum costs. Baseline additionally checks recognised `satN.txt` and
`unsatN.txt` filename labels. Other filenames have no inferred gold label.
Filenames affect evaluation expectations, not the solver's mathematical answer.

Every returned sat timetable is independently checked in Python. No timetable
exists to validate for unsat/unknown, so validation is N/A. Agreement between
two models is evidence, not an independent proof of unsatisfiability or
optimality, particularly because they share preprocessing.

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

### Solves versus checks

With 20 lecturer samples and the complete supplementary ZIP, the final summary
should report **202 passed, 0 failed, 0 inconclusive and 0 skipped**:

```text
1 worked-example result
20 baseline comparison checks
20 extended comparison checks
161 supplementary expectations
------------------------------
202 checks
```

These are checks, not 202 unique input instances or 202 solver calls. The 400
timed comparison calls are separate from the worked example and supplementary
calls. A test expecting unsat or parser rejection can pass correctly.

A portable verification run using a copied solver and input data, launched from an
unrelated working directory, confirmed this total and the result/cost table.
Timing values are machine- and run-dependent; there is no universal speed bound
or guaranteed fastest formulation. Separate inputs rejected by shared
preprocessing from those requiring model search in performance analysis.

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
case-insensitive sets. All requested features must be provided by the same
assigned room. No room is automatically a lab because of its capacity or ID.
Missing sets default to empty, so the lecturer's original files do not exercise
special facility requirements.

The four count headers come first, followed by capacities in room order.
Enrolments and optional metadata may then be interleaved. Header labels are
case-sensitive; follow the spelling shown. UTF-8 BOMs and leading/trailing line
whitespace are accepted. Duplicate metadata entries, invalid IDs, negative
counts and unknown lines are rejected. Slots per day must be positive.

An empty exam still occupies a room/slot. Zero exams form a valid empty timetable;
a nonempty exam set with no rooms or slots is infeasible. Malformed data is an
input error, not a mathematical unsatisfiability result.

### E2: required staff and available staff are different quantities

Required staff is `ceil(actual exam enrolment / 30)`, implemented as
`(size + 29) // 30`. It is not calculated from room capacity or capped at two.
The two available invigilators form a pool **across all rooms in each slot**.
Round each exam's demand separately, then sum concurrent demands.

| Situation | Required invigilators | Staffing result |
|---|---:|---|
| One 30-student exam | 1 | Permitted |
| One 31-student exam | 2 | Permitted |
| One 60-student exam | 2 | Permitted |
| One 90-student exam | 3 | Impossible with only two available |
| Two simultaneous 30-student exams | 1 + 1 = 2 | Permitted |
| Two simultaneous 31-student exams | 2 + 2 = 4 | Not permitted |
| Three simultaneous one-student exams | 1 + 1 + 1 = 3 | Not permitted |

Moving a 90-student exam to another slot does not help when every slot has only
two staff. Feasibility would require different staffing availability. E2's
ratio and availability are fixed in the implementation, not optional input
headers. Staff are interchangeable rather than named staff rotas. An empty
exam requires zero invigilators under the ceiling rule.

## 5. Follow the source code

| Numbered source section | Responsibility |
|---|---|
| 1. Settings | Defaults and constraint descriptions |
| 2. Input | Instance data, parsing and file reading |
| 3. Preprocessing | Sizes, conflicts, eligible rooms and necessary bounds |
| 4. Integer model | Integer room and slot decisions |
| 5. Boolean model | Boolean assignment decisions |
| 6. Solving | Separate build/check timing, cost, optional optimality verification and second-solution query |
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

Let E, S and R be the sets of exams, students and rooms. Let H be the slot count
and T the ordered slot IDs `0..H-1`. Define:

| Symbol | Meaning |
|---|---|
| S_e | Set of distinct students in exam e |
| E_s | Set of exams taken by student s |
| n_e | Exam enrolment, the cardinality of S_e |
| c_r | Capacity of room r |
| D | Slots per day from the input, default 5 |
| K | `MAX_EXAMS_PER_DAY`, currently 3 |
| v_e | Required invigilators, `ceil(n_e / 30)` |
| F_e | Rooms meeting capacity and, in full mode, required facilities |
| d(t) | Internal zero-based day index `floor(t / D)` |
| [P] | Indicator: 1 when proposition P holds, otherwise 0 |

Each exam has integer decisions r_e (room) and t_e (slot).
In the daily constraints, d ranges from zero to `ceil(H/D)-1`.

| Rule | Mathematical requirement |
|---|---|
| M1 | r_e belongs to F_e and 0 <= t_e < H |
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

x[e,r,t] is true when exam e uses eligible room r in slot t. Exactly one
eligible assignment is selected for each exam; the rules become counts of
selected assignments.

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

### Complete Boolean constraints

The following describes counts mathematically; `[x]` is a zero/one indicator,
not a suggestion to multiply raw Python Boolean objects. Unless stated
otherwise, assignment sums range over declared eligible triples: e in E,
r in F_e and t in T. Undeclared/ineligible assignments are treated as false
(indicator zero), so room-wise sums also have a precise meaning.

```text
M1: for each e:
    sum over r in F_e, t in T of [x[e,r,t]] = 1.
M2: for each r,t:
    sum over e of [x[e,r,t]] <= 1.
M3/E4: omit assignment variables for rooms outside F_e.
M4/M5: for each student s and adjacent two-slot window W_t:
    sum over e in E_s, r in F_e, u in W_t of [x[e,r,u]] <= 1.
E1: for each s,d:
    sum over e in E_s, r in F_e, t with d(t)=d of [x[e,r,t]] <= K.
E2: for each t:
    sum over e, r in F_e of v_e * [x[e,r,t]] <= 2.
E3: minimise sum over e,r,t of (c_r - n_e) * [x[e,r,t]].
```

Here `W_t = {t,t+1}` for `0 <= t < H-1`. A one-slot horizon uses `{0}` for
same-slot exclusivity. Any exam with no possible assignments makes M1
false. Partial final days are handled by slot bounds. Student groups with at
most K exams need no E1 constraint because they cannot exceed K in any day.

There are up to `|E| * |R| * H` primary Boolean decisions, reduced by room
filtering, versus `2 * |E|` primary integer decisions. Nominal variable counts
alone do not predict performance: constraint structure and the solver's internal
encoding also matter. The two formulations are encodings of the same scheduling
problem, not separate claims of a newly invented search algorithm.

### Why preprocessing and objective reductions are safe

The shared preprocessing rejects a problem only when a necessary condition
fails. In particular:

- Each exam must have at least one usable room. An exam needing more than two
  invigilators cannot be placed in any full-model slot under the fixed pool.
- Each exam occupies one room/slot position, so `|E| <= |R| * H` is necessary.
- A student taking k exams requires k exam slots and at least k-1 intervening
  gaps, hence `H >= 2*k-1`.
- Total invigilator demand cannot exceed `2*H` in full mode.
- A student's exam count cannot exceed `K*ceil(H/D)` under E1. This is a safe
  necessary bound even when the last day is only partial.

Passing these bounds does not establish feasibility; Z3 still checks all
remaining interactions. Deduplicating identical student groups removes repeated
constraints, not students from exam enrolment counts.

For the objective, let `m_e = min(c_r - n_e)` over exam e's eligible rooms. Then:

```text
total waste = sum_e m_e
            + sum over e,r of [exam e chooses room r] * (c_r - n_e - m_e).
```

Exactly one selected room makes this algebraically equal to the original cost.
All extra coefficients are non-negative, and a minimum-cost room contributes
only to the constant part. Room choices remain free to satisfy competition,
student and facility constraints. The Boolean model uses its equivalent
room-selection expression.

### Independent validation and its limits

The validator uses ordinary Python sets, counts and sorted slots to check the
concrete assignment. It verifies every active hard constraint and recalculates
unused seats. `solve` compares that cost against the model expression before
returning a sat result. A failure raises an error instead of presenting an
invalid timetable as valid.

This checks feasibility and cost arithmetic. It does not alone establish that
no solution exists or that a feasible cost is globally minimal. Those conclusions
come from the model/solver, supported by explicit expected results and small
independent exhaustive-reference comparisons.

### Optional strict-better optimality verification

The current implementation can additionally verify a full-model result using
`verify_optimality=True` or the optional `--verify-optimality` argument. After
validating a returned timetable with cost W*, it creates a fresh plain `Solver`,
copies the hard assertions and adds:

```text
W < W*
```

The optimisation command itself is not copied. The question is whether any
strictly lower-cost feasible timetable exists under the same encoded rules.

| Verification result | Interpretation |
|---|---|
| `unsat` | No strictly better timetable exists; the cost is optimal for this model |
| `sat` | A better timetable exists; the implementation raises `AssertionError` |
| `unknown` | The additional verification is inconclusive |

For example, the returned sat6 cost is 6. Proving `W < 6` unsatisfiable verifies
that cost. The schedule's main `status` remains `sat`; the separate
`optimality_status` is `unsat` because the strict-better question has no solution.

This is separate from `--second-solution`, which asks for any different feasible
assignment and may return one with higher cost. It is also separate from the
plain Python feasibility checker. The certificate does not use Optimize's
search, but shares the encoded hard model, so it is not a separately modelled
proof that the problem specification itself is correct.

Optimality verification is **off by default**, requires the full profile and is
not part of the normal 202-check walkthrough count. It has a separate timing.

## 6. Test every constraint automatically

Section 6 of a normal run reads [constraint_tests.zip](constraint_tests.zip) and
its `expected.json`. This archive was created as supplementary synthetic test
data for this implementation; it is separate from the lecturer's official
instances. It contains no additional Python program and does not define new
scheduling constraints.

There are 38 valid input instances and nine deliberately malformed inputs.
Each valid case is checked with both methods/profiles, including known minimum
costs and selected uniqueness results. No separate command or copied code is
needed.

The supplied manifest accounts for **161 checks**: 38 x 2 profiles x 2 methods,
plus nine parser-rejection checks. Expected rejection of malformed input passes
the test; accepting it fails. Valid means syntactically valid, not necessarily
satisfiable. The manifest specifies baseline/full statuses, known optimal costs
and selected second-solution outcomes rather than deriving truth from names.

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

### E1 boundary cases

| File | Scenario | Baseline | Full |
|---|---|---|---|
| `13_daily_limit.txt` | Three nonconsecutive exams in one five-slot day | sat | sat |
| `14_partial_final_day.txt` | Four exams across eight slots, with seven slots/day | sat | sat |
| `15_changed_day_size.txt` | Three exams across two three-slot days | sat | sat |
| `15b_daily_limit_four_exams.txt` | Four exams in one seven-slot day | sat | unsat |

Case 15b allows slots `0,2,4,6` under M4 but fails E1. Case 14 can use
`0,2,4,7`, with three exams in Day 1 and one in a partial Day 2. These fixtures
exercise the three-exam limit independently while preserving M1-M5.

### Six facility-related cases

| File | Scenario | Full result |
|---|---|---|
| `22_missing_facilities.txt` | An exam needs a lab that no room supplies | unsat |
| `23_matching_facilities.txt` | One room supplies both lab and computers | sat; minimum waste 3 |
| `24_features_in_different_rooms.txt` | Features exist separately, but no single room supplies both | unsat |
| `25_facility_competition.txt` | Two simultaneous exams compete for the sole lab room | unsat |
| `26_facilities_and_optimisation.txt` | Optimisation must reserve the lab for the constrained exam | sat; minimum waste 1 |
| `28_facility_case.txt` | Capitalisation and repeated names are normalised | sat; minimum waste 0 |

All six are satisfiable in baseline mode. Four primary E4 cases, 22-25, account
for **16 checks in the E4 output row**. Grouping uses the first rule mentioned
in a case's focus, so case 26 appears under E3 and case 28 under input/edge
cases. Both still exercise facility matching. Group totals therefore do not
list every constraint involved in every test.

The message **E4 NOT EXERCISED here** in the lecturer comparison applies only
to those inputs without facility data. Section 6 supplies the dedicated E4
positive and negative cases; the rule has not been removed from the full model.

Every returned timetable is checked using ordinary Python sets, counts and
sorted student slots. That checker establishes feasibility and recalculates
cost. Unsatisfiability and global optimality need the solver's conclusions or
small-case exhaustive reference checks.

Small generated problems can also be compared with exhaustive enumeration,
including feasibility and minimum unused-seat totals. Such checks supplement
the manifest cases. A finite test suite does not prove every possible unseen
input correct, and expected outcomes must match the configured daily limit.

Additional development verification of the current three-exam policy performed
**1,000 comparisons against exhaustive enumeration**: 250 small generated inputs
times two profiles times two encodings. Focused checks also pinned valid/invalid
daily schedules to exercise the actual model and validator. This is development
evidence, not an extra runtime dependency or an implemented `--selftest` option.

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
| `--verify-optimality` | Verify a full-model result by checking that no strictly lower-cost feasible timetable exists |
| `--compare` | Both methods/profiles on an explicitly supplied ZIP or folder |

For example, these optional commands assume your terminal is already in the
project folder:

```text
python exam_timetabling.py "test instances/sat6.txt" --encoding boolean
python exam_timetabling.py "test instances/sat6.txt" --verify-optimality
python exam_timetabling.py "test instances" --compare
```

`--compare` selects both profiles/methods and is not combined with the
single-instance options. An explicitly supplied ZIP is read directly. The
supplementary archive contains intentionally invalid inputs, so use its automatic
manifest runner rather than the ordinary comparison path.

### Python API

Importing the module is silent. Display and evaluation functions print, while
parsing, solving and validation remain usable independently:

| Interface | Contract |
|---|---|
| `parse_instance(text)` | Return an `Instance`; malformed text raises `ValueError` |
| `read_file(filename)` | Read and parse one text file; filesystem errors remain input errors |
| `solve(instance, encoding="integer", extended=True, second_solution=False, verify_optimality=False)` | Return result data without printing; optional fresh search for a strictly better timetable |
| `validate_timetable(instance, timetable, extended=True)` | Return unused-seat cost or raise `AssertionError` for an invalid concrete timetable |
| `compare(path)` | Print comparisons and return a success Boolean |

Explicit relative paths are relative to the caller's working directory;
automatic startup instead derives its location from the Python file.

Every `solve` result contains:

| Key | Meaning |
|---|---|
| `status` | `sat`, `unsat` or `unknown` |
| `timetable` | List of `(exam, room, slot)` tuples |
| `wasted_seats` | Unused-seat total for sat, otherwise `None` |
| `build_ms` | Preprocessing and construction time in milliseconds |
| `check_ms` | Z3 check time in milliseconds |
| `elapsed_ms` | Construction plus check time in milliseconds; retained for compatibility |

An unknown result adds `reason`. A requested second-solution query after sat
adds `second_status`, `second_timetable`, `second_elapsed_ms` and, if needed,
`second_reason`. No query is made after unsat/unknown. The second search checks
all hard-constraint-feasible alternatives, including ones with worse E3 cost.

When requested after a full-model sat result, the strict-better check adds
`optimality_status` and `optimality_elapsed_ms`; an unknown certificate also
adds `optimality_reason`. Verification with `extended=False` raises `ValueError`.
No follow-up query runs after an initial unsat/unknown result. Inconclusive
optional verification does not invalidate an already feasible timetable, but
does leave that additional check unproved.

An empty list normally means no timetable was returned, but it is also the
valid timetable for an instance with zero exams. Interpret it together with
`status` and the input, rather than testing list truthiness alone.

| Exit code | Meaning |
|---|---|
| 0 | Known single-run result or completed successful evaluation; optional skipped tests may still give 0 |
| 1 | Unknown result or failed/inconclusive evaluation |
| 2 | Invalid arguments or missing/malformed input |

Inspect the final skipped/inconclusive counts as well as the exit code.

### Development evidence used by the report

Additional offline experiments supported the report's deeper evaluation:
independent exhaustive enumeration, a scalar-rejection ablation, and controlled
resource-saturation families. Their scripts and raw measurements are archived
outside the repository, rather than included as solver modules or Moodle
uploads. The report states their methods, settings, results and limitations.

The submitted solver's own walkthrough still provides lecturer comparisons,
independent timetable validation and, when its optional input archive is
available, targeted constraint checks. Neither normal solving nor the
walkthrough depends on the archived experiment materials. Reported experimental
timeouts must remain distinct from unsatisfiability, and the results apply only
to their tested families and settings.

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
4. Explain the offline controlled study and distinguish its methods from the
   submitted solver's runtime features. Separate preprocessing rejections from
   model search, and state the scope of the tested inputs and resource limits.
5. Discuss fixed staffing, the day assumption, no splitting, missing facility
   data in lecturer files and potentially long runs on harder inputs.
6. Connect findings to research and reference the template and Z3 documentation.
   Describe the group's contribution accurately.

The numbered output makes results easier to inspect. The report must still
interpret those results and explain the mathematics. Standard Z3 APIs and
encodings should be attributed accurately; the experimental findings and
modelling decisions are the contributions to analyse rather than claims of
a newly invented general search algorithm.

## 9. Limitations and future work

- Ordered slots are not actual dates or exam durations. M4 applies across
  day boundaries under the chosen interpretation.
- Each exam occupies one room and one slot. Splitting large exams or scheduling
  cohorts separately would change the current problem.
- E1 is implied by M4 for the default five-slot day. The seven-slot fixtures
  are necessary to demonstrate an independent effect of the three-exam rule.
- E2 assumes a fixed 1:30 ratio and a pool of two interchangeable invigilators
  in every slot. It does not generate named staff rotas or infer availability.
- E4 depends on supplied facility data. The lecturer's original instances
  cannot establish facility-test coverage by themselves.
- There is no built-in solve-time limit. Harder instances can take much longer
  than the small examples; timings do not establish a universal performance bound.
- Both formulations share preprocessing and resource logic. Agreement alone
  cannot eliminate common mistakes. Independent expectations, validation and
  exhaustive references provide complementary evidence, not complete coverage
  of every possible unseen input.
- The main solver has no symmetry-breaking mode or unsat-core explanations.
  The offline ablation and controlled-family experiments are development
  analyses, not normal walkthrough options or required runtime files. Their
  single-machine measurements and synthetic families do not establish universal
  performance.

Possible extensions include richer resource availability, controlled scaling
studies and infeasibility explanations. Each needs a stated formulation,
appropriate tests and a clear distinction from the current implemented model.

## 10. Sources and attribution

- **Module convenor's coursework brief:**
  `COMP3070_Coursework1_(26-27)_revised_3Oct26.pdf`. Consult the supplied brief
  for official deliverables, assessment criteria and report requirements.
- **Module convenor's `CW1 template.py`:** the base `Instance` fields and text
  layout. The models, extensions, independent checker, comparisons and automatic
  presentation are additions to that template.
- **Lecturer's development instances:** the 20 inputs supplied in
  `test instances.zip`, extracted in [the sample folder](<test instances/>).
- **Supplementary synthetic inputs:** [constraint_tests.zip](constraint_tests.zip),
  created separately to exercise boundaries, special scenarios and expected
  parser errors. These should be labelled separately in evaluation tables.
- **[Z3 project and Python installation](https://github.com/Z3Prover/z3#python):**
  project and dependency information.
- **[Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html):**
  expression, solver and cardinality function reference.
- **[Cardinality and pseudo-Boolean constraints](https://microsoft.github.io/z3guide/docs/logic/propositional-logic/):**
  background for the counting constraints.
- **[Z3 Optimize API](https://z3prover.github.io/api/html/classz3py_1_1_optimize.html):**
  the minimisation interface used for E3.
