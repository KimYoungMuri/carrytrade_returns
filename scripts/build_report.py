"""Build report/hw4_report.pdf from the outputs of scripts/run_all.py.

Usage (from the repo root):  python scripts/build_report.py
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import mathtext
from matplotlib.font_manager import FontProperties
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT, TAB, FIG = ROOT / "outputs", ROOT / "outputs" / "tables", ROOT / "outputs" / "figures"
MATH = OUT / "math"
MATH.mkdir(parents=True, exist_ok=True)
PDF = ROOT / "report" / "hw4_report.pdf"
PDF.parent.mkdir(exist_ok=True)
res = json.loads((OUT / "results.json").read_text())

# ----------------------------------------------------------------------------- styles
AUTHOR = "Young Kim (yk3057)"
plt.rcParams.update({"mathtext.fontset": "cm"})
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="Times-Roman", fontSize=10.5, leading=15, spaceAfter=5)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=9, leading=12.5, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Times-Bold", fontSize=13.5, leading=17, spaceBefore=10, spaceAfter=5)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Times-Bold", fontSize=11.2, leading=15, spaceBefore=7, spaceAfter=3)
TITLE = ParagraphStyle("title", parent=BODY, fontSize=17, leading=21, alignment=TA_CENTER, spaceAfter=2)
CENTER = ParagraphStyle("center", parent=BODY, alignment=TA_CENTER, spaceAfter=1)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10.5, spaceAfter=0)

story: list = []
MARGIN = 0.85 * inch
W_AVAIL = letter[0] - 2 * MARGIN
_PARSER = mathtext.MathTextParser("path")


def M(tex: str, size: float = 10.5) -> str:
    """Inline math: render with mathtext and return a baseline-aligned <img> tag."""
    s = f"${tex}$"
    fp = FontProperties(size=size)
    key = hashlib.md5(f"{s}|{size}".encode()).hexdigest()[:16]
    path = MATH / f"{key}.png"
    if not path.exists():
        mathtext.math_to_image(s, str(path), prop=fp, dpi=400)
    _, _, depth, _, _ = _PARSER.parse(s, dpi=72, prop=fp)
    w, h = PILImage.open(path).size
    return f'<img src="{path}" width="{w / 400 * 72:.2f}" height="{h / 400 * 72:.2f}" valign="{-depth:.2f}"/>'


def P(text, style=BODY):
    story.append(Paragraph(text, style))


def h1(t):
    story.append(Paragraph(t, H1))


def h2(t):
    story.append(Paragraph(t, H2))


def eq(tex, size=12.5):
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, "$" + tex.replace(r"\frac", r"\dfrac") + "$", fontsize=size)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", pad_inches=0.03, transparent=True)
    plt.close(fig)
    buf.seek(0)
    w, h = PILImage.open(buf).size
    buf.seek(0)
    wpt, hpt = w / 300 * 72, h / 300 * 72
    max_w = W_AVAIL - 24
    if wpt > max_w:
        wpt, hpt = max_w, hpt * max_w / wpt
    img = Image(buf, width=wpt, height=hpt)
    img.hAlign = "CENTER"
    story.append(Spacer(1, 3))
    story.append(img)
    story.append(Spacer(1, 6))


def figure(name, caption, width=W_AVAIL * 0.95):
    p = FIG / name
    w, h = PILImage.open(p).size
    img = Image(str(p), width=width, height=width * h / w)
    story.append(KeepTogether([img, Spacer(1, 2), Paragraph(caption, CAP), Spacer(1, 8)]))


def table(rows, header, col_widths=None, caption=None, font=8):
    cell = ParagraphStyle(f"cell{font}", parent=CELL, fontSize=font, leading=font + 3)
    data = [[Paragraph(str(h), cell) for h in header]] + [[Paragraph(str(c), cell) for c in r] for r in rows]
    if col_widths and sum(col_widths) > W_AVAIL:
        col_widths = [c * W_AVAIL / sum(col_widths) for c in col_widths]
    t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.9, colors.black), ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.9, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2)]))
    block = ([Paragraph(caption, CAP), Spacer(1, 2)] if caption else []) + [t, Spacer(1, 9)]
    story.append(KeepTogether(block))


def f5(x):
    return f"{x:.5f}"


def sci(x):
    """5-significant-digit scientific notation as inline math, e.g. 6.94248 x 10^-5."""
    mant, ex = f"{x:.5e}".split("e")
    return M(rf"{mant}\times10^{{{int(ex)}}}")


# ----------------------------------------------------------------------------- numbers
q1r, q2r, q3r = res["q1"], res["q2"], res["q3"]
m_nj, m_jn = q1r["moments"]["NZDJPY"], q1r["moments"]["JPYNZD"]
pred = pd.read_csv(TAB / "q1_predictions.csv")
mom = pd.read_csv(TAB / "q1_moments.csv", index_col=0)
q2t = pd.read_csv(TAB / "q2_table.csv")
W1 = q2r["within_1pct"]
r72 = q2r["r72"]


def pr(src, stat, approx):
    return pred[(pred["from"] == src) & (pred.stat == stat) & (pred.approx == approx)].iloc[0]


# common inline symbols
R_, Rp, mu, s2 = M("R"), M("R'"), M(r"\mu"), M(r"\sigma^2")
St, STt, Kp, qp, dp = M("S_t"), M(r"S_{t+\tau}"), M("K_p"), M("q_p"), M(r"\delta_p")
eyj, eyi = M(r"e^{y^j\tau}"), M(r"e^{y^i\tau}")

# ============================================================================= title
P("B9339 Quantitative Hedge Fund Strategies", CENTER)
P("Homework 4", TITLE)
P(AUTHOR, CENTER)
P("Prof. Achilles Venetoulias, Fall 2026 &nbsp;&nbsp; October 29, 2026", CENTER)
story.append(Spacer(1, 6))

# ============================================================================= Q1
h1("1. Inverting returns")
P(f"<b>Notation.</b> Let {M('X_t')} be the price of one unit of currency A in units of currency B (for NZD/JPY: "
  f"JPY per NZD). The simple return in this direction is {M('R = X_{t+1}/X_t - 1')}. The opposite direction has price "
  f"{M('Y_t = 1/X_t')} (NZD per JPY) and return {Rp}.")
h2("(a) Why the return is not inverted")
eq(r"R'=\frac{Y_{t+1}}{Y_t}-1=\frac{X_t}{X_{t+1}}-1=\frac{1}{1+R}-1=-\frac{R}{1+R}=-R+R^2-R^3+\cdots")
P(f"Prices invert exactly ({M('Y = 1/X')}), but returns do not: {Rp} is neither {M('1/R')} nor {M('-R')}. Each return "
  "is measured relative to its own starting value, in its own numeraire. When A appreciates by 10% against B, B "
  f"depreciates by only {M('1 - 1/1.1 = 9.09091')}% against A, because the 10% is a fraction of the (smaller) starting "
  "price of A while the 9.09% is a fraction of the (larger) starting price of B. The function "
  f"{M('g(R) = 1/(1+R) - 1')} is convex, so")
eq(r"R+R'=\frac{R^2}{1+R}\geq 0\quad\Rightarrow\quad E[R]+E[R']=E\left[\frac{R^2}{1+R}\right]>0")
P("Both sides of the pair can therefore have a positive expected return at the same time (Jensen's inequality, the "
  "&lsquo;Siegel paradox&rsquo;). This is why carry-trade returns must be computed in the direction actually held "
  f"and in the investor's numeraire. Only log returns are antisymmetric: {M(r'\ln(1+R^{\prime}) = -\ln(1+R)')}.")

h2("(b) Approximate moments of the inverse return")
P(f"Only {M(r'\mu = E[R]')} and {M(r'\sigma^2 = \mathrm{Var}[R]')} are known, so expand {M('g(R)')} to second order "
  f"around {mu} (the delta method). The derivatives are {M(r'g^{\prime}(R) = -(1+R)^{-2}')}, "
  f"{M(r'g^{\prime\prime}(R) = 2(1+R)^{-3}')} and {M(r'g^{\prime\prime\prime}(R) = -6(1+R)^{-4}')}:")
eq(r"g(R)\approx g(\mu)+g'(\mu)(R-\mu)+\frac{1}{2}g''(\mu)(R-\mu)^2")
P(f"Taking expectations (using {M(r'E[R-\mu] = 0')} and {M(r'E[(R-\mu)^2] = \sigma^2')}) and variances (keeping the "
  "linear term) gives:")
eq(r"E[R']\approx-\frac{\mu}{1+\mu}+\frac{\sigma^2}{(1+\mu)^3}\;\approx\;-\mu+\mu^2+\sigma^2,"
   r"\qquad \mathrm{Var}[R']\approx\frac{\sigma^2}{(1+\mu)^4}\;\approx\;\sigma^2")
P(f"The small-{mu} forms follow from {M(r'1/(1+\mu) \approx 1-\mu')}. The key point is that the expected inverse "
  f"return is not {M(r'-\mu')} but {M(r'-\mu')} plus a variance (convexity) term. For daily FX returns, {s2} is of the "
  f"same order of magnitude as {mu}, so this term is not negligible; volatility is essentially unchanged by inversion. "
  f"For the empirical check I also report the next terms. They need the third and fourth central moments {M('m_3')} "
  f"and {M('m_4')}, which (b) does not assume are known:")
eq(r"E[R']\approx-\frac{\mu}{1+\mu}+\frac{\sigma^2}{(1+\mu)^3}-\frac{m_3}{(1+\mu)^4}+\frac{m_4}{(1+\mu)^5}", size=12.5)
eq(r"\mathrm{Var}[R']\approx\frac{\sigma^2}{(1+\mu)^4}-\frac{2m_3}{(1+\mu)^5}+\frac{3m_4-\sigma^4}{(1+\mu)^6}", size=12.5)

h2("(c) Empirical check: NZD/JPY and JPY/NZD")
P("The workbook (hw3.data.carry.FX.dly.xlsx, the HW3 file) quotes NZD as USD per NZD and JPY as JPY per USD. "
  "The cross rates are therefore")
eq(r"X_t^{NZD/JPY}=S_t^{NZD}\,[\mathrm{USD/NZD}]\times S_t^{JPY}\,[\mathrm{JPY/USD}]\ \ (\mathrm{JPY\ per\ NZD}),"
   r"\qquad X_t^{JPY/NZD}=1/X_t^{NZD/JPY}\ \ (\mathrm{NZD\ per\ JPY})", size=11.5)
P(f"with daily returns {M('R_t = X_t/X_{t-1} - 1')} for both series ({q1r['start']} to {q1r['end']}, {q1r['n']} "
  f"returns; spot from {q1r['level_first']:.5f} to {q1r['level_last']:.5f} JPY per NZD). Moments are population "
  f"moments (the mean of {M(r'(R-\mu)^k')}), which is what the Taylor expansion of the sample mean of {M('g(R)')} uses. "
  f"The JPY/NZD series computed directly from {M('1/X')} matches {M('1/(1+R) - 1')} to {M('10^{-14}')}.")
rows = []
for k, lab in [("NZDJPY", "NZD/JPY (JPY per NZD)"), ("JPYNZD", "JPY/NZD (NZD per JPY)")]:
    m = mom.loc[k]
    rows.append([lab, f"{m['mean']:.5e}", f"{m['variance']:.5e}", f5(m['std']), f5(m['skewness']), f5(m['kurtosis']),
                 f5(m['ann_mean_260']), f5(m['ann_vol_260'])])
table(rows, ["Series", "mean (daily)", "variance (daily)", "std (daily)", "skewness", "kurtosis",
             "mean &times; 260", "std &times; &radic;260"],
      [104, 60, 64, 50, 52, 50, 52, 62], caption="Table 1: Sample moments of the daily returns in both directions.")
P(f"Both directions have a <i>positive</i> average return. Their sum is {sci(q1r['sum_of_means'])}, almost exactly "
  f"{M(r'\sigma^2')} = {sci(m_nj['var'])}, while the mean log return is only {sci(q1r['mean_log_return'])} per day. "
  "This is the convexity effect from (a).")

rows = []
labels = {"naive": M(r"-\mu\ /\ \sigma^2", 8), "1st": M(r"-\mu/(1+\mu)", 8),
          "2nd": "(b) second order",
          "small_mu": "(b) " + M(r"-\mu+\mu^2+\sigma^2", 8), "4th": "with " + M("m_3, m_4", 8) + " terms"}
for src, tgt in [("NZDJPY", "JPYNZD"), ("JPYNZD", "NZDJPY")]:
    for stat in ["mean", "var"]:
        sub = pred[(pred["from"] == src) & (pred.stat == stat)]
        for _, r in sub.iterrows():
            rows.append([f"{src[:3]}/{src[3:]} &rarr; {tgt[:3]}/{tgt[3:]}",
                         M("E[R']", 8) if stat == "mean" else M(r"\mathrm{Var}[R']", 8),
                         labels[r.approx], f"{r.actual:.5e}", f"{r.predicted:.5e}", f"{r.error:.5e}",
                         f"{100 * r.rel_error:.5f}%"])
table(rows, ["Predict", "Moment", "Approximation (mean / variance)", "Actual", "Predicted", "Error", "Rel. error"],
      [92, 40, 150, 58, 58, 58, 56],
      caption=f"Table 2: Moments of the inverse series predicted from the moments of the other direction. Predicted = "
              f"formula from (b) evaluated at the sample {mu} and {s2} (and {M('m_3')}, {M('m_4')} in the last rows). "
              "Error = Predicted &minus; Actual.", font=7.6)
e_n, e_2 = pr("NZDJPY", "mean", "naive").error, pr("NZDJPY", "mean", "2nd").error
P(f"<b>Do the data agree?</b> Yes. For the mean, the naive guess {M(r'-\mu')} has the wrong sign (error "
  f"{sci(e_n)}, about {abs(e_n) * 260 * 100:.5f}% per year). The second-order formula from (b) cuts the error to "
  f"{sci(e_2)}, removing {100 * (1 - abs(e_2 / e_n)):.5f}% of the naive error, and the small-{mu} version is just as "
  "good. The remaining relative gap of about 1.4% comes from the third and fourth moments: daily NZD/JPY returns have "
  f"negative skewness ({mom.loc['NZDJPY','skewness']:.5f}, the carry-crash signature) and kurtosis above 10, so the "
  f"higher-order terms are not negligible. Adding them reduces the error to about {M('10^{-9}')}. For the variance, (b) "
  f"predicts {M(r'\mathrm{Var}[R^{\prime}] \approx \sigma^2')}, which is right to about 1.3%. The factor "
  f"{M(r'(1+\mu)^{-4}')} is practically 1, and the residual is the {M('-2m_3')} skewness term (inversion flips the "
  f"sign of skewness: {mom.loc['NZDJPY','skewness']:.5f} vs {mom.loc['JPYNZD','skewness']:.5f}). Figure 1 repeats the "
  "comparison on rolling one-year windows: the largest error of the second-order formula is "
  f"{sci(q1r['rolling_max_abs_err_2nd'])}, vs {sci(q1r['rolling_max_abs_err_naive'])} for {M(r'-\mu')}.")
figure("q1_inverse.png", f"Figure 1: Left, the inverse return as a function of {M('R', 9)}, with the linear "
       f"({M('-R', 9)}) and quadratic approximations. Right, mean daily JPY/NZD return over rolling 260-day windows "
       f"(every 20 days): actual vs the second-order prediction and {M(r'-\mu', 9)}, both computed from the NZD/JPY "
       "moments in the same window.")
story.append(PageBreak())

# ============================================================================= Q2
h1("2. The Rule of 72")
P(f"With discrete compounding at rate {M('r')} per period, doubling requires {M('(1+r)^n = 2')}, so the exact answer is")
eq(r"n^{*}(r)=\frac{\ln 2}{\ln(1+r)}")
P(f"<b>First-order approximations.</b> Using {M(r'\ln(1+r) \approx r')} gives {M(r'n \approx \ln 2/r = 69.3147/(100r)')} "
  f"(&lsquo;Rule of 69.3&rsquo;), or, with {M(r'\ln 2 \approx 0.69')}, {M(r'n \approx 69/(100r)')}. Since "
  f"{M(r'\ln(1+r) < r')}, both are always too short.")
P(f"<b>My two approximations (second order).</b> The series "
  f"{M(r'1/\ln(1+r) = 1/r + 1/2 - r/12 + r^2/24 - \cdots')} (equivalently {M(r'\ln(1+r) \approx r - r^2/2')} and "
  f"{M(r'1/(1-r/2) \approx 1 + r/2')}) gives:")
eq(r"\mathrm{(iv)}\ \ n\approx\ln 2\left(\frac{1}{r}+\frac{1}{2}\right)=\frac{69.3147+34.6574\,r}{100\,r},"
   r"\qquad\mathrm{(v)}\ \ n\approx0.69\left(\frac{1}{r}+\frac{1}{2}\right)=\frac{69+34.5\,r}{100\,r}")
P(f"Approximation (iv) is the better one: its error is about {M(r'\ln 2 \cdot r/12 > 0')}, under 0.005 periods for "
  f"{M(r'r \leq 9\%')}. Approximation (v) loses {M('0.00315(1/r + 1/2)')} periods from rounding ln 2 down to 0.69, "
  f"so it is worse at low rates. This rounding loss happens to offset the positive {M('r/12')} error, cancelling "
  f"exactly at {M('r')} = {100*q2r['zero_error_rates']['069_2nd'][0]:.5f}%, so (v) is slightly more accurate above "
  f"roughly 18%. Form (iv) also explains the Rule of 72: it is a &lsquo;rule of N&rsquo; with "
  f"{M('N(r) = 69.3147 + 34.6574r')}, which equals 72 when {M(r'r \approx 7.75\%')}. The number 72 is the constant "
  "that is right for typical interest rates (and it is divisible by 2, 3, 4, 6, 8, 9 and 12).")
h2("(a) Sensitivity to the interest rate")
P(f"I evaluated all five approximations and the exact {M('n^*')} on a grid of {M('r')} from 0.1% to 100% (Python, "
  f"numpy). Table 3 shows the error {M(r'n_{\mathrm{approx}} - n^*')} in periods, and Figure 2 plots the absolute and "
  "relative errors.")
cols = ["rule72", "ln2_1st", "069_1st", "ln2_2nd", "069_2nd"]
rows = []
for _, r in q2t.iterrows():
    rows.append([f"{r.r_pct:.5f}%", f5(r.exact), f5(r["rule72"])] + [f5(r[f'err_{c}']) for c in cols])
hdr = [M("r", 8), M("n^*", 8), M("72/(100r)", 8)] + ["error " + M(t, 8) for t in
       ["72/(100r)", r"\ln2/r", "0.69/r", r"\ln2(1/r+1/2)", "0.69(1/r+1/2)"]]
table(rows, hdr, [52, 52, 52, 60, 58, 58, 72, 72],
      caption=f"Table 3: Doubling periods and approximation errors ({M(r'n_{\mathrm{approx}} - n^*', 9)}, in periods). "
              f"The row {M('r', 9)} = {100*r72:.5f}% is where the Rule of 72 is exact.", font=7.6)
rows = [[lab, f"{100*W1[k]['rel_err_at_1pct']:.5f}%", f"{100*W1[k]['rel_err_at_10pct']:.5f}%",
         f"{100*W1[k]['rel_err_at_25pct']:.5f}%", f"{100*W1[k]['lo']:.5f}% to {100*W1[k]['hi']:.5f}%"]
        for k, lab in [("rule72", "(i) " + M("72/(100r)", 8)), ("ln2_1st", "(ii) " + M(r"\ln2/r", 8)),
                       ("069_1st", "(iii) " + M("0.69/r", 8)), ("ln2_2nd", "(iv) " + M(r"\ln2(1/r+1/2)", 8)),
                       ("069_2nd", "(v) " + M("0.69(1/r+1/2)", 8))]]
table(rows, ["Approximation", "rel. error at r = 1%", "rel. error at r = 10%", "rel. error at r = 25%",
             "range of r with |rel. error| &le; 1%"], [110, 70, 70, 70, 130],
      caption=f"Table 4: Relative error {M(r'n_{\mathrm{approx}}/n^* - 1', 9)}. The search grid starts at r = 0.1%.")
P(f"<b>Findings.</b> The first-order rules (ii) and (iii) have an almost constant absolute error of about "
  f"&minus;0.34 periods ({M(r'-\ln 2/2 = -0.34657')} in the limit), so they are fine only when {M('n')} is large "
  f"({M('r')} below about 2%), and their relative error grows roughly like {M('-r/2')}. The Rule of 72 overestimates "
  f"for {M('r')} &lt; {100*r72:.5f}% (by 2.33928 periods at 1%) and underestimates above it; it is within 1% only for "
  f"{M('r')} between {100*W1['rule72']['lo']:.5f}% and {100*W1['rule72']['hi']:.5f}%. The second-order rules (iv) and "
  "(v) are within 1% for every rate up to 41% and 52% respectively, so they are much less sensitive to the rate. The "
  f"rule-of-N constant needed for an exact answer rises with {M('r')}: "
  + ", ".join(f"{k}%: {v:.5f}" for k, v in q2r["c_needed"].items()) + ".")
figure("q2_errors.png", "Figure 2: Absolute (left, periods) and relative (right) errors of the five approximations; "
       "the dashed vertical line marks the rate at which the Rule of 72 is exact.")
h2("(b) Rate at which the Rule of 72 is exact")
P(f"Solve {M(r'72/(100r) = \ln 2/\ln(1+r)')}, i.e. {M(r'h(r) = 0.72\ln(1+r) - r\ln 2 = 0')}, with Brent's method "
  f"(tolerance {M('10^{-15}')}). Since {M('h(0) = 0')}, {M(r'h^{\prime}(0) = 0.72 - \ln 2 > 0')} and {M('h')} is "
  "strictly concave, there is exactly one positive root:")
eq(rf"r^{{*}}={r72:.7f}\ \ ({100*r72:.5f}\%),\qquad n^{{*}}={q2r['n_at_r72']:.5f}\ \mathrm{{periods}}")
P("At this rate the Rule of 72 matches the true doubling time. It is closest to the truth for rates near 8%, which is "
  "why practitioners chose 72.")
story.append(PageBreak())

# ============================================================================= Q3
h1("3. FX carry: Jurek (2014), crash-neutral carry")
P(f"<b>Setup</b> (Jurek's notation). The trader is long the high-yield currency J, funded in I. {M('S_t^{ji}')} is "
  f"the price of J in units of I, and {M('y^j')}, {M('y^i')} are the interest rates; below, {St} and {STt} stand for "
  f"{M('S^{ji}')}. Per unit of capital the trader holds {M(r'(1 - q_p\delta_p)')} units of J exposure: 1 unit for the "
  f"carry trade plus {M(r'-q_p\delta_p > 0')} units to hedge the puts' (negative) delta. They buy {qp} puts with "
  f"strike {Kp} at price {M(r'P_t(K_p,\tau)')}, and borrow everything in I. Equation (2) is:")
eq(r"\tilde r_{t+\tau}=e^{y^j\tau}(1-q_p\delta_p)\frac{S_{t+\tau}}{S_t}+q_p\max\left(\frac{K_p}{S_t}-\frac{S_{t+\tau}}{S_t},0\right)"
   r"-e^{y^i\tau}\left((1-q_p\delta_p)+q_p\frac{P_t(K_p,\tau)}{S_t}\right)", size=11.5)

h2(f"(a) The expression for {M('q_p', 11.2)} in Equation (3)")
P(f"The goal is a position with <i>no</i> exposure to {STt} below the strike. For {M(r'S_{t+\tau} < K_p')} the put is "
  f"in the money, and the terms of (2) that depend on {STt} are")
eq(r"\left[e^{y^j\tau}(1-q_p\delta_p)-q_p\right]\frac{S_{t+\tau}}{S_t}")
P(f"The first part is the long J holding, which has grown at the J interest rate to "
  f"{M(r'e^{y^j\tau}(1 - q_p\delta_p)')} units. The second part is the {qp} puts, each gaining one unit per unit fall "
  "in S. Setting the bracket to zero (one put per unit of terminal J holding) and solving gives (3):")
eq(r"q_p=e^{y^j\tau}(1-q_p\delta_p)\;\Rightarrow\;q_p\left(1+e^{y^j\tau}\delta_p\right)=e^{y^j\tau}"
   r"\;\Rightarrow\;q_p=\frac{e^{y^j\tau}}{1+e^{y^j\tau}\delta_p}")
P(f"The equation is circular. The puts have a negative delta, so {M(r'-q_p\delta_p')} extra units of J are bought to "
  f"keep the initial exposure equal to one unit of carry: the total delta is "
  f"{M(r'(1 - q_p\delta_p) + q_p\delta_p = 1')}. But those extra J units also need put protection, which needs more "
  f"delta hedging, and so on. Solving the fixed point sums this geometric series:")
eq(r"q_p=e^{y^j\tau}\sum_{k=0}^{\infty}\left(-e^{y^j\tau}\delta_p\right)^k")
P(f"The Garman&ndash;Kohlhagen put delta is {M(r'\delta_p = -e^{-y^j\tau}N(-d_1)')}, so "
  f"{M(r'-1 < e^{y^j\tau}\delta_p < 0')}; hence the series converges and {qp} is finite and larger than {eyj}.")

h2("(b) Why Equation (4) shows the return is bounded from below")
P(f"<b>Step 1.</b> By (3), {M(r'e^{y^j\tau}(1 - q_p\delta_p) = q_p')}, so the first two terms of (2) combine:")
eq(r"q_p\,\frac{S_{t+\tau}+\max(K_p-S_{t+\tau},0)}{S_t}=q_p\max\left(\frac{K_p}{S_t},\frac{S_{t+\tau}}{S_t}\right)")
P("which is the first line of (4). <b>Step 2.</b> FX put-call parity, "
  f"{M(r'P_t = C_t - S_t e^{-y^j\tau} + K_p e^{-y^i\tau}')}, together with "
  f"{M(r'1 - q_p\delta_p = q_p e^{-y^j\tau}')}, turns the funding cost into")
eq(r"e^{y^i\tau}\left(q_pe^{-y^j\tau}+q_p\frac{C_t-S_te^{-y^j\tau}+K_pe^{-y^i\tau}}{S_t}\right)"
   r"=q_p\frac{K_p}{S_t}+q_p\,e^{y^i\tau}\frac{C_t(K_p,\tau)}{S_t}")
P("<b>Step 3.</b> Subtracting gives the second line of (4):")
eq(r"\tilde r_{t+\tau}=q_p\max\left(\frac{S_{t+\tau}-K_p}{S_t},0\right)-q_p\,e^{y^i\tau}\frac{C_t(K_p,\tau)}{S_t}"
   r"\;\geq\;-q_p\,e^{y^i\tau}\frac{C_t(K_p,\tau)}{S_t}")
P(f"Economically, the crash-neutral trade is just {qp} call options on J, bought with borrowed I. The first term is an "
  "option payoff, so it can never be negative. The second term is fixed at time t: the call premium plus interest on "
  "the borrowing. So the worst-case return is known when the trade is opened, no matter how far J crashes. Unhedged "
  f"carry, {M(r'e^{y^j\tau}S_{t+\tau}/S_t - e^{y^i\tau}')}, has no such floor. Numerical check (Figure 3: one-month "
  f"options, {M('y^j')} = 4.5%, {M('y^i')} = 0.5%, 12% volatility, {M('K_p/S_t = 0.97')}, Garman&ndash;Kohlhagen "
  f"prices): {M(rf'\delta_p = {q3r['delta_p']:.5f}')}, {M(rf'q_p = {q3r['q_p']:.5f}')}, floor = {q3r['floor']:.5f}. "
  f"Equations (2) and (4) agree to {sci(q3r['max_abs_diff_eq2_eq4'])} at every terminal rate.")

h2("(c) Why the payoff is steeper than unhedged carry above the strike")
P(f"For {M(r'S_{t+\tau} > K_p')}, (4) is linear in {M(r'S_{t+\tau}/S_t')} with slope {qp}. The slope of unhedged "
  f"carry is {eyj}. The ratio is")
eq(r"\frac{q_p}{e^{y^j\tau}}=\frac{1}{1+e^{y^j\tau}\delta_p}>1\quad\mathrm{since}\quad\delta_p<0")
P(f"which is Jurek's &lsquo;magnified by a factor {M(r'q_p/\exp(y^j\tau)')}&rsquo; ({q3r['slope_ratio']:.5f} in the "
  f"example). The reason is the delta hedge. The trader bought {M(r'-q_p\delta_p')} extra units of J to offset the "
  "puts' negative delta at inception. If J ends above the strike, the puts expire worthless, but the extra J units "
  "are still held and add upside. In effect, the hedge turns put-protected carry into levered call exposure. The cost "
  f"is a lower floor than an unhedged put overlay ({q3r['floor']:.5f} vs {q3r['floor_unhedged_overlay']:.5f} in the "
  "example), because more options are bought and the extra position must also be protected.")
figure("q3_payoffs.png", f"Figure 3: Terminal return vs {M(r'S_{t+\tau}/S_t', 9)} for unhedged carry, carry plus an "
       f"unhedged put overlay ({M(r'\delta_p = 0', 9)}), and the delta-hedged crash-neutral trade of Eq. (4). The "
       "dashed line marks the strike.", width=W_AVAIL * 0.72)

h2(f"(d) Unhedged overlay: set {M(r'\delta_p = 0', 11.2)}")
P(f"{dp} enters (2) only through the extra {M(r'-q_p\delta_p')} units of J bought to hedge the option delta. Not "
  f"hedging the overlay means buying none, i.e. setting {M(r'\delta_p = 0')}. Then (3) gives "
  f"{M(r'q_p = e^{y^j\tau}')}, exactly one put per unit of terminal J holding (principal plus interest), and (2) "
  "becomes a carry trade with a protective put:")
eq(r"\tilde r_{t+\tau}=e^{y^j\tau}\max\left(\frac{S_{t+\tau}}{S_t},\frac{K_p}{S_t}\right)-e^{y^i\tau}\left(1+e^{y^j\tau}\frac{P_t(K_p,\tau)}{S_t}\right)")
P(f"This is still bounded below, but above the strike its slope is {eyj}, the same as plain carry (magnification "
  "factor 1), and it sits below plain carry by the financed put premium. As the strike goes to 0, the put becomes "
  f"worthless ({M(r'P_t \to 0')}), its delta goes to 0 ({M(r'N(-d_1) \to 0')}), and the put payoff is 0. The hedge "
  f"therefore disappears automatically, {M(r'q_p \to e^{y^j\tau}')}, and (2) reduces to the unhedged carry return "
  f"{M(r'e^{y^j\tau}S_{t+\tau}/S_t - e^{y^i\tau}')}. In other words, {M(r'\delta_p = 0')} with {M('K_p > 0')} is the "
  f"put-protected trade, and {M(r'K_p \to 0')} recovers the original carry trade as a special case. As Jurek notes, "
  f"if I is not the investor's home currency h, each return is converted by multiplying by "
  f"{M(r'S_{t+\tau}^{ih}/S_t^{ih}')}.")

h1("Reproducibility")
P("Code: https://github.com/KimYoungMuri/carrytrade_returns. scripts/run_all.py runs all computations (tables in "
  "outputs/tables, figures in outputs/figures) and scripts/build_report.py builds this PDF. The data loader "
  "(src/fxcarry/data.py) is the verified HW3 loader.", CAP)


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8.5)
    canvas.drawString(MARGIN, 0.5 * inch, f"B9339 HW4, {AUTHOR}")
    canvas.drawRightString(letter[0] - MARGIN, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(str(PDF), pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=0.8 * inch,
                        bottomMargin=0.8 * inch, title="B9339 Homework 4", author=AUTHOR)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"wrote {PDF}")
