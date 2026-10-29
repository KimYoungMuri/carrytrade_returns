"""HW4 analysis: inverse currency returns (Q1), Rule of 72 (Q2), Jurek crash-neutral carry check (Q3).

Usage (from the repo root):  python scripts/run_all.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fxcarry.data import load_dataset  # noqa: E402

OUT, TAB, FIG = ROOT / "outputs", ROOT / "outputs" / "tables", ROOT / "outputs" / "figures"
for d in (OUT, TAB, FIG):
    d.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"mathtext.fontset": "cm", "font.family": "serif", "font.size": 9})
LN2 = np.log(2.0)
res: dict = {}


# ============================================================================ Q1
def moments(r: pd.Series) -> dict:
    """Population (ddof=0) central moments, matching the Taylor expansion of the sample mean of g(R)."""
    mu = r.mean()
    d = r - mu
    return {"mu": mu, "var": (d ** 2).mean(), "m3": (d ** 3).mean(), "m4": (d ** 4).mean(), "n": len(r)}


def predict_inverse(m: dict) -> dict:
    """Moments of R' = 1/(1+R) - 1 from moments of R (delta method around mu)."""
    mu, s2, m3, m4 = m["mu"], m["var"], m["m3"], m["m4"]
    a = 1 + mu
    return {
        "mean_naive": -mu,
        "mean_1st": -mu / a,
        "mean_2nd": -mu / a + s2 / a ** 3,
        "mean_small_mu": -mu + mu ** 2 + s2,
        "mean_4th": -mu / a + s2 / a ** 3 - m3 / a ** 4 + m4 / a ** 5,
        "var_naive": s2,
        "var_2nd": s2 / a ** 4,
        "var_4th": s2 / a ** 4 - 2 * m3 / a ** 5 + (3 * m4 - s2 ** 2) / a ** 6,
    }


ds = load_dataset(ROOT / "hw3.data.carry.FX.dly.xlsx")
q = ds.quotes
jpy_per_nzd = q["NZD"] * q["JPY"]          # (USD per NZD) x (JPY per USD)  = NZD/JPY (JPY price of 1 NZD)
nzd_per_jpy = 1.0 / jpy_per_nzd            # JPY/NZD (NZD price of 1 JPY)
R = pd.DataFrame({"NZDJPY": jpy_per_nzd.pct_change(), "JPYNZD": nzd_per_jpy.pct_change()}).dropna()
assert np.allclose(R["JPYNZD"], 1 / (1 + R["NZDJPY"]) - 1, atol=1e-14)

mom = {k: moments(R[k]) for k in R}
rows = []
for src, tgt in [("NZDJPY", "JPYNZD"), ("JPYNZD", "NZDJPY")]:
    p = predict_inverse(mom[src])
    act = mom[tgt]
    for stat, act_v, keys in [("mean", act["mu"], ["naive", "1st", "2nd", "small_mu", "4th"]),
                              ("var", act["var"], ["naive", "2nd", "4th"])]:
        for k in keys:
            pred = p[f"{stat}_{k}"]
            rows.append({"from": src, "to": tgt, "stat": stat, "approx": k, "actual": act_v, "predicted": pred,
                         "error": pred - act_v, "rel_error": (pred - act_v) / abs(act_v)})
q1 = pd.DataFrame(rows)
q1.to_csv(TAB / "q1_predictions.csv", index=False)

sumtab = pd.DataFrame({k: {"mean": v["mu"], "variance": v["var"], "std": np.sqrt(v["var"]),
                           "skewness": v["m3"] / v["var"] ** 1.5, "kurtosis": v["m4"] / v["var"] ** 2,
                           "ann_mean_260": 260 * v["mu"], "ann_vol_260": np.sqrt(260 * v["var"]), "n": v["n"]}
                       for k, v in mom.items()}).T
sumtab.to_csv(TAB / "q1_moments.csv")
res["q1"] = {"start": str(R.index[0].date()), "end": str(R.index[-1].date()), "n": int(len(R)),
             "first_level_date": str(jpy_per_nzd.index[0].date()),
             "level_first": float(jpy_per_nzd.iloc[0]), "level_last": float(jpy_per_nzd.iloc[-1]),
             "moments": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in mom.items()},
             "sum_of_means": float(mom["NZDJPY"]["mu"] + mom["JPYNZD"]["mu"]),
             "mean_log_return": float(np.log(jpy_per_nzd).diff().dropna().mean()),
             "example_up": {"R": 0.10, "R_inv": 1 / 1.10 - 1}}

# Rolling check: one-year windows, 2nd-order prediction vs actual mean of JPY/NZD
win = 260
roll = []
for end in range(win, len(R) + 1, 20):
    sub = R.iloc[end - win:end]
    m = moments(sub["NZDJPY"])
    p = predict_inverse(m)
    roll.append({"date": sub.index[-1], "actual": sub["JPYNZD"].mean(), "naive": p["mean_naive"],
                 "second": p["mean_2nd"]})
