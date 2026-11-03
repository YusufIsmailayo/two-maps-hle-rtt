"""
Gold 3: what happens when you make the join anyway.

Route B gives every MSOA a dominant elective trust and an admissions-
weighted 18-week figure. This step asks what that joined table can and
cannot say - because if the join were both feasible and informative, the
article's premise would be wrong on both counts.

Outputs (data/gold/03_joined/):
  msoa_joined.csv          MSOA x HLE(M,F) x FPTP trust x RTT 18wk% (FPTP and
                           weighted) x ICB.
  trust_catchment_hle.csv  one row per FPTP trust: n MSOAs, HLE median/IQR/
                           range of its catchment MSOAs, its 18wk%.
  joined_summary.csv       correlations and variance splits.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR  # noqa: E402

OUT = GOLD_DIR / "03_joined"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    b = pd.read_csv(GOLD_DIR / "02_crosswalk" / "B_msoa_fptp_rtt.csv")
    hle = pd.read_parquet(GOLD_DIR / "01_spread" / "msoa_hle_icb.parquet")
    geo = hle[["msoa_code", "msoa_name", "icb_ods", "icb_name_short", "region_name"]].drop_duplicates("msoa_code")
    j = b.merge(geo, on="msoa_code", how="left")
    j.to_csv(OUT / "msoa_joined.csv", index=False)

    rows = []
    for sex, col in [("Male", "hle_male"), ("Female", "hle_female")]:
        d = j.dropna(subset=[col, "pct_within_18"])
        r_fptp = np.corrcoef(d[col], d.pct_within_18)[0, 1]
        dw = j.dropna(subset=[col, "weighted_pct_within_18"])
        r_w = np.corrcoef(dw[col], dw.weighted_pct_within_18)[0, 1]
        # Spearman for robustness
        rs = d[[col, "pct_within_18"]].corr(method="spearman").iloc[0, 1]
        # variance split of HLE by FPTP trust
        grand = d[col].mean()
        tm = d.groupby("trust_code")[col].transform("mean")
        ssw, ssb = ((d[col] - tm) ** 2).sum(), ((tm - grand) ** 2).sum()
        # within-trust-catchment HLE spread vs between-trust 18wk% spread
        tc = d.groupby(["trust_code", "trust_name"]).agg(
            n_msoa=(col, "size"), hle_median=(col, "median"),
            hle_p25=(col, lambda s: s.quantile(.25)), hle_p75=(col, lambda s: s.quantile(.75)),
            hle_min=(col, "min"), hle_max=(col, "max"), pct_within_18=("pct_within_18", "first"),
            total_waiting=("total_waiting", "first")).reset_index()
        tc["hle_iqr"] = tc.hle_p75 - tc.hle_p25
        tc["hle_range"] = tc.hle_max - tc.hle_min
        tc["sex"] = sex
        tc.round(3).to_csv(OUT / f"trust_catchment_hle_{sex.lower()}.csv", index=False)
        tc10 = tc[tc.n_msoa >= 10]
        rows += [
            {"sex": sex, "measure": "pearson r: MSOA HLE vs FPTP trust 18wk%", "value": round(r_fptp, 3), "n": len(d)},
            {"sex": sex, "measure": "spearman rho: MSOA HLE vs FPTP trust 18wk%", "value": round(rs, 3), "n": len(d)},
            {"sex": sex, "measure": "pearson r: MSOA HLE vs admissions-weighted 18wk%", "value": round(r_w, 3), "n": len(dw)},
            {"sex": sex, "measure": "share of MSOA HLE variance that is WITHIN FPTP-trust catchments", "value": round(ssw / (ssw + ssb), 3), "n": d.trust_code.nunique()},
            {"sex": sex, "measure": "median within-trust-catchment HLE range (trusts with >=10 MSOAs), years", "value": round(tc10.hle_range.median(), 1), "n": len(tc10)},
            {"sex": sex, "measure": "median within-trust-catchment HLE IQR (trusts with >=10 MSOAs), years", "value": round(tc10.hle_iqr.median(), 1), "n": len(tc10)},
            {"sex": sex, "measure": "range of trust-catchment HLE medians, years", "value": round(tc10.hle_median.max() - tc10.hle_median.min(), 1), "n": len(tc10)},
            {"sex": sex, "measure": "range of FPTP trusts' 18wk% (pp)", "value": round(100 * (tc10.pct_within_18.max() - tc10.pct_within_18.min()), 1), "n": len(tc10)},
            {"sex": sex, "measure": "IQR of FPTP trusts' 18wk% (pp)", "value": round(100 * (tc10.pct_within_18.quantile(.75) - tc10.pct_within_18.quantile(.25)), 1), "n": len(tc10)},
        ]
        # HLE gap between best- and worst-waiting trusts' catchments
        q = tc10.sort_values("pct_within_18")
        lo, hi = q.head(len(q) // 4), q.tail(len(q) // 4)
        # Two different statistics, and the article has to name which it uses.
        # The first is a median of trust-level medians - each trust counts once,
        # however many neighbourhoods it serves. The second pools the actual
        # neighbourhoods. They do not agree, and the pooled one is what a reader
        # hears when you say "the neighbourhoods they serve".
        rows.append({"sex": sex, "measure": "MEDIAN OF TRUST MEDIANS, catchment HLE: worst-quartile-waiting vs best-quartile (years)",
                     "value": f"{lo.hle_median.median():.1f} vs {hi.hle_median.median():.1f}", "n": len(lo)})
        # A reader needs one plain-English translation of a near-zero
        # correlation, and the correlation itself does not license one: r can
        # sit at zero while the extremes differ wildly. So I measure the
        # extremes directly - the decile of neighbourhoods with the lowest HLE
        # against the decile with the highest, compared on the 18-week share of
        # the trust each mostly uses.
        # Cut the deciles on the same frame the correlation uses - the
        # neighbourhoods that actually have a waiting figure. Cutting them on
        # the full MSOA set instead puts the 167 neighbourhoods whose dominant
        # trust did not submit inside the deciles, where the median then skips
        # them silently: the thresholds move, the group sizes stop being
        # deciles of anything, and the top decile reads 0.3 pp lower than it is.
        dec_lo = d[d[col] <= d[col].quantile(.10)]
        dec_hi = d[d[col] >= d[col].quantile(.90)]
        rows.append({"sex": sex, "measure": "dominant trust's 18wk%: bottom vs top HLE DECILE of neighbourhoods",
                     "value": f"{dec_lo.pct_within_18.median():.1%} vs {dec_hi.pct_within_18.median():.1%} "
                              f"({abs(dec_lo.pct_within_18.median() - dec_hi.pct_within_18.median()) * 100:.1f} pp apart)",
                     "n": f"{len(dec_lo)} vs {len(dec_hi)} MSOAs"})
        pooled_lo = d[d.trust_code.isin(lo.trust_code)][col]
        pooled_hi = d[d.trust_code.isin(hi.trust_code)][col]
        rows.append({"sex": sex, "measure": "POOLED MSOA median HLE: worst-quartile-waiting vs best-quartile (years)",
                     "value": f"{pooled_lo.median():.1f} vs {pooled_hi.median():.1f}",
                     "n": f"{len(pooled_lo)} vs {len(pooled_hi)} MSOAs"})

    s = pd.DataFrame(rows)
    s.to_csv(OUT / "joined_summary.csv", index=False)
    pd.set_option("display.width", 200, "display.max_colwidth", 100)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()
