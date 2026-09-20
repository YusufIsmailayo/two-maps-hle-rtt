"""
Gold 4: the chart that carries the argument.

One row per ICB (36, April 2026), every constituent MSOA's healthy life
expectancy as a mark along the row, ICB median called out, rows ordered by
median. The shaded vertical band is the full spread of the 36 ICB medians -
the "between" distance. The claim is proven visually if every row's marks
extend beyond the band on both sides. Two panels, males and females, same
row order (male median) so the eye can compare.

Two rows are annotated with the 18-week RTT share of providers parented by
that ICB (July 2026) - the top and bottom ICB by HLE - to show how little an
access figure at ICB level says about a neighbourhood. The annotations are
anchored to the right edge of the axes, not to the data, so no row can push
them off the canvas.
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
ACCENT = "#2a78d6"   # series-1
BAND = "#eb6834"     # series-2, used only for the between-ICB band


def beeswarm_offsets(values: np.ndarray, bin_width: float = 0.1, max_spread: float = 0.34) -> np.ndarray:
    """Deterministic vertical offsets so a row of neighbourhoods reads as a shape.

    The first version of this chart scattered each row's MSOAs with random
    jitter. With up to 400 marks in a row 60px tall, random placement stops
    being a distribution and becomes grain - the plot looked dirty, and the
    dirt carried no information. Here each value is binned on x and the points
    in a bin are dealt symmetrically outwards from the row's centre line, so
    vertical thickness means local density and nothing else. The bin width
    matches the data's own grid - ONS publishes HLE to one decimal - so a
    column is one distinct published value rather than an arbitrary bucket.
    Where a bin is deeper than the row can hold, the column is compressed to
    fit rather than bleeding into its neighbours.
    """
    order = np.argsort(values, kind="stable")
    offsets = np.zeros(len(values))
    bins = np.floor(values[order] / bin_width).astype(int)
    start = 0
    for b in range(len(bins)):
        if b + 1 < len(bins) and bins[b + 1] == bins[start]:
            continue
        column = order[start:b + 1]
        k = len(column)
        # deal outwards: 0, +1, -1, +2, -2 ... then scale to fit the row
        seq = np.zeros(k)
        for i in range(k):
            seq[i] = ((i + 1) // 2) * (1 if i % 2 else -1)
        step = min(0.042, max_spread / max(abs(seq).max(), 1))
        offsets[column] = seq * step
        start = b + 1
    return offsets


def main() -> None:
    m = pd.read_parquet(GOLD_DIR / "01_spread" / "msoa_hle_icb.parquet").dropna(subset=["hle"])
    icb = pd.read_csv(GOLD_DIR / "02_crosswalk" / "A_icb_table.csv")
    order = (m[m.sex == "Male"].groupby("icb_name_short").hle.median().sort_values(ascending=True).index.tolist())
    ypos = {name: i for i, name in enumerate(order)}
    rtt = icb.set_index("icb_name_short").pct_within_18

    fig, axes = plt.subplots(1, 2, figsize=(14, 15), sharey=True)
    fig.patch.set_facecolor("#fcfcfb")
    xlo, xhi = m.hle.min() - 1.5, m.hle.max() + 1.5
    for ax, sex in zip(axes, ["Male", "Female"]):
        d = m[m.sex == sex]
        med = d.groupby("icb_name_short").hle.median()
        lo, hi = med.min(), med.max()
        ax.axvspan(lo, hi, color=BAND, alpha=0.09, lw=0, zorder=0)
        for edge in (lo, hi):
            ax.axvline(edge, color=BAND, lw=1.3, alpha=0.95, zorder=3)
        ax.set_facecolor("#fcfcfb")
        for name, g in d.groupby("icb_name_short"):
            y = ypos[name]
            ax.scatter(g.hle, y + beeswarm_offsets(g.hle.to_numpy()), s=4,
                       color=MUTED, alpha=0.75, lw=0, zorder=2)
            ax.scatter([med[name]], [y], s=54, color=ACCENT, edgecolor="#fcfcfb", lw=1.1, zorder=4)
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels(order, fontsize=8.5, color=INK2)
        ax.set_xlim(xlo, xhi)
        ax.set_xlabel(f"Healthy life expectancy at birth, {sex.lower()}s, 2019–23 (years)", fontsize=9.5, color=INK2)
        ax.tick_params(axis="x", labelsize=8.5, colors=INK2)
        ax.grid(axis="x", color=GRID, lw=0.8, zorder=1)
        for s in ["top", "right", "left"]:
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="y", length=0)
        ax.text(lo + (hi - lo) / 2, len(order) + 0.35, f"spread of the 36 ICB medians: {hi - lo:.1f} yrs",
                ha="center", va="bottom", fontsize=8.5, color=BAND)
        # Annotate the best and worst ICB by HLE with their providers' 18-week
        # share. The labels sit just outside the two extreme rows rather than
        # on them, so they never cover a median marker or a neighbourhood.
        for name, dy, va in [(order[-1], 0.62, "bottom"), (order[0], -0.62, "top")]:
            ax.annotate(f"providers parented by this ICB: {rtt[name]:.0%} within 18 wks",
                        xy=(xhi - 0.4, ypos[name] + dy), fontsize=7.4, color=INK2, va=va, ha="right")
    axes[0].set_ylim(-1.5, len(order) + 1.3)

    fig.suptitle("Inside every ICB, neighbourhood healthy life expectancy spans more years than separate the best and worst ICB",
                 fontsize=13, color=INK, x=0.01, ha="left", y=0.985)
    fig.text(0.01, 0.955, "Each grey mark is one MSOA (6,856 in England). Blue mark: median of the ICB's MSOAs. Rows ordered by male median. "
             "Orange band: the whole distance between the highest- and lowest-median ICB.",
             fontsize=9, color=INK2)
    fig.text(0.01, 0.022, "Source: ONS, Health state life expectancy estimates for MSOAs, England and Wales: 2019 to 2023 (30 Jul 2026), "
             "redistributed by OHID Local health (2 Sep 2026); ONS Open Geography Portal LSOA→ICB (Apr 2026); NHS England RTT July 2026.",
             fontsize=7.5, color=INK2)
    fig.text(0.01, 0.008, "HLE uses Census 2021 health prevalence and is not comparable with the APS-based national series. "
             "One MSOA-sex (Barnet 042, male) excluded by ONS as implausible.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.035, 1, 0.94))
    fig.savefig(OUT / "icb_strip_hle.png", dpi=180, facecolor=fig.get_facecolor())
    print("wrote", OUT / "icb_strip_hle.png")


if __name__ == "__main__":
    main()
