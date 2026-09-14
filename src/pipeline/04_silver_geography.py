"""
Silver: one row per English MSOA (2021) with its LAD, region, SICBL, ICB and
NHS region, built from LSOA-level lookups.

The ICB layer is the one the article's objection hinges on, so the nesting
is asserted rather than assumed: every MSOA must sit in exactly one ICB
(April 2026 boundaries). If any MSOA straddles two ICBs it is written to a
side table, not resolved by majority vote silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BRONZE_DIR, SILVER_DIR  # noqa: E402

LU = BRONZE_DIR / "ons_geography_lookups"
OUT = SILVER_DIR / "geography"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    oa = pd.read_csv(LU / "OA21_LSOA21_MSOA21_LAD23_EN_LU.csv", encoding="utf-8-sig", low_memory=False)
    # LSOA -> MSOA only. The OA-level LAD23 best-fit in this file puts one LSOA
    # (E01014754, North Somerset 005) in two LADs; LAD comes from the LSOA-level
    # April 2026 lookup instead, which has no such split.
    lsoa_msoa = oa[["LSOA21CD", "MSOA21CD", "MSOA21NM"]].drop_duplicates()
    assert not lsoa_msoa.duplicated("LSOA21CD").any(), "an LSOA maps to >1 MSOA"

    icb = pd.read_csv(LU / "LSOA21_SICBL26_ICB26_NHSER26_LAD26_EN_LU.csv", encoding="utf-8-sig")
    icb = icb.drop(columns=["ObjectId"], errors="ignore")
    assert not icb.duplicated("LSOA21CD").any(), "an LSOA maps to >1 SICBL/ICB"

    rgn = pd.read_csv(LU / "LAD24_RGN24_EN_LU.csv", encoding="utf-8-sig")
    rgn = rgn[["LAD24CD", "RGN24CD", "RGN24NM"]].drop_duplicates()

    lsoa = lsoa_msoa.merge(icb, on="LSOA21CD", how="outer", indicator=True)
    print("LSOA merge:", lsoa._merge.value_counts().to_dict())
    assert (lsoa._merge == "both").all(), "LSOA coverage differs between the two lookups"
    lsoa = lsoa.drop(columns="_merge")

    # Roll up to MSOA: count distinct ICB / SICBL / LAD per MSOA.
    g = lsoa.groupby("MSOA21CD")
    nest = pd.DataFrame({
        "n_lsoa": g.size(),
        "n_icb": g.ICB26CD.nunique(),
        "n_sicbl": g.SICBL26CD.nunique(),
        "n_lad26": g.LAD26CD.nunique(),
    }).reset_index()
    straddle = nest[(nest.n_icb > 1) | (nest.n_sicbl > 1) | (nest.n_lad26 > 1)]
    straddle.to_csv(OUT / "msoa_straddling_boundaries.csv", index=False)
    print(f"MSOAs straddling >1 ICB: {(nest.n_icb > 1).sum()} | >1 SICBL: {(nest.n_sicbl > 1).sum()} | >1 LAD26: {(nest.n_lad26 > 1).sum()}")

    # One row per MSOA. For any MSOA that does straddle, take the ICB/SICBL of
    # the majority of its LSOAs and flag it; the flag is carried to Gold.
    def majority(s: pd.Series) -> str:
        return s.value_counts().idxmax()

    msoa = lsoa.groupby("MSOA21CD").agg(
        msoa_name=("MSOA21NM", "first"),
        lad_code=("LAD26CD", majority), lad_name=("LAD26NM", majority),
        sicbl_code=("SICBL26CD", majority), sicbl_ods=("SICBL26CDH", majority), sicbl_name=("SICBL26NM", majority),
        icb_code=("ICB26CD", majority), icb_ods=("ICB26CDH", majority), icb_name=("ICB26NM", majority),
        nhser_code=("NHSER26CD", majority), nhser_name=("NHSER26NM", majority),
        n_lsoa=("LSOA21CD", "size"), n_icb=("ICB26CD", "nunique"), n_sicbl=("SICBL26CD", "nunique"),
    ).reset_index().rename(columns={"MSOA21CD": "msoa_code"})
    msoa["straddles_icb"] = msoa.n_icb > 1
    msoa["straddles_sicbl"] = msoa.n_sicbl > 1
    msoa = msoa.merge(rgn, left_on="lad_code", right_on="LAD24CD", how="left").drop(columns="LAD24CD") \
               .rename(columns={"RGN24CD": "region_code", "RGN24NM": "region_name"})
    # Barnsley and Sheffield were re-coded in the April 2026 LAD vintage
    # (E08000016 -> E08000038, E08000019 -> E08000039) and so miss the Dec 2024
    # LAD->Region lookup. Resolve by LAD name against the same lookup, and
    # assert that nothing else falls through.
    missing = msoa.region_code.isna()
    by_name = rgn.merge(pd.read_csv(LU / "LAD24_RGN24_EN_LU.csv", encoding="utf-8-sig")[["LAD24CD", "LAD24NM"]],
                        on="LAD24CD").set_index("LAD24NM")
    msoa.loc[missing, "region_code"] = msoa.loc[missing, "lad_name"].map(by_name.RGN24CD)
    msoa.loc[missing, "region_name"] = msoa.loc[missing, "lad_name"].map(by_name.RGN24NM)
    print("MSOAs with region resolved by LAD name (2026 re-coding):", int(missing.sum()),
          "->", msoa.loc[missing, "lad_name"].unique().tolist())
    assert msoa.region_code.notna().all(), "MSOAs still without region"

    assert msoa.msoa_code.is_unique
    assert len(msoa) == 6856, f"expected 6856 English MSOAs, got {len(msoa)}"
    msoa["icb_name_short"] = (msoa.icb_name.str.replace("^NHS ", "", regex=True)
                                            .str.replace(" Integrated Care Board$", "", regex=True))
    msoa.to_parquet(OUT / "msoa_geography.parquet", index=False)
    lsoa.to_parquet(OUT / "lsoa_geography.parquet", index=False)
    print("ICBs:", msoa.icb_code.nunique(), "| SICBLs:", msoa.sicbl_code.nunique(), "| LADs:", msoa.lad_code.nunique(),
          "| regions:", msoa.region_code.nunique())
    print(msoa.groupby("icb_name_short").size().describe().round(0).to_dict())


if __name__ == "__main__":
    main()
