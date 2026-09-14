"""
Gold 5: is the headline result a one-month artefact?

Repeats the two RTT-dependent results for every month in Bronze (April-July
2026): the MSOA-level correlation between HLE and the dominant elective
trust's 18-week share (Route B), and the ICB-level correlation between HLE
median and providers' 18-week share (Route A). Also re-derives the England
18-week figure per month so the drift in the waiting list is visible.

Output: data/gold/05_months/by_month.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR, SILVER_DIR  # noqa: E402

OUT = GOLD_DIR / "05_months"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    prov_all = pd.read_parquet(SILVER_DIR / "rtt" / "rtt_provider.parquet")
    cat = pd.read_parquet(SILVER_DIR / "catchment" / "msoa_trust_admissions.parquet")
    cat = cat[(cat.catchment_year == 2024) & (cat.admission_type == "elective")]
    fp = cat[cat.fptp][["msoa_code", "trust_code"]]
    hle = pd.read_parquet(GOLD_DIR / "01_spread" / "msoa_hle_icb.parquet")
    wide = hle.pivot(index="msoa_code", columns="sex", values="hle").rename(columns={"Male": "hle_male", "Female": "hle_female"})
    icb_of = hle.drop_duplicates("msoa_code").set_index("msoa_code").icb_ods
    icb_med = hle.groupby(["icb_ods", "sex"]).hle.median().unstack()

    rows = []
    for period, prov in prov_all.groupby("period"):
        eng = prov.within_18.sum() / prov.total_waiting.sum()
        # Route B: MSOA HLE vs FPTP trust 18wk%
        b = fp.merge(prov[["provider_code", "pct_within_18"]], left_on="trust_code", right_on="provider_code", how="left") \
              .merge(wide, left_on="msoa_code", right_index=True)
        # admissions-weighted alternative
        w = cat.merge(prov[["provider_code", "pct_within_18"]], left_on="trust_code", right_on="provider_code", how="inner")
        w["wt"] = w.patients_admitted * w.pct_within_18
        wm = (w.groupby("msoa_code").wt.sum() / w.groupby("msoa_code").patients_admitted.sum()).rename("weighted")
        b = b.merge(wm, left_on="msoa_code", right_index=True, how="left")
        # Route A: ICB medians vs ICB provider-parent 18wk%
        a = prov.groupby("provider_icb_ods").apply(lambda g: g.within_18.sum() / g.total_waiting.sum(), include_groups=False).rename("icb_pct")
        a = icb_med.merge(a, left_index=True, right_index=True)
        r = {"period": period, "providers": len(prov), "england_pct_within_18": round(eng, 4),
             "msoas_with_fptp_rtt": int(b.pct_within_18.notna().sum())}
        for sex in ["male", "female"]:
            d = b.dropna(subset=[f"hle_{sex}", "pct_within_18"])
            dw = b.dropna(subset=[f"hle_{sex}", "weighted"])
            r[f"r_msoa_fptp_{sex}"] = round(np.corrcoef(d[f"hle_{sex}"], d.pct_within_18)[0, 1], 3)
            r[f"rho_msoa_fptp_{sex}"] = round(d[[f"hle_{sex}", "pct_within_18"]].corr(method="spearman").iloc[0, 1], 3)
            r[f"r_msoa_weighted_{sex}"] = round(np.corrcoef(dw[f"hle_{sex}"], dw.weighted)[0, 1], 3)
            r[f"r_icb_{sex}"] = round(np.corrcoef(a[sex.capitalize()], a.icb_pct)[0, 1], 3)
        rows.append(r)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "by_month.csv", index=False)
    pd.set_option("display.width", 250)
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
