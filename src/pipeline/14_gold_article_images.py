"""
Gold 14: the three article images the strip plot can't do on its own.

The ICB strip plot (10_gold_chart.py) carries the argument, but it sits two
thirds of the way down the piece and it is the wrong shape for two other
jobs: opening the article, and surviving as a 1200x630 social card at
thumbnail size. This writes:

  1. wirral_row.png     - the lede, drawn. One council, 42 neighbourhoods,
                          25 years of healthy life, with the confidence
                          intervals of the two extremes shown so the
                          "still 22 years apart at the cautious ends"
                          sentence is visible rather than asserted.
  2. null_scatter.png   - the finding, drawn. Every neighbourhood against
                          its main hospital's 18-week share. The horizontal
                          banding is real and worth seeing: a neighbourhood
                          inherits its trust's single figure, so each band
                          is one trust's catchment. The decile means make
                          the flatness legible.
  3. social_card.png    - 1200x630 for Medium's featured image / OG card.
                          Eight of the 36 ICBs, evenly spaced through the
                          ordered list, so the band-vs-row comparison
                          survives at thumbnail size.

Every number drawn here comes from the Gold tables, not from the prose.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR  # noqa: E402

OUT = GOLD_DIR / "04_chart"
OUT.mkdir(parents=True, exist_ok=True)

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#9a9891", "#e6e4de"
ACCENT, BAND = "#2a78d6", "#eb6834"
PAPER = "#fcfcfb"

SHORT_NAME = {
    "Bath and North East Somerset, Swindon and Wiltshire": "Bath & NE Somerset, Swindon & Wilts",
    "Bristol, North Somerset and South Gloucestershire": "Bristol, N Somerset & S Glos",
    "Leicester, Leicestershire and Rutland": "Leicester, Leics & Rutland",
    "Cornwall and the Isles of Scilly": "Cornwall & Isles of Scilly",
}


def tidy(ax, spines=("top", "right", "left")) -> None:
    for s in spines:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0)


def wirral_row(m: pd.DataFrame) -> None:
    """The opening paragraph, drawn. One row, 42 neighbourhoods, both ends named."""
    d = m[(m.lad_name == "Wirral") & (m.sex == "Male")].sort_values("hle")
    lo, hi = d.iloc[0], d.iloc[-1]

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    # the span itself, then the neighbourhoods on top of it
    ax.plot([lo.hle, hi.hle], [0, 0], color=GRID, lw=2.4, zorder=1, solid_capstyle="round")
    ax.scatter(d.hle, np.zeros(len(d)), s=68, color=MUTED, alpha=0.8, lw=0, zorder=3)
    for r, c in [(lo, BAND), (hi, ACCENT)]:
        ax.plot([r.hle_lci, r.hle_uci], [0, 0], color=c, lw=3.4, alpha=0.3,
                zorder=2, solid_capstyle="butt")
        ax.scatter([r.hle], [0], s=150, color=c, edgecolor=PAPER, lw=1.6, zorder=4)
        ax.annotate(f"{r.msoa_name}\n{r.hle:.1f} years",
                    xy=(r.hle, 0.09), ha="center", va="bottom",
                    fontsize=11.5, color=c, linespacing=1.3, fontweight="semibold")
        ax.annotate(f"95% interval {r.hle_lci:.1f}–{r.hle_uci:.1f}",
                    xy=(r.hle, -0.1), ha="center", va="top", fontsize=9.5, color=INK2)

    # the cautious comparison the third paragraph makes
    cautious = hi.hle_lci - lo.hle_uci
    ax.annotate("", xy=(lo.hle_uci, -0.46), xytext=(hi.hle_lci, -0.46),
                arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    ax.text((lo.hle_uci + hi.hle_lci) / 2, -0.53,
            f"{cautious:.1f} years apart even at the cautious end of each interval",
            ha="center", va="top", fontsize=10, color=INK2)

    ax.set_xlim(d.hle.min() - 3.2, d.hle.max() + 3.2)
    ax.set_ylim(-0.95, 0.72)
    ax.set_yticks([])
    ax.set_xlabel("Healthy life expectancy at birth, men, 2019–23 (years)", fontsize=11, color=INK2)
    ax.tick_params(axis="x", labelsize=10.5, colors=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    tidy(ax)

    fig.suptitle(f"One council. {len(d)} neighbourhoods. {hi.hle - lo.hle:.1f} years of healthy life.",
                 fontsize=15, color=INK, x=0.012, ha="left", y=0.975)
    fig.text(0.012, 0.902, "Each grey mark is one of Wirral's middle-layer super output areas, "
             "a neighbourhood of 5,000–15,000 people.", fontsize=10.2, color=INK2, va="top")
    fig.text(0.012, 0.028, "Source: ONS, Health state life expectancy estimates for MSOAs, England and Wales: "
             "2019 to 2023 (30 Jul 2026), via OHID Local health.\nCensus-2021-based: not comparable with the "
             "APS national series.", fontsize=8.4, color=INK2, linespacing=1.35, va="bottom")
    fig.tight_layout(rect=(0, 0.085, 1, 0.875))
    fig.savefig(OUT / "wirral_row.png", dpi=170, facecolor=PAPER)
    plt.close(fig)
    print("wrote", OUT / "wirral_row.png",
          f"(range {hi.hle - lo.hle:.1f}, cautious {cautious:.1f})")


def null_scatter(j: pd.DataFrame, r_male: float) -> None:
    """The absence of a relationship, drawn."""
    d = j.dropna(subset=["hle_male", "pct_within_18"]).copy()
    d["pct"] = d.pct_within_18 * 100

    fig, ax = plt.subplots(figsize=(9.2, 6.6))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.scatter(d.hle_male, d.pct, s=7, color=MUTED, alpha=0.3, lw=0, zorder=2)

    # The decile comparison the prose makes, all ten steps of it. Medians,
    # not means, and cut on this same frame - matching 09_gold_joined.py, so
    # the two ends of this line are the two numbers the article quotes.
    d["decile"] = pd.qcut(d.hle_male, 10, labels=False, duplicates="drop")
    dec = d.groupby("decile").agg(hle=("hle_male", "median"), pct=("pct", "median"))
    ax.plot(dec.hle, dec.pct, color=ACCENT, lw=1.8, zorder=4, alpha=0.9)
    ax.scatter(dec.hle, dec.pct, s=86, color=ACCENT, edgecolor=PAPER, lw=1.5, zorder=5)
    ax.annotate(f"healthiest tenth of\nneighbourhoods: {dec.pct.iloc[-1]:.1f}%",
                xy=(dec.hle.iloc[-1], dec.pct.iloc[-1]), xytext=(dec.hle.iloc[-1] - 1.4, 86.5),
                fontsize=9.8, color=ACCENT, ha="center", linespacing=1.3,
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.9, alpha=0.6))
    ax.annotate(f"least healthy tenth: {dec.pct.iloc[0]:.1f}%",
                xy=(dec.hle.iloc[0], dec.pct.iloc[0]), xytext=(dec.hle.iloc[0] + 1.6, 86.5),
                fontsize=9.8, color=ACCENT, ha="center",
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.9, alpha=0.6))

    ax.axhline(92, color=BAND, lw=1.4, zorder=3)
    ax.text(d.hle_male.max(), 92.9, "the 18-week standard: 92%", ha="right", va="bottom",
            fontsize=10, color=BAND)

    ax.set_xlim(d.hle_male.min() - 1.2, d.hle_male.max() + 1.2)
    ax.set_ylim(40, 99)
    ax.set_xlabel("Neighbourhood healthy life expectancy at birth, men, 2019–23 (years)",
                  fontsize=11, color=INK2)
    ax.set_ylabel("18-week share of the main hospital (%)", fontsize=11, color=INK2)
    ax.tick_params(labelsize=10.5, colors=INK2)
    ax.grid(color=GRID, lw=0.8, zorder=1)
    tidy(ax, spines=("top", "right"))
    ax.spines["left"].set_color(GRID)

    fig.suptitle(f"Two measures that do not move together (r = \u2212{abs(r_male):.3f})",
                 fontsize=15, color=INK, x=0.012, ha="left", y=0.978)
    fig.text(0.012, 0.912, f"Each grey mark is one of {len(d):,} English neighbourhoods, placed by its own healthy life "
             "expectancy and by the\n18-week performance of the acute trust taking most of its elective admissions. "
             "Blue: the median of each\ntenth of neighbourhoods. The horizontal banding is the join itself — "
             "every neighbourhood sharing a main\nhospital inherits that one figure.",
             fontsize=9.8, color=INK2, linespacing=1.38, va="top")
    fig.text(0.012, 0.022, "Sources: ONS MSOA healthy life expectancy 2019–23 via OHID Local health; NHS England RTT "
             "incomplete pathways, July 2026 (reported\nproviders, reconciled to the published provider workbook); OHID "
             "acute trust catchment populations, elective, Apr 2026.",
             fontsize=8.4, color=INK2, linespacing=1.35, va="bottom")
    fig.tight_layout(rect=(0, 0.075, 1, 0.825))
    fig.savefig(OUT / "null_scatter.png", dpi=170, facecolor=PAPER)
    plt.close(fig)
    print("wrote", OUT / "null_scatter.png", f"(n={len(d)}, deciles {dec.pct.iloc[0]:.1f} -> {dec.pct.iloc[-1]:.1f})")


def social_card(m: pd.DataFrame) -> None:
    """1200x630. Eight of the 36 ICBs, so the comparison survives a thumbnail."""
    d = m[m.sex == "Male"]
    med = d.groupby("icb_name_short").hle.median().sort_values()
    lo, hi = med.min(), med.max()
    picks = med.index[np.linspace(0, len(med) - 1, 8).round().astype(int)].tolist()

    fig, ax = plt.subplots(figsize=(12, 6.3))
    fig.patch.set_facecolor(PAPER)
    ax.set_position((0.245, 0.135, 0.738, 0.545))
    ax.set_facecolor(PAPER)
    ax.axvspan(lo, hi, color=BAND, alpha=0.1, lw=0, zorder=0)
    for edge in (lo, hi):
        ax.axvline(edge, color=BAND, lw=1.6, zorder=3)
    for i, name in enumerate(picks):
        g = d[d.icb_name_short == name]
        ax.scatter(g.hle, np.full(len(g), i), s=11, color=MUTED, alpha=0.5, lw=0, zorder=2)
        ax.scatter([med[name]], [i], s=82, color=ACCENT, edgecolor=PAPER, lw=1.4, zorder=4)
    ax.set_yticks(range(len(picks)))
    ax.set_yticklabels([SHORT_NAME.get(n, n).replace(" and ", " & ") for n in picks],
                       fontsize=11.5, color=INK2)
    ax.set_xlim(d.hle.min() - 1, d.hle.max() + 1)
    ax.set_ylim(-1.35, len(picks) - 0.45)
    ax.tick_params(axis="x", labelsize=11, colors=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=1)
    tidy(ax)
    # The band label goes under the rows, where there is nothing to collide with.
    ax.text(lo + (hi - lo) / 2, -0.75, f"all 36 ICB medians fit in here: {hi - lo:.1f} yrs",
            ha="center", va="center", fontsize=11.5, color=BAND)

    fig.text(0.018, 0.955, "Every ICB in England is wider\nthan the gap between ICBs",
             fontsize=33, color=INK, va="top", ha="left", linespacing=1.14, fontweight="bold")
    fig.text(0.018, 0.735, "Neighbourhood healthy life expectancy at birth, men, 2019\u201323. "
             "Eight of the 36 ICBs, evenly spaced by median.",
             fontsize=12.5, color=INK2, va="top", ha="left")
    fig.text(0.018, 0.038, "ONS \u00b7 OHID Local health", fontsize=10.5, color=MUTED, va="bottom")
    fig.savefig(OUT / "social_card.png", dpi=100, facecolor=PAPER)
    plt.close(fig)
    print("wrote", OUT / "social_card.png")


def main() -> None:
    m = pd.read_parquet(GOLD_DIR / "01_spread" / "msoa_hle_icb.parquet").dropna(subset=["hle"])
    j = pd.read_csv(GOLD_DIR / "03_joined" / "msoa_joined.csv")
    s = pd.read_csv(GOLD_DIR / "03_joined" / "joined_summary.csv")
    row = s[(s.measure.str.startswith("pearson r: MSOA HLE vs FPTP")) & (s.sex == "Male")]
    r_male = float(row.value.iloc[0]) if len(row) else float("nan")
    wirral_row(m)
    null_scatter(j, r_male)
    social_card(m)


if __name__ == "__main__":
    main()
