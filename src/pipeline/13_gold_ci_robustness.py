"""
Gold 7: does the within-ICB claim survive the estimates' uncertainty?

The strip chart plots 6,856 point estimates, and ONS publishes a 95% interval
around each one with a median width of about three years. So the fair question
is whether "every ICB's internal spread exceeds the distance between ICB
medians" is a real feature or an artefact of plotting points without their
error.

I answer it with a deliberately conservative FIXED-EXTREMES check: for each
ICB, take the neighbourhood with the lowest point estimate and the one with
the highest, then compare the LOWER bound of the high one against the UPPER
bound of the low one. That shrinks every ICB's internal range by roughly the
width of two intervals before the comparison is made.

What this is not: a simultaneous confidence band over all 6,856 neighbourhoods,
and not a like-for-like test either - the between-ICB side stays on point
estimates, so the comparison is harder on the within-ICB side than on the
between-ICB side. I report the interdecile version too, where the same
penalty bites much harder, rather than only the measure that survives.

Output (data/gold/07_ci_robustness/ci_robustness.csv).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR  # noqa: E402

OUT = GOLD_DIR / "07_ci_robustness"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    m = pd.read_parquet(GOLD_DIR / "01_spread" / "msoa_hle_icb.parquet").dropna(subset=["hle"])
    width = (m.hle_uci - m.hle_lci)
    print(f"MSOA 95% interval width: median {width.median():.1f} yrs, p90 {width.quantile(.9):.1f}")

    rows = []
    for sex, d in m.groupby("sex"):
        med = d.groupby("icb_name_short").hle.median()
        between = med.max() - med.min()
        per_icb = []
        for name, g in d.groupby("icb_name_short"):
            lo_msoa, hi_msoa = g.loc[g.hle.idxmin()], g.loc[g.hle.idxmax()]
            per_icb.append({
                "icb_name_short": name,
                "range_point": hi_msoa.hle - lo_msoa.hle,
                "range_conservative": hi_msoa.hle_lci - lo_msoa.hle_uci,
                "interdecile_point": g.hle.quantile(.90) - g.hle.quantile(.10),
                "interdecile_conservative": g.hle_lci.quantile(.90) - g.hle_uci.quantile(.10),
            })
        t = pd.DataFrame(per_icb)
        t["sex"] = sex
        t["between_icb_median_spread"] = between
        for measure in ["range", "interdecile"]:
            t[f"{measure}_conservative_exceeds_between"] = t[f"{measure}_conservative"] > between
        rows.append(t)
        for measure in ["range", "interdecile"]:
            c = t[f"{measure}_conservative"]
            n = int(t[f"{measure}_conservative_exceeds_between"].sum())
            print(f"{sex} {measure:12s}: between-ICB spread {between:.1f} | conservative within-ICB "
                  f"min {c.min():.1f}, median {c.median():.1f} | exceeds between: {n}/{len(t)} ICBs")

    out = pd.concat(rows, ignore_index=True)
    out.round(2).to_csv(OUT / "ci_robustness.csv", index=False)
    print("wrote", OUT / "ci_robustness.csv")


if __name__ == "__main__":
    main()
