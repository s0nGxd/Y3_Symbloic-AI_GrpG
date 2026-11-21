Setup (from results.csv.meta.txt):

```
date: 2026-11-18T19:20:16
machine: macOS-15.7.1-arm64-arm-64bit (arm64)
python: 3.12.16
time limit per solve: 60.0 s
repeats: 5 if the first run < 1 s, else 3; 1 if it timed out
status: decided if any run decided; timed-out runs counted in 'timeouts'
time_ms: median over the deciding runs of model building + first solve
unique_ms: median of the uniqueness check (block + re-solve)
ortools: 9.15.6755
z3: 5.4.1
```

| File | Expected | A CP-SAT | B Z3 Boolean | C Z3 Integer | Brute force |
| --- | --- | --- | --- | --- | --- |
| example1 | sat | sat ✓ 2.2 | sat ✓ 0.99 | sat ✓ 1.6 | sat ✓ 0.00 |
| example2 | unsat | unsat ✓ 0.00 | unsat ✓ 0.00 | unsat ✓ 0.00 | unsat ✓ 0.00 |
| example3 | sat | sat ✓ 2.0 | sat ✓ 0.67 | sat ✓ 1.7 | sat ✓ 0.01 |
| example4 | unsat | unsat ✓ 0.16 | unsat ✓ 0.49 | unsat ✓ 0.94 | unsat ✓ 0.01 |
| example5 | sat | sat ✓ 2.2 | sat ✓ 1.3 | sat ✓ 1.3 | sat ✓ 0.01 |
| example6 | unsat | unsat ✓ 0.23 | unsat ✓ 1.1 | unsat ✓ 0.77 | unsat ✓ 0.01 |
| example7 | sat | sat ✓ 2.2 | sat ✓ 0.68 | sat ✓ 1.3 | sat ✓ 0.01 |
| example8 | unsat | unsat ✓ 0.13 | unsat ✓ 0.63 | unsat ✓ 1.1 | unsat ✓ 0.01 |
| example9 | sat | sat ✓ 6.6 | sat ✓ 12 | sat ✓ 4.6 | too large |
| example10 | sat | sat ✓ 5.2 | sat ✓ 9.6 | sat ✓ 3.4 | too large |
| example11 | sat | sat ✓ 42 | sat ✓ 174 | sat ✓ 20 | too large |
| example12 | sat | sat ✓ 41 | sat ✓ 154 | sat ✓ 22 | too large |
| example13 | unsat | unsat ✓ 3.3 | unsat ✓ 27 | unsat ✓ 8.8 | too large |
| example14 | unsat | unsat ✓ 0.93 | unsat ✓ 6.9 | unsat ✓ 2.0 | too large |
| example15 | unsat | unsat ✓ 3.2 | unsat ✓ 25 | unsat ✓ 4.7 | too large |
| example16 | sat | sat ✓ 2.8 s | timeout | sat ✓ 2.5 s | too large |
| example17 | sat | sat ✓ 275 | sat ✓ 1.1 s | sat ✓ 56.6 s | too large |
| example18 | unsat | unsat ✓ 622 | unsat ✓ 1.5 s | unsat ✓ 30.6 s (1/3 runs timed out) | too large |
| example19 | unsat | unsat ✓ 2.6 s | unsat ✓ 13.2 s | timeout | too large |

Table 5.1: Answer and median time (ms unless marked s) on examples 1–19.

| Folder | A CP-SAT | B Z3 Boolean | C Z3 Integer | Brute force |
| --- | --- | --- | --- | --- |
| examples 1–19 | 19/19 (10/10 valid) | 18/19 (9/9 valid), 1 timeout | 18/19 (10/10 valid), 1 timeout | 8/8 (4/4 valid) |
| instances/3-constraint | 20/20 (12/12 valid) | 20/20 (12/12 valid) | 20/20 (12/12 valid) | – |
| instances/4-constraint | 20/20 (11/11 valid) | 20/20 (11/11 valid) | 20/20 (11/11 valid) | 1/1 (0/0 valid) |
| instances/4-constraint-hard | 20/20 (5/5 valid) | 10/20 (2/2 valid), 10 timeout | 0/20 (0/0 valid), 20 timeout | – |
| instances/5-constraint | 20/20 (10/10 valid) | 20/20 (10/10 valid) | 20/20 (10/10 valid) | – |
| our-instances | 10/10 (7/7 valid) | 10/10 (7/7 valid) | 10/10 (7/7 valid) | 10/10 (7/7 valid) |

Table 5.2: Answers matching the official answer, and solutions accepted by the independent checker, per folder.

