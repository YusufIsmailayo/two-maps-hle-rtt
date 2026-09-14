"""
Silver: the only published residence -> provider crosswalk.

OHID's acute trust catchment populations (April 2026), Table 2: for each
MSOA (2021) of residence and each acute trust, the number of patients
admitted over three pooled financial years, the share of that MSOA's
admitted patients who went to that trust, and OHID's own "first past the
post" (FPTP) flag marking the trust with the largest share.

Grain (asserted): admission_type x catchment_year x msoa_code x trust_code,
where admission_type is all / elective / emergency (Tables 2, 3, 4). RTT is
an elective measure, so Gold joins on the elective catchment and uses the
all-admissions one as the comparison.

Only the 2024 catchment year (HES FY2022/23-2024/25) is carried forward to
Gold - the most recent, and the one nearest the July 2026 RTT snapshot.
Rounding/suppression from the source is kept as published: counts are to
the nearest 5, trusts with <8 admissions from an MSOA are absent, and the
share is as OHID rounded it (3 d.p.).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BRONZE_DIR, SILVER_DIR  # noqa: E402

ODS = BRONZE_DIR / "ohid_trust_catchment_2026-04" / "nhs-acute-hospital-trust-catchment-populations-data_tables-april-2026.ods"
OUT = SILVER_DIR / "catchment"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    x = pd.ExcelFile(ODS, engine="odf")
    frames = []
    for sheet in ["All_admissions", "Elective", "Emergency"]:
        frames.append(x.parse(sheet, header=2))
    t2 = pd.concat(frames, ignore_index=True).rename(columns={
        "Catchment year": "catchment_year", "Admission type": "admission_type",
        "Trust code": "trust_code", "Trust name": "trust_name", "MSOA21CD": "msoa_code",
        "Patients admitted": "patients_admitted", "Total patients": "msoa_total_patients",
        "Patients admitted as a proportion of total patients": "share_of_msoa_patients",
        "Trust total catchment population": "trust_catchment_pop",
        "MSOA21total catchment": "msoa_catchment_to_trust",
        "First past the post (FPTP)": "fptp", "Percentage admitted category": "share_band",
    })
    t2["admission_type"] = t2.admission_type.str.replace(" Admissions", "", regex=False).str.lower()  # all / elective / emergency
    assert set(t2.admission_type) == {"all", "elective", "emergency"}, set(t2.admission_type)
    assert not t2.duplicated(["admission_type", "catchment_year", "msoa_code", "trust_code"]).any(), "grain violated"
    t2["fptp"] = t2.fptp.astype(bool)

    t7 = x.parse("Trust_area_lookup", header=2)
    t7.columns = [c.strip() for c in t7.columns]
    t7 = t7.rename(columns={
        "Trust code": "trust_code", "Trust name": "trust_name", "Trust type": "trust_type",
        "Lower super output area code (LSOA21CD)": "hq_lsoa_code",
        "Lower tier local authority code (LTLA21CD)": "hq_ltla_code",
        "Lower tier local authority name (LTLA21NM)": "hq_ltla_name",
        "Statistical region name (RGN09NM)": "hq_region_name",
    })[["trust_code", "trust_name", "trust_type", "hq_lsoa_code", "hq_ltla_code", "hq_ltla_name", "hq_region_name"]]
    assert t7.trust_code.is_unique

    t2.to_parquet(OUT / "msoa_trust_admissions.parquet", index=False)
    t7.to_parquet(OUT / "trust_lookup.parquet", index=False)

    print("rows:", len(t2), "| years:", sorted(t2.catchment_year.unique()), "| trusts:", t2.trust_code.nunique(),
          "| MSOAs:", t2.msoa_code.nunique())
    for typ, y in t2[t2.catchment_year == 2024].groupby("admission_type"):
        fp = y[y.fptp]
        print(f"2024 {typ}: MSOAs with exactly one FPTP trust: {(fp.groupby('msoa_code').size() == 1).sum()} of {y.msoa_code.nunique()}"
              f" | FPTP share quantiles: {fp.share_of_msoa_patients.quantile([.1, .5, .9]).round(3).to_dict()}"
              f" | trusts per MSOA median: {y.groupby('msoa_code').size().median():.0f}")
    print("trust types:", t7.trust_type.value_counts().to_dict())


if __name__ == "__main__":
    main()
