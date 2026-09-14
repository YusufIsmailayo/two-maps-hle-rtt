"""
Gold 1: within-ICB vs between-ICB spread of MSOA healthy life expectancy.

The claim under test: the spread of HLE *inside* a single ICB is wider than
the distance *between* ICB medians. Reported separately for males and
females - the article shows whichever is the weaker case for the claim.

Outputs (data/gold/01_spread/):
  icb_spread_by_sex.csv   one row per ICB x sex: n MSOAs, min/p10/p25/median/
                          p75/p90/max, IQR, range, and the ICB's population
                          rank by median.
  spread_summary.csv      the headline comparison per sex: typical within-ICB
                          IQR and range vs the IQR and range of ICB medians;
                          share of ICBs whose internal range exceeds the
                          between-ICB range; within/between variance split.
  msoa_hle_icb.parquet    the MSOA x sex rows with ICB attached (chart input).

ICB HLE "median" here is the median of constituent MSOA HLEs - a summary of
neighbourhood values, not an ICB life table. ONS publishes its own ICB HLE
on the pre-April-2026 42 ICBs; that series is used as a second, independent
between-ICB benchmark (spread_summary rows tagged 'ons_42_icb').
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR, SILVER_DIR  # noqa: E402

OUT = GOLD_DIR / "01_spread"
OUT.mkdir(parents=True, exist_ok=True)


def q(s: pd.Series, p: float) -> float:
    return float(s.quantile(p))


def main() -> None:
    ons = pd.read_parquet(SILVER_DIR / "hle" / "hle_ons.parquet")
    geo = pd.read_parquet(SILVER_DIR / "geography" / "msoa_geography.parquet")
    msoa = ons[(ons.country == "England") & (ons.area_type == "MSOA")][
        ["area_code", "area_name", "sex", "hle", "hle_lci", "hle_uci", "hle_excluded_reason"]]
    df = msoa.merge(geo[["msoa_code", "lad_name", "region_name", "icb_code", "icb_ods", "icb_name_short", "straddles_icb"]],
                    left_on="area_code", right_on="msoa_code", how="left", validate="m:1")
    assert df.icb_code.notna().all(), "MSOA without ICB"
    df = df.drop(columns="msoa_code").rename(columns={"area_code": "msoa_code", "area_name": "msoa_name"})
    df.to_parquet(OUT / "msoa_hle_icb.parquet", index=False)

    rows, summary = [], []
    for sex, d in df.dropna(subset=["hle"]).groupby("sex"):
        g = d.groupby(["icb_code", "icb_ods", "icb_name_short"]).hle
        icb = pd.DataFrame({
            "n_msoa": g.size(), "min": g.min(), "p10": g.quantile(.10), "p25": g.quantile(.25),
            "median": g.median(), "p75": g.quantile(.75), "p90": g.quantile(.90), "max": g.max(),
        }).reset_index()
        icb["iqr"] = icb.p75 - icb.p25
        icb["range"] = icb["max"] - icb["min"]
        icb["interdecile"] = icb.p90 - icb.p10
        icb["sex"] = sex
        icb = icb.sort_values("median", ascending=False)
        icb["rank_by_median"] = range(1, len(icb) + 1)
        rows.append(icb)

        # Between-ICB spread: the distribution of the 36 ICB medians.
        med = icb["median"]
        between = {"iqr": q(med, .75) - q(med, .25), "range": med.max() - med.min(),
                   "interdecile": q(med, .9) - q(med, .1)}
        # Variance decomposition of MSOA HLE: total = within-ICB + between-ICB.
        grand = d.hle.mean()
        icb_mean = d.groupby("icb_code").hle.transform("mean")
        ss_within = ((d.hle - icb_mean) ** 2).sum()
        ss_between = ((icb_mean - grand) ** 2).sum()

        summary += [
            {"sex": sex, "basis": "msoa_within_36_icb", "measure": "IQR", "within_icb_median": icb.iqr.median(),
             "within_icb_min": icb.iqr.min(), "within_icb_max": icb.iqr.max(), "between_icb_medians": between["iqr"],
             "n_icb_within_exceeds_between": int((icb.iqr > between["iqr"]).sum()), "n_icb": len(icb)},
            {"sex": sex, "basis": "msoa_within_36_icb", "measure": "interdecile", "within_icb_median": icb.interdecile.median(),
             "within_icb_min": icb.interdecile.min(), "within_icb_max": icb.interdecile.max(), "between_icb_medians": between["interdecile"],
             "n_icb_within_exceeds_between": int((icb.interdecile > between["interdecile"]).sum()), "n_icb": len(icb)},
            {"sex": sex, "basis": "msoa_within_36_icb", "measure": "range", "within_icb_median": icb["range"].median(),
             "within_icb_min": icb["range"].min(), "within_icb_max": icb["range"].max(), "between_icb_medians": between["range"],
             "n_icb_within_exceeds_between": int((icb["range"] > between["range"]).sum()), "n_icb": len(icb)},
            {"sex": sex, "basis": "msoa_within_36_icb", "measure": "variance_share_within_icb",
             "within_icb_median": ss_within / (ss_within + ss_between), "between_icb_medians": ss_between / (ss_within + ss_between),
             "n_icb": len(icb)},
        ]

        # Independent between-ICB benchmark: ONS's own ICB-level HLE (42 pre-2026 ICBs).
        o42 = ons[(ons.area_type == "Integrated Care Board") & (ons.sex == sex)].hle
        summary.append({"sex": sex, "basis": "ons_42_icb", "measure": "range",
                        "within_icb_median": icb["range"].median(), "between_icb_medians": o42.max() - o42.min(),
                        "n_icb_within_exceeds_between": int((icb["range"] > (o42.max() - o42.min())).sum()), "n_icb": len(o42)})
        summary.append({"sex": sex, "basis": "ons_42_icb", "measure": "IQR",
                        "within_icb_median": icb.iqr.median(), "between_icb_medians": q(o42, .75) - q(o42, .25),
                        "n_icb_within_exceeds_between": int((icb.iqr > (q(o42, .75) - q(o42, .25))).sum()), "n_icb": len(o42)})

    icb_all = pd.concat(rows, ignore_index=True)
    icb_all.round(2).to_csv(OUT / "icb_spread_by_sex.csv", index=False)
    summ = pd.DataFrame(summary).round(3)
    summ.to_csv(OUT / "spread_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(summ.to_string(index=False))
    print()
    for sex in ["Male", "Female"]:
        i = icb_all[icb_all.sex == sex]
        print(f"{sex}: top ICB median {i['median'].max():.1f} ({i.loc[i['median'].idxmax(), 'icb_name_short']}), "
              f"bottom {i['median'].min():.1f} ({i.loc[i['median'].idxmin(), 'icb_name_short']}); "
              f"narrowest within-ICB range {i['range'].min():.1f} ({i.loc[i['range'].idxmin(), 'icb_name_short']}), "
              f"widest {i['range'].max():.1f} ({i.loc[i['range'].idxmax(), 'icb_name_short']})")


if __name__ == "__main__":
    main()