Totals: cpsat: 109/109 decided, 0 wrong, 0 invalid; z3-bool: 98/109 decided, 0 wrong, 0 invalid; z3-int: 88/109 decided, 0 wrong, 0 invalid; brute: 19/19 decided, 0 wrong, 0 invalid

| Folder | Size | A CP-SAT | B Z3 Boolean | C Z3 Integer | Brute force |
| --- | --- | --- | --- | --- | --- |
| examples 1–19 | 3 × 4 | 338 / 3.2 / 2.8 s | 901 / 8.3 / 13.2 s (+1 timeout) | 5.0 s / 2.7 / 56.6 s (+1 timeout) | 0.01 / 0.01 / 0.01 |
| instances/3-constraint | 10 × 50 | 1.7 / 2.2 / 2.8 | 3.6 / 3.5 / 5.2 | 3.2 / 3.5 / 5.4 | – |
| instances/4-constraint | 8 × 20 | 4.4 / 5.3 / 9.7 | 11 / 11 / 17 | 3.8 / 4.3 / 5.7 | 5.1 s / 5.1 s / 5.1 s |
| instances/4-constraint-hard | 60 × 500 | 6.1 s / 4.0 s / 19.3 s | 29.9 s / 22.2 s / 56.2 s (+10 timeout) | all 20 timeout | – |
| instances/5-constraint | 10 × 50 | 6.0 / 5.0 / 12 | 25 / 24 / 34 | 8.0 / 8.4 / 11 | – |
| our-instances | 4 × 3 | 2.0 / 2.5 / 3.7 | 2.0 / 1.4 / 4.7 | 6.3 / 3.1 / 25 | 0.21 / 0.01 / 1.7 |

Table 5.3: Mean / median / max time (ms unless marked s) of the instances solved within the limit, per folder. Size = steps × users of the first file.

| File | Approach | Answer | Pattern | Users | Speed-up |
| --- | --- | --- | --- | --- | --- |
| instances/4-constraint-hard/0.txt | A CP-SAT | sat | 2.0 s | timeout | users timed out |
| instances/4-constraint-hard/0.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/1.txt | A CP-SAT | unsat | 5.4 s | timeout | users timed out |
| instances/4-constraint-hard/1.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/2.txt | A CP-SAT | sat | 10.3 s | timeout | users timed out |
| instances/4-constraint-hard/2.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/3.txt | A CP-SAT | unsat | 9.7 s | timeout | users timed out |
| instances/4-constraint-hard/3.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/4.txt | A CP-SAT | unsat | 2.3 s | timeout | users timed out |
| instances/4-constraint-hard/4.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/5.txt | A CP-SAT | unsat | 4.9 s | timeout | users timed out |
| instances/4-constraint-hard/5.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/6.txt | A CP-SAT | sat | 2.4 s | timeout | users timed out |
| instances/4-constraint-hard/6.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/7.txt | A CP-SAT | unsat | 7.9 s | timeout | users timed out |
| instances/4-constraint-hard/7.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/8.txt | A CP-SAT | unsat | 8.0 s | timeout | users timed out |
| instances/4-constraint-hard/8.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/9.txt | A CP-SAT | sat | 1.7 s | timeout | users timed out |
| instances/4-constraint-hard/9.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/10.txt | A CP-SAT | unsat | 19.3 s | timeout | users timed out |
| instances/4-constraint-hard/10.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/11.txt | A CP-SAT | unsat | 2.6 s | timeout | users timed out |
| instances/4-constraint-hard/11.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/12.txt | A CP-SAT | unsat | 3.1 s | timeout | users timed out |
| instances/4-constraint-hard/12.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/13.txt | A CP-SAT | unsat | 2.9 s | timeout | users timed out |
| instances/4-constraint-hard/13.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/14.txt | A CP-SAT | unsat | 1.9 s | timeout | users timed out |
| instances/4-constraint-hard/14.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/15.txt | A CP-SAT | sat | 7.3 s | timeout | users timed out |
| instances/4-constraint-hard/15.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/16.txt | A CP-SAT | unsat | 2.7 s | timeout | users timed out |
| instances/4-constraint-hard/16.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/17.txt | A CP-SAT | unsat | 3.1 s | timeout | users timed out |
| instances/4-constraint-hard/17.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/18.txt | A CP-SAT | unsat | 18.4 s | timeout | users timed out |
| instances/4-constraint-hard/18.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/19.txt | A CP-SAT | unsat | 7.0 s | timeout | users timed out |
| instances/4-constraint-hard/19.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/example16.txt | A CP-SAT | sat | 2.8 s | timeout | users timed out |
| instances/example16.txt | C Z3 Integer | sat | 2.5 s | timeout | users timed out |
| instances/example17.txt | A CP-SAT | sat | 275 | 45.9 s | 166.9× |
| instances/example17.txt | C Z3 Integer | sat | 56.6 s | timeout | users timed out |
| instances/example18.txt | A CP-SAT | unsat | 622 | 5.5 s | 8.8× |
| instances/example18.txt | C Z3 Integer | unsat | 30.6 s | timeout | users timed out |
| instances/example19.txt | A CP-SAT | unsat | 2.6 s | timeout | users timed out |
| instances/example19.txt | C Z3 Integer | unknown | timeout | timeout |  |

