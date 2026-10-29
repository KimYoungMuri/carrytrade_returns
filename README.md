# B9339 HW4 – Inverse FX returns, Rule of 72, crash-neutral carry

Young Kim (yk3057), B9339 Quantitative Hedge Fund Strategies, Fall 2026.

**Report:** `report/hw4_report.pdf`.

1. **Inverting returns.** Why the return of a currency pair is not the negative of the return in the opposite
   direction, second-order approximations for the mean and variance of the inverse return, and an empirical check on
   daily NZD/JPY and JPY/NZD returns (1999–2010).
2. **Rule of 72.** Exact doubling time vs the Rule of 72, two first-order and two second-order approximations, their
   sensitivity to the interest rate, and the rate at which the Rule of 72 is exact (7.84687%).
3. **Crash-neutral carry (Jurek, 2014).** Derivations behind the put quantity, the lower bound on returns, the
   steeper upside of the delta-hedged overlay, and the unhedged-overlay special case, with a numerical check that
   Equations (2) and (4) agree.

## Inputs

- `hw3.data.carry.FX.dly.xlsx` – the course FX workbook from HW3 (called `hw3.data.FX.dly.xlsx` in the assignment).

## Reproduce

Python 3.12, from the repo root:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
MPLCONFIGDIR=.mplcache .venv/bin/python scripts/run_all.py       # analysis -> outputs/
MPLCONFIGDIR=.mplcache .venv/bin/python scripts/build_report.py  # -> report/hw4_report.pdf
```

## Layout

| Path | Content |
|---|---|
| `src/fxcarry/data.py` | Workbook loading, layout verification, quote standardisation (shared with HW3) |
| `scripts/run_all.py` | Q1 moments and inverse-moment predictions, Q2 approximations and root, Q3 Eq. (2) = Eq. (4) check |
| `scripts/build_report.py` | Builds the PDF from the outputs |
| `outputs/tables/` | `q1_moments.csv`, `q1_predictions.csv`, `q1_rolling.csv`, `q2_table.csv` |
| `outputs/figures/` | `q1_inverse.png`, `q2_errors.png`, `q3_payoffs.png` |
| `outputs/results.json` | All headline numbers |
