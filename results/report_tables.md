Setup (from results/results.csv.meta.txt):

```
date: 2026-11-22T22:43:35
machine: Windows-11-10.0.26300-SP0 (AMD64)
python: 3.12.9
time limit per solve: 60.0 s
repeats: 5 if the first run < 1 s, else 3; 1 if it timed out
status: decided if any run decided; timed-out runs counted in 'timeouts'
time_ms: median over the deciding runs of model building + first solve
unique_ms: median of the uniqueness check (block + re-solve)
ortools: 9.15.6755
z3: 5.3.3
```

| File | Expected | A CP-SAT | B Z3 Boolean | C Z3 Integer | D CP-SAT Integer | Brute force |
| --- | --- | --- | --- | --- | --- | --- |
| example1 | sat | sat ✓ 15 | sat ✓ 2.3 | sat ✓ 3.7 | sat ✓ 15 | sat ✓ 0.02 |
| example2 | unsat | unsat ✓ 0.01 | unsat ✓ 0.01 | unsat ✓ 0.01 | unsat ✓ 0.01 | unsat ✓ 0.01 |
| example3 | sat | sat ✓ 15 | sat ✓ 2.2 | sat ✓ 3.9 | sat ✓ 14 | sat ✓ 0.03 |
| example4 | unsat | unsat ✓ 0.54 | unsat ✓ 1.3 | unsat ✓ 2.5 | unsat ✓ 0.68 | unsat ✓ 0.04 |
| example5 | sat | sat ✓ 14 | sat ✓ 3.5 | sat ✓ 3.9 | sat ✓ 15 | sat ✓ 0.02 |
| example6 | unsat | unsat ✓ 1.00 | unsat ✓ 3.3 | unsat ✓ 2.3 | unsat ✓ 1.3 | unsat ✓ 0.04 |
| example7 | sat | sat ✓ 14 | sat ✓ 1.8 | sat ✓ 2.7 | sat ✓ 15 | sat ✓ 0.03 |
| example8 | unsat | unsat ✓ 0.65 | unsat ✓ 2.1 | unsat ✓ 2.5 | unsat ✓ 0.63 | unsat ✓ 0.05 |
| example9 | sat | sat ✓ 32 | sat ✓ 27 | sat ✓ 11 | sat ✓ 46 | too large |
| example10 | sat | sat ✓ 31 | sat ✓ 21 | sat ✓ 7.6 | sat ✓ 46 | too large |
| example11 | sat | sat ✓ 148 | sat ✓ 343 | sat ✓ 34 | sat ✓ 251 | too large |
| example12 | sat | sat ✓ 140 | sat ✓ 346 | sat ✓ 31 | sat ✓ 206 | too large |
| example13 | unsat | unsat ✓ 13 | unsat ✓ 65 | unsat ✓ 18 | unsat ✓ 7.2 | too large |
| example14 | unsat | unsat ✓ 4.0 | unsat ✓ 16 | unsat ✓ 4.9 | unsat ✓ 1.1 | too large |
| example15 | unsat | unsat ✓ 14 | unsat ✓ 52 | unsat ✓ 9.8 | unsat ✓ 1.8 | too large |
| example16 | sat | sat ✓ 6.3 s | timeout | sat ✓ 5.9 s | timeout | too large |
| example17 | sat | sat ✓ 880 | sat ✓ 2.1 s | timeout | sat ✓ 2.0 s | too large |
| example18 | unsat | unsat ✓ 2.3 s | unsat ✓ 2.8 s | unsat ✓ 51.4 s (1/2 runs timed out) | unsat ✓ 6.6 s | too large |
| example19 | unsat | unsat ✓ 6.6 s | unsat ✓ 25.5 s | timeout | unsat ✓ 25.6 s | too large |

Table 5.1: Answer and median time (ms unless marked s) on examples 1–19.