Table 5.4: At-most-k encodings, pattern (user-independent) vs users (one helper per user). Speed-up = users time / pattern time.

| Folder | Approach | Sat | Only solution | Other solutions exist | First solve | Uniqueness check |
| --- | --- | --- | --- | --- | --- | --- |
| examples 1–19 | A CP-SAT | 10 | 3 | 7 | 5.9 | 5.0 |
| examples 1–19 | B Z3 Boolean | 9 | 3 | 6 | 9.6 | 1.2 |
| examples 1–19 | C Z3 Integer | 10 | 3 | 7 | 4.0 | 1.0 |
| examples 1–19 | Brute force | 4 | 3 | 1 | 0.01 | 0.00 |
| instances/3-constraint | A CP-SAT | 12 | 0 | 12 | 2.4 | 1.9 |
| instances/3-constraint | B Z3 Boolean | 12 | 0 | 12 | 3.8 | 0.84 |
| instances/3-constraint | C Z3 Integer | 12 | 0 | 12 | 4.0 | 0.64 |
| instances/4-constraint | A CP-SAT | 11 | 0 | 11 | 6.5 | 5.1 |
| instances/4-constraint | B Z3 Boolean | 11 | 0 | 11 | 12 | 1.4 |
| instances/4-constraint | C Z3 Integer | 11 | 0 | 11 | 4.6 | 1.0 |
| instances/4-constraint-hard | A CP-SAT | 5 | 0 | 5 | 2.4 s | 2.5 s |
| instances/4-constraint-hard | B Z3 Boolean | 2 | 0 | 2 | 19.0 s | 12.9 s |
| instances/5-constraint | A CP-SAT | 10 | 0 | 10 | 9.3 | 6.5 |
| instances/5-constraint | B Z3 Boolean | 10 | 0 | 10 | 28 | 2.4 |
| instances/5-constraint | C Z3 Integer | 10 | 0 | 10 | 9.4 | 1.6 |
| our-instances | A CP-SAT | 7 | 2 | 5 | 2.7 | 2.8 |
| our-instances | B Z3 Boolean | 7 | 2 | 5 | 2.6 | 0.46 |
| our-instances | C Z3 Integer | 7 | 2 | 5 | 3.5 | 1.0 |
| our-instances | Brute force | 7 | 2 | 5 | 0.02 | 0.01 |

Table 5.5: Uniqueness check on the satisfiable instances: number with exactly one solution, and median first-solve time vs median uniqueness-check time (ms unless marked s).

