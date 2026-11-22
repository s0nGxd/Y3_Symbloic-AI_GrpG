# COMP3070 Coursework 2 – Workflow Satisfiability Problem (WSP) Solver

Given a workflow (steps), a set of users and security constraints, the solver
assigns exactly one user to every step so that all constraints hold, or proves
that no such assignment exists. When it finds one, it also reports whether it is
the **only** solution.

**Status:** code complete. All 111 test instances pass (99 lecturer + 8 our
extra-constraint tests + 4 edge-case tests). `results/` holds the final
benchmark of all four approaches (Windows 11 laptop, 22 Nov 2026).

> **What we submit:** only `coursework02.py` (single file, as the brief asks).
> Everything else in this folder is for testing, benchmarking and the report.

---

## 1. Setup (once)

Use a **separate conda environment**. Installing OR-Tools into Anaconda's `base`
environment crashes on import (a protobuf clash: *"File already exists in database"*).

```bash
conda create -n wsp python=3.12 -y
conda activate wsp
pip install ortools z3-solver matplotlib
python -c "from ortools.sat.python import cp_model; import z3; print('ok')"
```

In VS Code: `Cmd+Shift+P` → **Python: Select Interpreter** → `wsp`.
Every new terminal needs `conda activate wsp` (the prompt shows `(wsp)`).

Versions used for the results: Python 3.12.16, OR-Tools 9.15.6755, Z3 5.4.1,
macOS 15.7 (Apple Silicon).

---

## 2. Folder structure

```
coursework-SA-02/
├── coursework02.py        ← THE SUBMISSION: solver, tests, benchmark, all in one file
├── report_tables.py       ← helper (not submitted): benchmark CSV → report tables + chart
├── README.md              ← this file
├── instances/             ← lecturer: example1–19 (12 is identical to 11)
│                            + 3/4/5-constraint + 4-constraint-hard
├── our-instances/         ← ours: 8 test files for the extra constraints E1–E4
├── edge-cases/            ← ours: 4 awkward-but-valid input files (one file holds
│                            BOM, CRLF, tabs, blank lines, any case, extra spaces)
└── results/               ← final benchmark output used in the report
    ├── results.csv            raw data, one row per instance × approach
    ├── results.csv.meta.txt   machine, versions, time limit, repeat policy
    ├── report_tables.md       Tables 5.1–5.6, ready to paste
    ├── scaling.png            chart: time vs instance size
    └── explain.txt            why each unsat instance is impossible
```

Every instance `X.txt` has an `X-solution.txt` next to it (first line `sat`/`unsat`).
Our own solution files may also contain `# unique: yes|no` and `# min-users: k`.

---

## 3. How to run

### From Python (the lecturer's template interface)

```python
from coursework02 import Solver, transform_output
d = Solver("instances/example3.txt")      # {'sat', 'sol', 'mul_sol', 'exe_time'}
print(transform_output(d))
```

Optional keyword arguments of `Solver()`:

| Argument | Default | Meaning |
| --- | --- | --- |
| `silent` | `False` | don't print the file name |
| `method` | `'cpsat'` | `'cpsat'` (A), `'z3-bool'` (B), `'z3-int'` (C), `'cpsat-int'` (D), `'brute'` (tiny files only) |
| `amk` | `'pattern'` | At-most-k encoding: `'pattern'` or `'users'` |
| `timeout` | `None` | seconds per solve (`None` = no limit, what the marker uses) |
| `optimise` | `False` | E4: return a solution with the fewest users |

### From the command line

```bash
python coursework02.py instances/example3.txt                 # solve, template output
python coursework02.py instances/example3.txt --method z3-int # another approach
python coursework02.py instances/example1.txt --optimise      # fewest users (E4)
python coursework02.py instances/example2.txt --explain       # why is it unsat?
python coursework02.py -h                                     # all options
```

Expected output for `example3.txt`:

```
sat
s1: u3
s2: u1
s3: u3
this is the only solution
2ms
```

---

## 4. Testing (run before every commit)

```bash
python coursework02.py instances our-instances edge-cases --test --timeout 60
```

Expected last line: **`111 passed, 0 failed, 0 timed out`** (a few minutes; the
`4-constraint-hard` folder takes most of it).

`--test` compares every answer with its `-solution.txt` (or the Appendix 1 table for
`exampleN.txt`), checks uniqueness where known, and runs the **independent checker**
`verify()` on every solution — so a wrong solver answer cannot pass.

Quick checks:

```bash
python coursework02.py our-instances edge-cases --test                    # ~1 s
python coursework02.py instances/example*.txt --test --method z3-int --timeout 60
python coursework02.py our-instances --test --method brute                # exhaustive oracle
```

Approaches B, C and D time out on some hard instances — `TIME` lines are expected
for them, not failures.

---

## 5. What is inside `coursework02.py`

| Section | Contents |
| --- | --- |
| 2 | `Instance` data class (0-based steps/users) |
| 3 | `parse_instance()` – Appendix 1 format: any case, extra spaces, CRLF, BOM |
| 4 | Solver back-ends `CpSatBackend`, `Z3Backend` behind one small interface |
| 5 | `BooleanModel` – x[s,u] formulation, one method per constraint (approaches A, B) |
| 6 | `Z3IntegerModel` – a[s] = user formulation (approach C); also used by `--explain` |
| 6b | `CpSatIntegerModel` – the same integer formulation in CP-SAT (approach D) |
| 7–8 | `solve_with()` – build, solve, read answer, uniqueness check; `explain_unsat()` |
| 9 | `Solver()` – lecturer's interface |
| 10 | `transform_output()` – copied unchanged from the lecturer's helper |
| 11 | `verify()` – independent checker, no solver |
| 12 | `--test` runner; 12b `--bench` benchmark |
| 13 | command line |

### Four approaches (2 formulations × 2 solvers)

| | Solver | Formulation | Role |
| --- | --- | --- | --- |
| **A** `cpsat` | OR-Tools CP-SAT | Boolean x[s,u] = 1 ⇔ user u does step s | main, default |
| **B** `z3-bool` | Z3 | the *identical* Boolean model | compares solvers fairly |
| **C** `z3-int` | Z3 | integer a[s] = u | compares formulations |
| **D** `cpsat-int` | OR-Tools CP-SAT | the *same* integer model, lab style: `NewIntVar` domains, `AddAllDifferent`, `OnlyEnforceIf` | C vs D compares solvers again (Lab 7) |

### Constraints

| ID | File line | Meaning |
| --- | --- | --- |
| C1 | `Authorisations u1 s1 s2` | u1 may only do s1, s2 (no line = any step; empty list = none) |
| C2 | `Separation-of-duty s1 s2` | different users |
| C3 | `Binding-of-duty s1 s2` | same user |
| C4 | `At-most-k 2 s1 s2 s3` | at most k distinct users over the steps |
| C5 | `One-team s1 s2 (u1 u2) (u3 u4)` | all steps by members of one team |
| E1 | `At-least-k 2 s1 s2 s3` | **ours:** at least k distinct users |
| E2 | `Max-workload 3` | **ours:** no user does more than L steps |
| E3 | `Conditional s1 u1 s2 u2` | **ours:** if u1 does s1, u2 must not do s2 |
| E4 | `Minimise-users` (or `optimise=True`) | **ours:** fewest distinct users (objective) |

**Key design decision – At-most-k "pattern" encoding.** Instead of one helper
variable per user (`--amk users`), we only encode *which steps share a user*
(user-independent, after Karapetyan et al., 2019). Example 17: 275 ms vs 45.9 s;
the users encoding timed out on all 20 hard instances.

---

## 6. Benchmark and report tables