| Folder | A CP-SAT | B Z3 Boolean | C Z3 Integer | D CP-SAT Integer | Brute force |
| --- | --- | --- | --- | --- | --- |
| examples 1–19 | 19/19 (10/10 valid) | 18/19 (9/9 valid), 1 timeout | 17/19 (9/9 valid), 2 timeout | 18/19 (9/9 valid), 1 timeout | 8/8 (4/4 valid) |
| instances/3-constraint | 20/20 (12/12 valid) | 20/20 (12/12 valid) | 20/20 (12/12 valid) | 20/20 (12/12 valid) | – |
| instances/4-constraint | 20/20 (11/11 valid) | 20/20 (11/11 valid) | 20/20 (11/11 valid) | 20/20 (11/11 valid) | 1/1 (0/0 valid) |
| instances/4-constraint-hard | 20/20 (5/5 valid) | 5/20 (2/2 valid), 15 timeout | 0/20 (0/0 valid), 20 timeout | 19/20 (5/5 valid), 1 timeout | – |
| instances/5-constraint | 20/20 (10/10 valid) | 20/20 (10/10 valid) | 20/20 (10/10 valid) | 20/20 (10/10 valid) | – |
| our-instances | 8/8 (5/5 valid) | 8/8 (5/5 valid) | 8/8 (5/5 valid) | 8/8 (5/5 valid) | 8/8 (5/5 valid) |

Table 5.2: Answers matching the official answer, and solutions accepted by the independent checker, per folder.

Totals: cpsat: 107/107 decided, 0 wrong, 0 invalid; z3-bool: 91/107 decided, 0 wrong, 0 invalid; z3-int: 85/107 decided, 0 wrong, 0 invalid; cpsat-int: 105/107 decided, 0 wrong, 0 invalid; brute: 17/17 decided, 0 wrong, 0 invalid

| Folder | Size | A CP-SAT | B Z3 Boolean | C Z3 Integer | D CP-SAT Integer | Brute force |
| --- | --- | --- | --- | --- | --- | --- |
| examples 1–19 | 3 × 4 | 867 / 15 / 6.6 s | 1.7 s / 18 / 25.5 s (+1 timeout) | 3.4 s / 4.9 / 51.4 s (+2 timeout) | 1.9 s / 15 / 25.6 s (+1 timeout) | 0.03 / 0.03 / 0.05 |
| instances/3-constraint | 10 × 50 | 9.6 / 14 / 15 | 12 / 12 / 17 | 11 / 12 / 19 | 9.3 / 15 / 16 | – |
| instances/4-constraint | 8 × 20 | 20 / 30 / 34 | 26 / 25 / 38 | 9.2 / 9.5 / 13 | 25 / 30 / 48 | 16.9 s / 16.9 s / 16.9 s |
| instances/4-constraint-hard | 60 × 500 | 14.3 s / 10.5 s / 45.7 s | 40.1 s / 39.9 s / 52.7 s (+15 timeout) | all 20 timeout | 25.1 s / 20.3 s / 52.9 s (+1 timeout) | – |
| instances/5-constraint | 10 × 50 | 29 / 24 / 61 | 58 / 55 / 82 | 20 / 19 / 29 | 32 / 22 / 78 | – |
| our-instances | 4 × 3 | 9.6 / 14 / 16 | 5.0 / 4.3 / 11 | 14 / 6.4 / 47 | 9.4 / 14 / 15 | 0.82 / 0.04 / 5.9 |

Table 5.3: Mean / median / max time (ms unless marked s) of the instances solved within the limit, per folder. Size = steps × users of the first file.