roll = pd.DataFrame(roll).set_index("date")
roll.to_csv(TAB / "q1_rolling.csv")
res["q1"]["rolling_max_abs_err_2nd"] = float((roll["second"] - roll["actual"]).abs().max())
res["q1"]["rolling_max_abs_err_naive"] = float((roll["naive"] - roll["actual"]).abs().max())

fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7))
x = np.linspace(-0.5, 1.0, 400)
ax[0].plot(x, 1 / (1 + x) - 1, label=r"$R'=1/(1+R)-1$")
ax[0].plot(x, -x, "--", label=r"$-R$")
ax[0].plot(x, -x + x ** 2, ":", label=r"$-R+R^2$")
ax[0].set_xlabel(r"$R$ (NZD/JPY return)")
ax[0].set_ylabel(r"$R'$ (JPY/NZD return)")
ax[0].set_ylim(-1, 1.2)
ax[0].axhline(0, color="k", lw=0.4)
ax[0].axvline(0, color="k", lw=0.4)
ax[0].legend(frameon=False, fontsize=7.5)
ax[0].set_title("Inverse return is a convex function of $R$")
ax[1].plot(roll.index, 1e4 * roll["actual"], label="actual JPY/NZD mean", lw=1.6)
ax[1].plot(roll.index, 1e4 * roll["second"], "--", label=r"$-\mu/(1+\mu)+\sigma^2/(1+\mu)^3$", lw=1.0)
ax[1].plot(roll.index, 1e4 * roll["naive"], ":", label=r"naive $-\mu$", lw=1.0)
ax[1].set_ylabel("mean daily return (bp)")
ax[1].set_title("Rolling 260-day windows")
ax[1].legend(frameon=False, fontsize=7)
fig.tight_layout()
fig.savefig(FIG / "q1_inverse.png", dpi=200)
plt.close(fig)


# ============================================================================ Q2
def n_exact(r):
    return LN2 / np.log1p(r)


APPROX = {
    "rule72": ("Rule of 72", lambda r: 0.72 / r),
    "ln2_1st": (r"ln2 / r", lambda r: LN2 / r),
    "069_1st": (r"0.69 / r", lambda r: 0.69 / r),
    "ln2_2nd": (r"ln2 (1/r + 1/2)", lambda r: LN2 * (1 / r + 0.5)),
    "069_2nd": (r"0.69 (1/r + 1/2)", lambda r: 0.69 * (1 / r + 0.5)),
}
grid_pct = [0.5, 1, 2, 3, 4, 5, 6, 7, 7.84687, 8, 9, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100]
rr = np.array(grid_pct) / 100
q2 = pd.DataFrame({"r_pct": grid_pct, "exact": n_exact(rr)})
for k, (_, f) in APPROX.items():
    q2[k] = f(rr)
for k in APPROX:
    q2[f"err_{k}"] = q2[k] - q2["exact"]
q2.to_csv(TAB / "q2_table.csv", index=False)

r72 = brentq(lambda r: 0.72 / r - n_exact(r), 1e-4, 1.0, xtol=1e-15)
q2.loc[q2["r_pct"] == 7.84687, "r_pct"] = 100 * r72
fine = np.linspace(0.001, 1.0, 100_000)
within = {}
for k, (_, f) in APPROX.items():
    rel = np.abs(f(fine) / n_exact(fine) - 1)
    ok = fine[rel <= 0.01]
    within[k] = {"lo": float(ok.min()) if len(ok) else None, "hi": float(ok.max()) if len(ok) else None,
                 "rel_err_at_1pct": float(f(0.01) / n_exact(0.01) - 1),
                 "rel_err_at_10pct": float(f(0.10) / n_exact(0.10) - 1),
                 "rel_err_at_25pct": float(f(0.25) / n_exact(0.25) - 1)}
# Each approximation's zero-error rate (if any) on (0, 1]
zeros = {}
for k, (_, f) in APPROX.items():
    g = f(fine) - n_exact(fine)
    s = np.where(np.sign(g[:-1]) != np.sign(g[1:]))[0]
    zeros[k] = [float(brentq(lambda r: f(r) - n_exact(r), fine[i], fine[i + 1], xtol=1e-15)) for i in s]
res["q2"] = {"r72": float(r72), "n_at_r72": float(n_exact(r72)), "within_1pct": within, "zero_error_rates": zeros,
             "const_implied_at_r72": float(100 * LN2 * r72 / np.log1p(r72)),
             "c_needed": {str(p): float(100 * LN2 * (p / 100) / np.log1p(p / 100)) for p in [1, 2, 5, 8, 10, 15, 20]}}

fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8))
rp = np.linspace(0.005, 0.5, 2000)
styles = {"rule72": "-", "ln2_1st": "--", "069_1st": ":", "ln2_2nd": "-.", "069_2nd": (0, (3, 1, 1, 1, 1, 1))}
for k, (lab, f) in APPROX.items():
    ax[0].plot(100 * rp, f(rp) - n_exact(rp), ls=styles[k], label=lab)
    ax[1].plot(100 * rp, 100 * (f(rp) / n_exact(rp) - 1), ls=styles[k], label=lab)
ax[0].set_ylim(-0.6, 0.2)
ax[1].set_ylim(-20, 4)
for a in ax:
    a.axhline(0, color="k", lw=0.5)
    a.axvline(100 * r72, color="grey", lw=0.5, ls="--")
    a.set_xlabel("interest rate per period, r (%)")
ax[0].set_ylabel(r"$n_{approx}-n_{exact}$ (periods)")
ax[1].set_ylabel("relative error (%)")
ax[0].legend(frameon=False, fontsize=7)
fig.tight_layout()
fig.savefig(FIG / "q2_errors.png", dpi=200)
plt.close(fig)


# ============================================================================ Q3 numerical check of Eq. (2) = Eq. (4)
def gk(S, K, tau, yi, yj, vol):
    """Garman-Kohlhagen put/call on S (units of I per J); domestic rate yi, foreign rate yj (continuous)."""
    d1 = (np.log(S / K) + (yi - yj + 0.5 * vol ** 2) * tau) / (vol * np.sqrt(tau))
    d2 = d1 - vol * np.sqrt(tau)
    call = S * np.exp(-yj * tau) * norm.cdf(d1) - K * np.exp(-yi * tau) * norm.cdf(d2)
    put = K * np.exp(-yi * tau) * norm.cdf(-d2) - S * np.exp(-yj * tau) * norm.cdf(-d1)
    delta_p = -np.exp(-yj * tau) * norm.cdf(-d1)
    return put, call, delta_p


S0, tau, yi, yj, vol = 1.0, 1 / 12, 0.005, 0.045, 0.12
K = 0.97 * S0
P, C, dp = gk(S0, K, tau, yi, yj, vol)
qp = np.exp(yj * tau) / (1 + np.exp(yj * tau) * dp)
ST = np.linspace(0.85, 1.12, 541) * S0


def eq2(ST, qp, dp, P):
    return (np.exp(yj * tau) * (1 - qp * dp) * ST / S0 + qp * np.maximum(K / S0 - ST / S0, 0)
            - np.exp(yi * tau) * ((1 - qp * dp) + qp * P / S0))


r2 = eq2(ST, qp, dp, P)
r4 = qp * np.maximum((ST - K) / S0, 0) - qp * np.exp(yi * tau) * C / S0
r_carry = np.exp(yj * tau) * ST / S0 - np.exp(yi * tau)
q0 = np.exp(yj * tau)
r_unhedged_overlay = eq2(ST, q0, 0.0, P)
assert np.allclose(r2, r4, atol=1e-13)
res["q3"] = {"S0": S0, "K": K, "tau": tau, "yi": yi, "yj": yj, "vol": vol, "put": float(P), "call": float(C),
             "delta_p": float(dp), "q_p": float(qp), "q_p_unhedged": float(q0),
             "max_abs_diff_eq2_eq4": float(np.abs(r2 - r4).max()),
             "floor": float(-qp * np.exp(yi * tau) * C / S0),
             "floor_unhedged_overlay": float(r_unhedged_overlay.min()),
             "slope_ratio": float(qp / np.exp(yj * tau)),
             "slope_ratio_formula": float(1 / (1 + np.exp(yj * tau) * dp))}
fig, ax = plt.subplots(figsize=(5.4, 3.0))
ax.plot(ST / S0, 100 * r_carry, label="unhedged carry", lw=1.2)
ax.plot(ST / S0, 100 * r_unhedged_overlay, "--", label=r"put overlay, $\delta_p=0$ ($q_p=e^{y^j\tau}$)", lw=1.2)
ax.plot(ST / S0, 100 * r4, label=r"delta-hedged overlay, Eq. (4)", lw=1.6)
ax.axvline(K / S0, color="grey", lw=0.5, ls="--")
ax.axhline(0, color="k", lw=0.4)
ax.set_xlabel(r"$S_{t+\tau}/S_t$")
ax.set_ylabel(r"return $\tilde r_{t+\tau}$ (%)")
ax.set_title(rf"$\tau$=1M, $y^j$={yj:.1%}, $y^i$={yi:.1%}, vol={vol:.0%}, $K_p/S_t$={K/S0:.2f}", fontsize=8)
ax.legend(frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(FIG / "q3_payoffs.png", dpi=200)
plt.close(fig)

(OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
print(json.dumps(res, indent=2, default=str))
print(q1.to_string())
print(sumtab.to_string())
print(q2.round(5).to_string())
