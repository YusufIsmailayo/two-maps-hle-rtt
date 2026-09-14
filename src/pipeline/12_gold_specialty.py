"""
Gold 6: the national 18-week picture by treatment function.

Silver builds RTT at period x provider x treatment function, but nothing in
Gold used it until now - which left the article citing a specialty figure
that was not reproducible from data/gold/. This closes that gap.

The specialty split is context, not evidence for the thesis: it is the
spread that makes "65% within 18 weeks" worth interrogating at all. Every
share is rebuilt from the weekly wait bands, never from a published
percentage, and C_999 ("Total") rows are dropped so the specialties sum to
the England total rather than double-counting it.

Output (data/gold/06_specialty/):
  specialty_18wk.csv      period x treatment function: pathways, within 18
                          weeks, over 52 weeks, and the recomputed shares.
  specialty_headline.csv  the headline month only, ordered worst-performing
                          first, with the England total as the last row.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR, SILVER_DIR  # noqa: E402

OUT = GOLD_DIR / "06_specialty"
OUT.mkdir(parents=True, exist_ok=True)

STANDARD = 0.92  # the operational standard: 92% of incomplete pathways within 18 weeks


def main() -> None:
    tfc = pd.read_parquet(SILVER_DIR / "rtt" / "rtt_provider_tfc.parquet")
    spec = tfc[tfc.tfc_code != "C_999"]

    by_period = (spec.groupby(["period", "tfc_code", "tfc_name"])[["total_waiting", "within_18", "over_52"]]
                 .sum().reset_index())
    by_period["pct_within_18"] = by_period.within_18 / by_period.total_waiting
    by_period["pct_over_52"] = by_period.over_52 / by_period.total_waiting
    by_period["gap_to_standard_pp"] = (STANDARD - by_period.pct_within_18) * 100

    # Every specialty must reconcile to the provider-level total for its month.
    prov = pd.read_parquet(SILVER_DIR / "rtt" / "rtt_provider.parquet")
    for period, g in by_period.groupby("period"):
        expected = prov.loc[prov.period == period, "total_waiting"].sum()
        assert abs(g.total_waiting.sum() - expected) < 1, \
            f"{period}: specialties sum to {g.total_waiting.sum():,.0f}, providers to {expected:,.0f}"

    by_period.round(4).to_csv(OUT / "specialty_18wk.csv", index=False)

    headline = by_period[by_period.period == by_period.period.max()].sort_values("pct_within_18")
    england = prov[prov.period == by_period.period.max()]
    total = pd.DataFrame([{
        "period": by_period.period.max(), "tfc_code": "C_999", "tfc_name": "England, all specialties",
        "total_waiting": england.total_waiting.sum(), "within_18": england.within_18.sum(),
        "over_52": england.over_52.sum(),
        "pct_within_18": england.within_18.sum() / england.total_waiting.sum(),
        "pct_over_52": england.over_52.sum() / england.total_waiting.sum(),
        "gap_to_standard_pp": (STANDARD - england.within_18.sum() / england.total_waiting.sum()) * 100,
    }])
    headline = pd.concat([headline, total], ignore_index=True)
    headline.round(4).to_csv(OUT / "specialty_headline.csv", index=False)

    period = by_period.period.max()
    print(f"{period}: {len(headline) - 1} treatment functions; none meets the 92% standard"
          if (headline.pct_within_18[:-1] < STANDARD).all() else f"{period}: some specialty meets the standard")
    show = headline.copy()
    show["pct_within_18"] = (show.pct_within_18 * 100).round(1)
    show["gap_to_standard_pp"] = show.gap_to_standard_pp.round(1)
    print(show[["tfc_name", "total_waiting", "pct_within_18", "gap_to_standard_pp"]].head(6).to_string(index=False))
    print("...")
    print(show[["tfc_name", "total_waiting", "pct_within_18", "gap_to_standard_pp"]].tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