The data in `results/` came from these commands (about 2 hours in total;
resumable — rerun the same command after Ctrl+C and it continues).
On Windows, run the `python` lines one at a time without `caffeinate`:

```bash
caffeinate -i sh -c '
python coursework02.py instances our-instances --bench results/results.csv --methods cpsat,cpsat-int,brute &&
python coursework02.py instances/example*.txt instances/3-constraint instances/4-constraint instances/5-constraint our-instances --bench results/results.csv --methods cpsat,cpsat-int --optimise &&
python coursework02.py instances our-instances --bench results/results.csv --methods z3-bool,z3-int &&
python coursework02.py instances/example16.txt instances/example17.txt instances/example18.txt instances/example19.txt instances/4-constraint-hard --bench results/results.csv --methods cpsat,z3-int,cpsat-int --amks users &&
python coursework02.py instances/example2.txt instances/example4.txt instances/example6.txt instances/example8.txt instances/example13.txt instances/example14.txt instances/example15.txt our-instances --explain --timeout 60 > results/explain.txt &&
python report_tables.py results/results.csv'
```

Benchmark settings: 60 s limit per solve; median of 5 runs if the first run is
under 1 s, otherwise 3; timed-out runs are not repeated. Time = model building +
first solve (high-resolution clock). To regenerate only the tables and chart:

```bash
python report_tables.py results/results.csv
```

### Headline results

| | A CP-SAT Bool | B Z3 Bool | C Z3 Int | D CP-SAT Int |
| --- | --- | --- | --- | --- |
| Decided within 60 s | **107 / 107** | 91 / 107 | 85 / 107 | 105 / 107 |
| Hard folder (60 steps × 500 users) | **20 / 20**, median 10.5 s | 5 / 20, median 39.9 s | 0 / 20 | 19 / 20, median 20.3 s |
| Wrong answers / invalid solutions | 0 | 0 | 0 | 0 |

Same solver, different formulation (A vs D) and same formulation, different
solver (A vs B, C vs D): CP-SAT wins both solver comparisons, and the Boolean
formulation beats the integer one in CP-SAT. Optimisation (E4) used fewer users
in 47 of 93 runs (e.g. example 17: 19 → 10 users).

---

## 7. Working on the code (teammates)

1. `git pull` (or copy the folder), `conda activate wsp`.
2. Make your change in `coursework02.py`.
3. Run the full test command in §4 — it must still say **279 passed**.
4. Commit with a clear message.

**Adding a new constraint type** touches seven places, all marked by section headers:
`Instance` field (2) → parser branch (3) → `BooleanModel.add_…` (5) →
`Z3IntegerModel.add_…` (6) → `CpSatIntegerModel.build` (6b) → `verify()` (11) → a new test file with a
`-solution.txt` in `our-instances/`. Use `--method brute` to get the expected
answer for a small test file.

**Do not change** the `Solver()` name, its return keys, or the strings
`'sat'`, `'unsat'`, `'other solutions exist'`, `'this is the only solution'` —
the marker probably checks them automatically.

---

## 8. Notes

- **Timing varies between runs** (the solvers search in parallel), which is why
  the benchmark reports medians. A few Z3 instances solved in some runs and timed
  out in others; the CSV column `timeouts` records this.
- `example2` shows 0.00 ms for every approach: a step there has no authorised
  user, so it is reported unsat before any model is built.
- Ctrl+C stops the whole run cleanly (CP-SAT normally swallows it; we re-raise it).

## Credits

- `Solver()` interface, return dict and output strings: COMP3070 CW2 template.
- `transform_output()`: copied unchanged from the COMP3070 CW2 helper.
- At-most-k pattern idea: Karapetyan, D., Parkes, A. J., Gutin, G., & Gagarin, A.
  (2019). Pattern-based approach to the workflow satisfiability problem with
  user-independent constraints. *Journal of Artificial Intelligence Research, 66*,
  85–122. https://doi.org/10.1613/jair.1.11339