| File | Approach | Answer | Pattern | Users | Speed-up |
| --- | --- | --- | --- | --- | --- |
| instances/4-constraint-hard/0.txt | A CP-SAT | sat | 3.5 s | timeout | users timed out |
| instances/4-constraint-hard/0.txt | D CP-SAT Integer | sat | 10.2 s | timeout | users timed out |
| instances/4-constraint-hard/0.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/1.txt | A CP-SAT | unsat | 11.6 s | timeout | users timed out |
| instances/4-constraint-hard/1.txt | D CP-SAT Integer | unsat | 29.3 s | timeout | users timed out |
| instances/4-constraint-hard/1.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/2.txt | A CP-SAT | sat | 12.1 s | timeout | users timed out |
| instances/4-constraint-hard/2.txt | D CP-SAT Integer | sat | 15.5 s | timeout | users timed out |
| instances/4-constraint-hard/2.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/3.txt | A CP-SAT | unsat | 21.7 s | timeout | users timed out |
| instances/4-constraint-hard/3.txt | D CP-SAT Integer | unsat | 52.9 s | timeout | users timed out |
| instances/4-constraint-hard/3.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/4.txt | A CP-SAT | unsat | 5.8 s | timeout | users timed out |
| instances/4-constraint-hard/4.txt | D CP-SAT Integer | unsat | 18.2 s | timeout | users timed out |
| instances/4-constraint-hard/4.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/5.txt | A CP-SAT | unsat | 13.3 s | timeout | users timed out |
| instances/4-constraint-hard/5.txt | D CP-SAT Integer | unsat | 31.8 s | timeout | users timed out |
| instances/4-constraint-hard/5.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/6.txt | A CP-SAT | sat | 9.4 s | timeout | users timed out |
| instances/4-constraint-hard/6.txt | D CP-SAT Integer | sat | 9.3 s | timeout | users timed out |
| instances/4-constraint-hard/6.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/7.txt | A CP-SAT | unsat | 19.3 s | timeout | users timed out |
| instances/4-constraint-hard/7.txt | D CP-SAT Integer | unsat | 35.1 s | timeout | users timed out |
| instances/4-constraint-hard/7.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/8.txt | A CP-SAT | unsat | 21.2 s | timeout | users timed out |
| instances/4-constraint-hard/8.txt | D CP-SAT Integer | unsat | 39.8 s | timeout | users timed out |
| instances/4-constraint-hard/8.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/9.txt | A CP-SAT | sat | 5.4 s | timeout | users timed out |
| instances/4-constraint-hard/9.txt | D CP-SAT Integer | sat | 7.7 s | timeout | users timed out |
| instances/4-constraint-hard/9.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/10.txt | A CP-SAT | unsat | 43.8 s | timeout | users timed out |
| instances/4-constraint-hard/10.txt | D CP-SAT Integer | unsat | 51.3 s | timeout | users timed out |
| instances/4-constraint-hard/10.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/11.txt | A CP-SAT | unsat | 7.3 s | timeout | users timed out |
| instances/4-constraint-hard/11.txt | D CP-SAT Integer | unsat | 17.9 s | timeout | users timed out |
| instances/4-constraint-hard/11.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/12.txt | A CP-SAT | unsat | 7.1 s | timeout | users timed out |
| instances/4-constraint-hard/12.txt | D CP-SAT Integer | unsat | 27.8 s | timeout | users timed out |
| instances/4-constraint-hard/12.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/13.txt | A CP-SAT | unsat | 7.4 s | timeout | users timed out |
| instances/4-constraint-hard/13.txt | D CP-SAT Integer | unsat | 20.3 s | timeout | users timed out |
| instances/4-constraint-hard/13.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/14.txt | A CP-SAT | unsat | 4.9 s | timeout | users timed out |
| instances/4-constraint-hard/14.txt | D CP-SAT Integer | unsat | 16.1 s | timeout | users timed out |
| instances/4-constraint-hard/14.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/15.txt | A CP-SAT | sat | 15.0 s | timeout | users timed out |
| instances/4-constraint-hard/15.txt | D CP-SAT Integer | sat | 23.6 s | timeout | users timed out |
| instances/4-constraint-hard/15.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/16.txt | A CP-SAT | unsat | 6.7 s | timeout | users timed out |
| instances/4-constraint-hard/16.txt | D CP-SAT Integer | unsat | 19.9 s | timeout | users timed out |
| instances/4-constraint-hard/16.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/17.txt | A CP-SAT | unsat | 7.5 s | timeout | users timed out |
| instances/4-constraint-hard/17.txt | D CP-SAT Integer | unsat | 18.9 s | timeout | users timed out |
| instances/4-constraint-hard/17.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/18.txt | A CP-SAT | unsat | 45.7 s | timeout | users timed out |
| instances/4-constraint-hard/18.txt | D CP-SAT Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/18.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/4-constraint-hard/19.txt | A CP-SAT | unsat | 18.0 s | timeout | users timed out |
| instances/4-constraint-hard/19.txt | D CP-SAT Integer | unsat | 32.1 s | timeout | users timed out |
| instances/4-constraint-hard/19.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/example16.txt | A CP-SAT | sat | 6.3 s | timeout | users timed out |
| instances/example16.txt | D CP-SAT Integer | unknown | timeout | 60.3 s |  |
| instances/example16.txt | C Z3 Integer | sat | 5.9 s | timeout | users timed out |
| instances/example17.txt | A CP-SAT | sat | 880 | timeout | users timed out |
| instances/example17.txt | D CP-SAT Integer | sat | 2.0 s | timeout | users timed out |
| instances/example17.txt | C Z3 Integer | unknown | timeout | timeout |  |
| instances/example18.txt | A CP-SAT | unsat | 2.3 s | 7.7 s | 3.4× |
| instances/example18.txt | D CP-SAT Integer | unsat | 6.6 s | timeout | users timed out |
| instances/example18.txt | C Z3 Integer | unsat | 51.4 s | timeout | users timed out |
| instances/example19.txt | A CP-SAT | unsat | 6.6 s | timeout | users timed out |
| instances/example19.txt | D CP-SAT Integer | unsat | 25.6 s | timeout | users timed out |
| instances/example19.txt | C Z3 Integer | unknown | timeout | timeout |  |