| File | Approach | Users (plain) | Users (optimised) | Time plain | Time optimised |
| --- | --- | --- | --- | --- | --- |
| instances/3-constraint/0.txt | A CP-SAT | 5 | 3 ← | 2.6 | 4.6 |
| instances/3-constraint/1.txt | A CP-SAT | 6 | 2 ← | 2.3 | 4.3 |
| instances/3-constraint/2.txt | A CP-SAT | 7 | 2 ← | 2.4 | 4.8 |
| instances/3-constraint/3.txt | A CP-SAT | 8 | 2 ← | 2.6 | 5.6 |
| instances/3-constraint/6.txt | A CP-SAT | 8 | 3 ← | 2.4 | 6.4 |
| instances/3-constraint/8.txt | A CP-SAT | 8 | 2 ← | 2.2 | 5.0 |
| instances/3-constraint/10.txt | A CP-SAT | 9 | 3 ← | 2.7 | 5.9 |
| instances/3-constraint/11.txt | A CP-SAT | 7 | 3 ← | 2.3 | 3.1 |
| instances/3-constraint/13.txt | A CP-SAT | 7 | 3 ← | 2.5 | 4.3 |
| instances/3-constraint/16.txt | A CP-SAT | 5 | 2 ← | 2.2 | 5.4 |
| instances/3-constraint/18.txt | A CP-SAT | 6 | 2 ← | 2.3 | 4.4 |
| instances/3-constraint/19.txt | A CP-SAT | 5 | 2 ← | 2.8 | 4.0 |
| instances/4-constraint/0.txt | A CP-SAT | 2 | 2 | 9.7 | 7.0 |
| instances/4-constraint/5.txt | A CP-SAT | 3 | 3 | 5.7 | 6.3 |
| instances/4-constraint/6.txt | A CP-SAT | 3 | 3 | 5.4 | 6.5 |
| instances/4-constraint/7.txt | A CP-SAT | 3 | 2 ← | 8.4 | 7.8 |
| instances/4-constraint/8.txt | A CP-SAT | 2 | 2 | 6.3 | 6.7 |
| instances/4-constraint/10.txt | A CP-SAT | 2 | 2 | 7.4 | 7.6 |
| instances/4-constraint/11.txt | A CP-SAT | 3 | 2 ← | 7.0 | 8.4 |
| instances/4-constraint/12.txt | A CP-SAT | 2 | 2 | 5.2 | 5.6 |
| instances/4-constraint/14.txt | A CP-SAT | 2 | 2 | 6.5 | 6.2 |
| instances/4-constraint/18.txt | A CP-SAT | 3 | 2 ← | 6.5 | 7.0 |
| instances/4-constraint/19.txt | A CP-SAT | 3 | 2 ← | 6.5 | 5.5 |
| instances/5-constraint/2.txt | A CP-SAT | 2 | 2 | 11 | 12 |
| instances/5-constraint/3.txt | A CP-SAT | 2 | 2 | 11 | 12 |
| instances/5-constraint/5.txt | A CP-SAT | 3 | 3 | 6.2 | 6.9 |
| instances/5-constraint/6.txt | A CP-SAT | 3 | 2 ← | 11 | 11 |
| instances/5-constraint/9.txt | A CP-SAT | 2 | 2 | 12 | 13 |
| instances/5-constraint/10.txt | A CP-SAT | 3 | 3 | 10 | 11 |
| instances/5-constraint/12.txt | A CP-SAT | 3 | 2 ← | 7.5 | 8.4 |
| instances/5-constraint/13.txt | A CP-SAT | 3 | 2 ← | 8.6 | 9.2 |
| instances/5-constraint/16.txt | A CP-SAT | 3 | 2 ← | 8.2 | 8.6 |
| instances/5-constraint/18.txt | A CP-SAT | 3 | 3 | 7.6 | 8.3 |
| instances/example1.txt | A CP-SAT | 2 | 1 ← | 2.2 | 2.2 |
| instances/example3.txt | A CP-SAT | 2 | 2 | 2.0 | 2.0 |
| instances/example5.txt | A CP-SAT | 3 | 3 | 2.2 | 2.1 |
| instances/example7.txt | A CP-SAT | 5 | 5 | 2.2 | 2.0 |
| instances/example9.txt | A CP-SAT | 2 | 2 | 6.6 | 6.9 |
| instances/example10.txt | A CP-SAT | 2 | 2 | 5.2 | 5.7 |
| instances/example11.txt | A CP-SAT | 5 | 4 ← | 42 | 63 |
| instances/example12.txt | A CP-SAT | 5 | 4 ← | 41 | 67 |
| instances/example16.txt | A CP-SAT | 7 | 5 ← | 2.8 s | 10.4 s |
| instances/example17.txt | A CP-SAT | 19 | 10 ← | 275 | 1.5 s |
| our-instances/e1-at-least-k-sat.txt | A CP-SAT | 3 | 3 | 3.2 | 3.0 |
| our-instances/e2-max-workload-sat.txt | A CP-SAT | 3 | 3 | 3.7 | 3.3 |
| our-instances/e2-max-workload-unique.txt | A CP-SAT | 2 | 2 | 2.3 | 2.5 |
| our-instances/e3-conditional-unique.txt | A CP-SAT | 2 | 2 | 2.4 | 2.4 |
| our-instances/e4-minimise-users-2.txt | A CP-SAT | 2 | 2 | 2.7 | 3.0 |
| our-instances/e4-minimise-users-3.txt | A CP-SAT | 3 | 3 | 2.6 | 2.6 |
| our-instances/mixed-all-constraints.txt | A CP-SAT | 3 | 3 | 2.9 | 3.0 |

Table 5.6: Users in the first solution found (plain) vs the optimised solution (E4). Fewer users in 25 of 50 runs (←).
