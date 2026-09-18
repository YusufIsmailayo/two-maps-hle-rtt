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
  lad_spread.csv          the same spread measures one level down, per local
                          authority x sex - the geography a reader actually
                          recognises as "twenty minutes apart".
  lad_spread_summary.csv  headline within-LAD spread across LADs with at least
                          ten MSOAs, so the opening claim rests on a measured
                          figure rather than a national percentile gap.

ICB HLE "median" here is the median of constituent MSOA HLEs - a summary of
neighbourhood values, not an ICB life table. ONS publishes its own ICB HLE
on the pre-April-2026 42 ICBs; that series is used as a second, independent
between-ICB benchmark (spread_summary rows tagged 'ons_42_icb').
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR, SILVER_DIR  # noqa: E402

OUT = GOLD_DIR / "01_spread"
OUT.mkdir(parents=True, exist_ok=True)


def q(s: pd.Series, p: float) -> float:
    return float(s.quantile(p))


def lad_spread(df: pd.DataFrame, min_msoa: int = 10) -> None:
    """Within-local-authority HLE spread.

    An ICB is an administrative footprint most people have never heard of; a
    council area is the unit that matches "twenty minutes apart by car". I
    compute the same measures per LAD, and summarise across the LADs big
    enough for a range to mean anything (>= min_msoa MSOAs), so the article's
    opening image can cite a number instead of a national percentile gap.
    """
    rows, summary = [], []
    for sex, d in df.dropna(subset=["hle"]).groupby("sex"):
        g = d.groupby("lad_name").hle
        lad = pd.DataFrame({
            "n_msoa": g.size(), "min": g.min(), "p10": g.quantile(.10), "p25": g.quantile(.25),
            "median": g.median(), "p75": g.quantile(.75), "p90": g.quantile(.90), "max": g.max(),
        }).reset_index()
        lad["iqr"] = lad.p75 - lad.p25
        lad["range"] = lad["max"] - lad["min"]
        lad["interdecile"] = lad.p90 - lad.p10
        lad["sex"] = sex
        lad["meets_min_msoa"] = lad.n_msoa >= min_msoa
        rows.append(lad.sort_values("range", ascending=False))

        big = lad[lad.meets_min_msoa]
        # The range is a distance between a council's two EXTREME neighbourhoods.
        # It is not what two neighbourhoods a short drive apart typically differ
        # by, and the first draft of the article confused the two. So I also
        # compute the median absolute difference over every pair of MSOAs inside
        # the same council - the honest answer to "pick two neighbourhoods here".
        pairs = []
        for _, g in d[d.lad_name.isin(big.lad_name)].groupby("lad_name"):
            v = g.hle.to_numpy()
            diff = np.abs(v[:, None] - v[None, :])
            pairs.append(diff[np.triu_indices(len(v), 1)])
        pairs = np.concatenate(pairs)
        # The between-LAD comparison is the distribution of LAD medians, same
        # logic as the ICB test one level up.
        med = big["median"]
        widest = big.loc[big["range"].idxmax()]
        summary.append({
            "sex": sex, "min_msoa": min_msoa, "n_lad": len(big),
            "within_lad_range_median": big["range"].median(),
            "within_lad_range_p90": q(big["range"], .90),
            "within_lad_range_max": big["range"].max(),
            "widest_lad": widest.lad_name, "widest_lad_min": widest["min"], "widest_lad_max": widest["max"],
            "within_lad_iqr_median": big.iqr.median(),
            "between_lad_medians_range": med.max() - med.min(),
            "n_lad_range_ge_13": int((big["range"] >= 13).sum()),
            "within_lad_pairwise_median": float(np.median(pairs)),
            "within_lad_pairwise_p90": float(np.percentile(pairs, 90)),
            "within_lad_pairwise_share_ge_13": float((pairs >= 13).mean()),
            "n_pairs": len(pairs),
            "n_lad_within_exceeds_between": int((big["range"] > (med.max() - med.min())).sum()),
        })

    pd.concat(rows, ignore_index=True).round(2).to_csv(OUT / "lad_spread.csv", index=False)
    summ = pd.DataFrame(summary).round(2)
    summ.to_csv(OUT / "lad_spread_summary.csv", index=False)
    for _, r in summ.iterrows():
        print(f"{r.sex}: within-LAD HLE range across {int(r.n_lad)} LADs with >={min_msoa} MSOAs - "
              f"median {r.within_lad_range_median:.1f} yrs, max {r.within_lad_range_max:.1f} "
              f"({r.widest_lad}, {r.widest_lad_min:.1f}-{r.widest_lad_max:.1f}); "
              f"{int(r.n_lad_range_ge_13)} LADs span >= 13 yrs internally")
        print(f"{r.sex}: but two MSOAs picked at random inside the same council differ by a median "
              f"{r.within_lad_pairwise_median:.1f} yrs (p90 {r.within_lad_pairwise_p90:.1f}); only "
              f"{r.within_lad_pairwise_share_ge_13:.1%} of within-council pairs differ by 13+ years")


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
    print()
    lad_spread(df)


if __name__ == "__main__":
    main()