Table 5.4: At-most-k encodings, pattern (user-independent) vs users (one helper per user). Speed-up = users time / pattern time.

| Folder | Approach | Sat | Only solution | Other solutions exist | First solve | Uniqueness check |
| --- | --- | --- | --- | --- | --- | --- |
| examples 1–19 | A CP-SAT | 10 | 3 | 7 | 31 | 30 |
| examples 1–19 | B Z3 Boolean | 9 | 3 | 6 | 21 | 2.4 |
| examples 1–19 | C Z3 Integer | 9 | 3 | 6 | 7.6 | 1.8 |
| examples 1–19 | D CP-SAT Integer | 9 | 3 | 6 | 46 | 32 |
| examples 1–19 | Brute force | 4 | 3 | 1 | 0.03 | 0.02 |
| instances/3-constraint | A CP-SAT | 12 | 0 | 12 | 15 | 16 |
| instances/3-constraint | B Z3 Boolean | 12 | 0 | 12 | 13 | 2.6 |
| instances/3-constraint | C Z3 Integer | 12 | 0 | 12 | 14 | 2.1 |
| instances/3-constraint | D CP-SAT Integer | 12 | 0 | 12 | 15 | 16 |
| instances/4-constraint | A CP-SAT | 11 | 0 | 11 | 31 | 32 |
| instances/4-constraint | B Z3 Boolean | 11 | 0 | 11 | 27 | 2.9 |
| instances/4-constraint | C Z3 Integer | 11 | 0 | 11 | 11 | 2.2 |
| instances/4-constraint | D CP-SAT Integer | 11 | 0 | 11 | 46 | 47 |
| instances/4-constraint-hard | A CP-SAT | 5 | 0 | 5 | 9.4 s | 5.6 s |
| instances/4-constraint-hard | B Z3 Boolean | 2 | 0 | 2 | 43.2 s | 42.5 s |
| instances/4-constraint-hard | D CP-SAT Integer | 5 | 0 | 5 | 10.2 s | 5.7 s |
| instances/5-constraint | A CP-SAT | 10 | 0 | 10 | 46 | 32 |
| instances/5-constraint | B Z3 Boolean | 10 | 0 | 10 | 69 | 5.3 |
| instances/5-constraint | C Z3 Integer | 10 | 0 | 10 | 22 | 3.4 |
| instances/5-constraint | D CP-SAT Integer | 10 | 0 | 10 | 54 | 54 |
| our-instances | A CP-SAT | 5 | 2 | 3 | 15 | 15 |
| our-instances | B Z3 Boolean | 5 | 2 | 3 | 4.6 | 1.5 |
| our-instances | C Z3 Integer | 5 | 2 | 3 | 6.9 | 2.0 |
| our-instances | D CP-SAT Integer | 5 | 2 | 3 | 14 | 16 |
| our-instances | Brute force | 5 | 2 | 3 | 0.02 | 0.01 |

Table 5.5: Uniqueness check on the satisfiable instances: number with exactly one solution, and median first-solve time vs median uniqueness-check time (ms unless marked s).

