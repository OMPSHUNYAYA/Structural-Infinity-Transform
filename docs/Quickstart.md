# ⭐ Shunyaya Structural Infinity Transform (SSIT)

## Quickstart

**Deterministic • Lawful Infinity Objects • Infinity Algebra • SIS Banding • Curvature • Infinity Governance (Zones, Guards, IDO) • Robustness-Validated**

---

## WHAT YOU NEED

Shunyaya Structural Infinity Transform (SSIT) is intentionally minimal, deterministic, and implementation-neutral.

### Requirements
- Python 3.9+
- Standard library only (no external dependencies)

Everything is:
- **deterministic**
- **offline**
- **reproducible**
- **identical across machines**

No randomness.  
No training.  
No probabilistic heuristics.  
No adaptive tuning.

---

## MINIMAL PROJECT LAYOUT (PUBLIC RELEASE)

A review-grade SSIT release contains only the following artifacts:

```
/SSIT  
  scripts/  
    ssit_phase2_robust_v2.py  
    ssit_guard_summary_v1.py  
    ssit_infinity_ops_demo.py  

  outputs/  
    ssit_out_phase2_robust_v2_200k/  
    ssit_out_phase2_robust_v2_1M5/  
    ssit_out_phase2_robust_v2_1M5_shock99/
```

No other scripts or outputs are required for validation, review, or replication.

**Note:**  
In the public release, scan CSV files are **not hosted** due to repository size constraints.  
All scan CSVs are **fully reproducible** using the provided scripts, and their **SHA-256 hashes are recorded in the included reports** for verification.

---

## ENTRY POINTS (scripts/)

### 1. ssit_phase2_robust_v2.py

Authoritative SSIT Phase II engine.

This single script computes:

- infinity coordinate `I(n) = 1 / (1 - H_s(n))`
- posture lane `a(n)`
- structural infinity depth `D_inf(n)`
- SIS banding (THIN / MEDIUM / THICK)
- typed objects (FINSET vs INFSET)
- curvature near infinity `K(n)`
- Infinity Stability Zones
- Infinity Dominance Ordering (IDO)
- guard flag (zone- or shock-triggered)

This script fully subsumes all earlier Phase I and Phase II variants.

---

### 2. ssit_guard_summary_v1.py

Deterministic post-processing and reviewer summary tool.

Consumes a scan CSV and produces:

- zone counts
- guard and shock counts
- top IDO dominators
- largest curvature events
- first INFINITY_PROXIMAL entries

No recomputation.  
Purely derivative.  
Reviewer-friendly.

---

### 3. ssit_infinity_ops_demo.py

Infinity algebra demonstration script.

Produces deterministic examples showing:

- `INF / INF` → finite-class (posture-relative)
- `INF - INF` → zero-class (posture-relative)
- `INF + INF` → infinity with merged posture
- `INF / 0` → undefined (explicitly preserved)

This script is illustrative and is not part of the Phase II engine.

---

## CANONICAL OUTPUTS (outputs/)

The public release contains three active output folders.

### 1. ssit_out_phase2_robust_v2_200k

Early-scale validation run.

Contains:
- Phase II report

Purpose:
- demonstrates non-degenerate behavior at smaller scale
- confirms zones, IDO, and guard logic are not scale artifacts

(The scan CSV is reproducible; its SHA-256 hash is recorded in the report.)

---

### 2. ssit_out_phase2_robust_v2_1M5

Canonical reference run.

Contains:
- Phase II report
- guard summary

Purpose:
- primary citation dataset
- source of all documented counts and examples
- hash-verified, review-grade ground truth

---

### 3. ssit_out_phase2_robust_v2_1M5_shock99

Strict-governance companion run.

Contains:
- Phase II report
- guard summary

Purpose:
- demonstrates deterministic governance tightening
- validates guard behavior under stricter curvature thresholds

---

## ARCHIVE POLICY

The following are intentionally excluded from the public Quickstart:

- earlier Phase I scripts
- Phase II v1 and exploratory robustness scripts
- exploratory scans and intermediate outputs

They are:
- preserved internally
- reproducible from v2
- unnecessary for validation or review

This ensures:
- clarity for reviewers
- zero ambiguity on what is authoritative
- a clean, infrastructure-grade release surface

---

## HOW TO RUN (MINIMAL CANONICAL SET)

All commands are run from the project root (`/SSIT`).

### (1) Canonical Phase II (Robust) v2 Run

```
python scripts/ssit_phase2_robust_v2.py \
  --n_max 1500000 \
  --out_dir outputs/ssit_out_phase2_robust_v2_1M5 \
  --near_eps 0.02 \
  --shock_quantile 0.95
```

Produces:
- scan CSV (local)
- full Phase II report
- SHA-256 receipt

---

### (2) Strict Shock Profile (Optional Companion)

```
python scripts/ssit_phase2_robust_v2.py \
  --n_max 1500000 \
  --out_dir outputs/ssit_out_phase2_robust_v2_1M5_shock99 \
  --near_eps 0.02 \
  --shock_quantile 0.99
```
---

### (3) Reviewer Summary Extraction

```
python scripts/ssit_guard_summary_v1.py \
  --scan_csv outputs/ssit_out_phase2_robust_v2_1M5/ssit_phase2_robust_v2_scan.csv \
  --out_report outputs/ssit_out_phase2_robust_v2_1M5/ssit_guard_summary_v1.txt \
  --top_k 50  
  ```

---

## ONE-MINUTE MENTAL MODEL

Classical mathematics treats infinity as:
- a limit target
- a symbol that collapses distinctions
- a source of indeterminate forms

SSIT treats infinity as:
- a deterministic transform output
- a structured object with posture and depth
- a governed domain with zones, dominance, and guards

SSIT does not change integers.  
SSIT governs how infinity-aligned objects are handled.

---

## CORE SSIT DEFINITIONS (MINIMAL)

- saturated hardness `H_s(n) = d_min(n) / sqrt(n)`
- infinity coordinate `I(n) = 1 / (1 - H_s(n))`

Phase II governance adds:
- posture lane `a(n)`
- depth `D_inf(n)` in `[0,1]`
- SIS bands via depth quantiles
- curvature `K(n) = abs(I(n+1) - 2*I(n) + I(n-1))`
- zones: STABLE_FINITE / TRANSITIONAL / INFINITY_PROXIMAL
- dominance ordering (IDO)
- guard flag

---

## DETERMINISM GUARANTEE

Given identical inputs:
- identical CSV rows
- identical reports
- identical zone and dominance counts
- identical curvature statistics
- identical SHA-256 receipts

No randomness.  
No machine dependence.  
No hidden state.

---

## WHAT SSIT IS — AND IS NOT

SSIT is:
- a deterministic structural infinity transform
- a lawful infinity object and governance system
- conservative with respect to classical arithmetic
- compatible with SSNT

SSIT is not:
- a replacement for limits
- a set-theoretic infinity theory
- a prime predictor
- a factorization tool
- a probabilistic or asymptotic model

---

## ONE-LINE SUMMARY

**Shunyaya Structural Infinity Transform deterministically lifts finite integer closure resistance into governed infinity objects, enabling lawful infinity algebra, typed regimes, SIS banding, curvature observability, dominance ordering, and guard-based interaction — without altering classical mathematics or SSNT observables.**
