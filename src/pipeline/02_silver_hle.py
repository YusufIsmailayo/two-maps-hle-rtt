"""
Silver: healthy life expectancy at MSOA level, from both the ONS origin file
and the OHID Fingertips redistribution, on a common schema.

Output grain (asserted): area_code x sex, one row each, per source.

Two tables are written rather than one merged table so the reconciliation
gate (03) can compare them as independent extracts rather than as a join
that would silently drop mismatches.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BRONZE_DIR, SILVER_DIR  # noqa: E402

OUT = SILVER_DIR / "hle"
OUT.mkdir(parents=True, exist_ok=True)

ONS_XLSX = BRONZE_DIR / "ons_hsle_msoa" / "hslemsoa.xlsx"
FT_CSV = BRONZE_DIR / "fingertips_hle_msoa" / "hle_94359_msoa.csv"


def silver_ons() -> pd.DataFrame:
    x = pd.ExcelFile(ONS_XLSX)
    hle = x.parse("2", header=6)
    hle = hle.rename(columns={
        "Area code": "area_code", "Area name": "area_name", "Area type": "area_type",
        "Country": "country", "Sex": "sex", "HLE": "hle", "LCI": "hle_lci", "UCI": "hle_uci",
        "Proportion (%)": "pct_life_in_good_health",
        "LE imputed": "le_imputed_age_groups", "Health prevalence imputed": "health_prev_imputed",
    })
    le = x.parse("1", header=6).rename(columns={"Area code": "area_code", "Sex": "sex", "LE": "le",
                                                "LCI": "le_lci", "UCI": "le_uci"})
    implaus = x.parse("4", header=6).rename(columns={"Area code": "area_code", "Sex": "sex", "LE": "le_implausible"})

    df = hle.merge(le[["area_code", "sex", "le", "le_lci", "le_uci"]], on=["area_code", "sex"], how="left")
    df["period"] = "2019 to 2023"
    df["source"] = "ONS hslemsoa.xlsx (30 Jul 2026)"
    df = df[["source", "period", "country", "area_type", "area_code", "area_name", "sex",
             "hle", "hle_lci", "hle_uci", "pct_life_in_good_health", "le", "le_lci", "le_uci",
             "le_imputed_age_groups", "health_prev_imputed"]]

    # The excluded MSOA(s) exist in the LE outlier sheet but have no HLE row at all
    # in sheet 2. Carry them as explicit rows with hle = NaN and a reason, so the
    # count of English MSOAs in Silver equals the count of English MSOAs in the
    # geography (6,856) rather than silently being one short.
    ex = implaus[["Country", "Area type", "area_code", "Area name", "sex", "le_implausible"]].rename(
        columns={"Country": "country", "Area type": "area_type", "Area name": "area_name"})
    ex["period"] = "2019 to 2023"
    ex["source"] = df["source"].iat[0]
    ex["hle_excluded_reason"] = "LE implausible (ONS outer-fence rule, sheet 4); ONS publishes no HSLE"
    df = pd.concat([df, ex], ignore_index=True)
    df["hle_excluded_reason"] = df["hle_excluded_reason"].fillna("")

    assert not df.duplicated(["area_code", "sex"]).any(), "ONS: grain violated (area_code x sex)"
    assert set(df["sex"]) == {"Male", "Female"}
    return df


def silver_fingertips() -> pd.DataFrame:
    d = pd.read_csv(FT_CSV)
    d = d.rename(columns={
        "Area Code": "area_code", "Area Name": "area_name", "Area Type": "area_type",
        "Sex": "sex", "Time period": "period", "Value": "hle",
        "Lower CI 95.0 limit": "hle_lci", "Upper CI 95.0 limit": "hle_uci",
        "Value note": "value_note",
    })
    # The API returns England twice (once as a parent row, once as an area) - identical values.
    d = d.drop_duplicates(["area_code", "sex"])
    d["source"] = "OHID Fingertips indicator 94359 (2 Sep 2026)"
    d = d[["source", "period", "area_type", "area_code", "area_name", "sex", "hle", "hle_lci", "hle_uci", "value_note"]]
    assert not d.duplicated(["area_code", "sex"]).any(), "Fingertips: grain violated (area_code x sex)"
    return d


def main() -> None:
    ons = silver_ons()
    ft = silver_fingertips()
    ons.to_parquet(OUT / "hle_ons.parquet", index=False)
    ft.to_parquet(OUT / "hle_fingertips.parquet", index=False)

    eng_msoa = ons[(ons.country == "England") & (ons.area_type == "MSOA")]
    print("ONS rows:", len(ons), "| area types:", ons.area_type.value_counts().to_dict())
    print("ONS English MSOAs:", eng_msoa.area_code.nunique(), "| rows with HLE:", eng_msoa.hle.notna().sum(),
          "| excluded:", (eng_msoa.hle_excluded_reason != "").sum())
    print("Fingertips rows:", len(ft), "| area types:", ft.area_type.value_counts().to_dict(),
          "| MSOAs:", ft[ft.area_type == "MSOA"].area_code.nunique(), "| null HLE:", ft.hle.isna().sum())


if __name__ == "__main__":
    main()