| File | Approach | Users (plain) | Users (optimised) | Time plain | Time optimised |
| --- | --- | --- | --- | --- | --- |
| instances/3-constraint/0.txt | A CP-SAT | 5 | 3 ← | 15 | 31 |
| instances/3-constraint/0.txt | D CP-SAT Integer | 5 | 3 ← | 15 | 50 |
| instances/3-constraint/1.txt | A CP-SAT | 6 | 2 ← | 15 | 32 |
| instances/3-constraint/1.txt | D CP-SAT Integer | 5 | 2 ← | 15 | 47 |
| instances/3-constraint/2.txt | A CP-SAT | 7 | 2 ← | 15 | 31 |
| instances/3-constraint/2.txt | D CP-SAT Integer | 6 | 2 ← | 16 | 64 |
| instances/3-constraint/3.txt | A CP-SAT | 8 | 2 ← | 15 | 30 |
| instances/3-constraint/3.txt | D CP-SAT Integer | 7 | 2 ← | 15 | 79 |
| instances/3-constraint/6.txt | A CP-SAT | 8 | 3 ← | 15 | 31 |
| instances/3-constraint/6.txt | D CP-SAT Integer | 8 | 3 ← | 15 | 138 |
| instances/3-constraint/8.txt | A CP-SAT | 8 | 2 ← | 15 | 32 |
| instances/3-constraint/8.txt | D CP-SAT Integer | 8 | 2 ← | 15 | 62 |
| instances/3-constraint/10.txt | A CP-SAT | 9 | 3 ← | 14 | 31 |
| instances/3-constraint/10.txt | D CP-SAT Integer | 9 | 3 ← | 15 | 184 |
| instances/3-constraint/11.txt | A CP-SAT | 7 | 3 ← | 15 | 15 |
| instances/3-constraint/11.txt | D CP-SAT Integer | 7 | 3 ← | 15 | 47 |
| instances/3-constraint/13.txt | A CP-SAT | 7 | 3 ← | 15 | 30 |
| instances/3-constraint/13.txt | D CP-SAT Integer | 6 | 3 ← | 15 | 62 |
| instances/3-constraint/16.txt | A CP-SAT | 5 | 2 ← | 15 | 31 |
| instances/3-constraint/16.txt | D CP-SAT Integer | 5 | 2 ← | 15 | 62 |
| instances/3-constraint/18.txt | A CP-SAT | 6 | 2 ← | 14 | 29 |
| instances/3-constraint/18.txt | D CP-SAT Integer | 5 | 2 ← | 15 | 47 |
| instances/3-constraint/19.txt | A CP-SAT | 5 | 2 ← | 15 | 16 |
| instances/3-constraint/19.txt | D CP-SAT Integer | 7 | 2 ← | 15 | 47 |
| instances/4-constraint/0.txt | A CP-SAT | 2 | 2 | 31 | 30 |
| instances/4-constraint/0.txt | D CP-SAT Integer | 3 | 2 ← | 46 | 45 |
| instances/4-constraint/5.txt | A CP-SAT | 3 | 3 | 30 | 30 |
| instances/4-constraint/5.txt | D CP-SAT Integer | 3 | 3 | 29 | 31 |
| instances/4-constraint/6.txt | A CP-SAT | 3 | 3 | 31 | 30 |
| instances/4-constraint/6.txt | D CP-SAT Integer | 3 | 3 | 46 | 31 |
| instances/4-constraint/7.txt | A CP-SAT | 3 | 2 ← | 34 | 31 |
| instances/4-constraint/7.txt | D CP-SAT Integer | 3 | 2 ← | 46 | 61 |
| instances/4-constraint/8.txt | A CP-SAT | 2 | 2 | 31 | 33 |
| instances/4-constraint/8.txt | D CP-SAT Integer | 2 | 2 | 48 | 46 |
| instances/4-constraint/10.txt | A CP-SAT | 2 | 2 | 31 | 33 |
| instances/4-constraint/10.txt | D CP-SAT Integer | 3 | 2 ← | 47 | 47 |
| instances/4-constraint/11.txt | A CP-SAT | 2 | 2 | 30 | 46 |
| instances/4-constraint/11.txt | D CP-SAT Integer | 3 | 2 ← | 47 | 46 |
| instances/4-constraint/12.txt | A CP-SAT | 2 | 2 | 31 | 31 |
| instances/4-constraint/12.txt | D CP-SAT Integer | 3 | 2 ← | 43 | 46 |
| instances/4-constraint/14.txt | A CP-SAT | 2 | 2 | 29 | 31 |
| instances/4-constraint/14.txt | D CP-SAT Integer | 2 | 2 | 46 | 34 |
| instances/4-constraint/18.txt | A CP-SAT | 2 | 2 | 30 | 31 |
| instances/4-constraint/18.txt | D CP-SAT Integer | 3 | 2 ← | 45 | 31 |
| instances/4-constraint/19.txt | A CP-SAT | 2 | 2 | 32 | 31 |
| instances/4-constraint/19.txt | D CP-SAT Integer | 3 | 2 ← | 30 | 30 |
| instances/5-constraint/2.txt | A CP-SAT | 2 | 2 | 59 | 60 |
| instances/5-constraint/2.txt | D CP-SAT Integer | 3 | 2 ← | 64 | 62 |
| instances/5-constraint/3.txt | A CP-SAT | 2 | 2 | 61 | 58 |
| instances/5-constraint/3.txt | D CP-SAT Integer | 3 | 2 ← | 46 | 48 |
| instances/5-constraint/5.txt | A CP-SAT | 3 | 3 | 32 | 30 |
| instances/5-constraint/5.txt | D CP-SAT Integer | 3 | 3 | 44 | 46 |
| instances/5-constraint/6.txt | A CP-SAT | 3 | 2 ← | 47 | 60 |
| instances/5-constraint/6.txt | D CP-SAT Integer | 3 | 2 ← | 75 | 63 |
| instances/5-constraint/9.txt | A CP-SAT | 3 | 2 ← | 61 | 62 |
| instances/5-constraint/9.txt | D CP-SAT Integer | 2 | 2 | 78 | 76 |
| instances/5-constraint/10.txt | A CP-SAT | 3 | 3 | 46 | 46 |
| instances/5-constraint/10.txt | D CP-SAT Integer | 3 | 3 | 62 | 62 |
| instances/5-constraint/12.txt | A CP-SAT | 2 | 2 | 30 | 35 |
| instances/5-constraint/12.txt | D CP-SAT Integer | 3 | 2 ← | 46 | 46 |
| instances/5-constraint/13.txt | A CP-SAT | 2 | 2 | 46 | 47 |
| instances/5-constraint/13.txt | D CP-SAT Integer | 3 | 2 ← | 77 | 62 |
| instances/5-constraint/16.txt | A CP-SAT | 3 | 2 ← | 31 | 41 |
| instances/5-constraint/16.txt | D CP-SAT Integer | 2 | 2 | 31 | 30 |
| instances/5-constraint/18.txt | A CP-SAT | 3 | 3 | 31 | 46 |
| instances/5-constraint/18.txt | D CP-SAT Integer | 3 | 3 | 31 | 46 |
| instances/example1.txt | A CP-SAT | 2 | 1 ← | 15 | 16 |
| instances/example1.txt | D CP-SAT Integer | 2 | 1 ← | 15 | 15 |
| instances/example3.txt | A CP-SAT | 2 | 2 | 15 | 15 |
| instances/example3.txt | D CP-SAT Integer | 2 | 2 | 14 | 14 |
| instances/example5.txt | A CP-SAT | 3 | 3 | 14 | 15 |
| instances/example5.txt | D CP-SAT Integer | 3 | 3 | 15 | 15 |
| instances/example7.txt | A CP-SAT | 5 | 5 | 14 | 15 |
| instances/example7.txt | D CP-SAT Integer | 5 | 5 | 15 | 14 |
| instances/example9.txt | A CP-SAT | 2 | 2 | 32 | 31 |
| instances/example9.txt | D CP-SAT Integer | 3 | 2 ← | 46 | 47 |
| instances/example10.txt | A CP-SAT | 2 | 2 | 31 | 29 |
| instances/example10.txt | D CP-SAT Integer | 2 | 2 | 46 | 47 |
| instances/example11.txt | A CP-SAT | 5 | 4 ← | 148 | 235 |
| instances/example11.txt | D CP-SAT Integer | 4 | 4 | 251 | 2.1 s |
| instances/example16.txt | A CP-SAT | 8 | 5 ← | 6.3 s | 18.1 s |
| instances/example17.txt | A CP-SAT | 19 | 10 ← | 880 | 4.0 s |
| instances/example17.txt | D CP-SAT Integer | 18 | 10 ← | 2.0 s | 18.6 s |
| our-instances/e1-at-least-k-sat.txt | A CP-SAT | 3 | 3 | 16 | 15 |
| our-instances/e1-at-least-k-sat.txt | D CP-SAT Integer | 3 | 3 | 15 | 15 |
| our-instances/e2-max-workload-unique.txt | A CP-SAT | 2 | 2 | 16 | 15 |
| our-instances/e2-max-workload-unique.txt | D CP-SAT Integer | 2 | 2 | 14 | 15 |
| our-instances/e3-conditional-unique.txt | A CP-SAT | 2 | 2 | 13 | 15 |
| our-instances/e3-conditional-unique.txt | D CP-SAT Integer | 2 | 2 | 14 | 14 |
| our-instances/e4-minimise-users-2.txt | A CP-SAT | 2 | 2 | 15 | 15 |
| our-instances/e4-minimise-users-2.txt | D CP-SAT Integer | 2 | 2 | 14 | 15 |
| our-instances/mixed-all-constraints.txt | A CP-SAT | 3 | 3 | 15 | 15 |
| our-instances/mixed-all-constraints.txt | D CP-SAT Integer | 3 | 3 | 15 | 15 |

Table 5.6: Users in the first solution found (plain) vs the optimised solution (E4). Fewer users in 47 of 93 runs (←).
