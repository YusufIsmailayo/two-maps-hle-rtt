"""
Bronze ingest for the Two Maps pipeline.

Downloads every raw source unmodified into data/bronze/<source>/ and stamps
each with a SHA-256 + metadata.json (source URL, publisher, publication date,
what the file is and at what grain). Nothing is parsed here.

Sources
-------
1. ONS  - Health state life expectancy estimates for MSOAs, E&W: 2019 to 2023
          (hslemsoa.xlsx, released 30 Jul 2026). The origin of the HLE figures.
2. OHID - Local health Fingertips profile, indicator 94359 "Healthy life
          expectancy at birth 2021 Census based", MSOA + England rows via the
          Fingertips API (loaded 2 Sep 2026). The redistribution the article
          is anchored on; reconciled against (1) in Silver.
3. NHSE - Referral to Treatment full CSV extracts, April-July 2026. Provider-
          level incomplete pathways by treatment function. July is the
          headline month; the earlier three exist to show the Gold result is
          not a one-month artefact.
4. ONS  - Open Geography Portal lookups: LSOA21 -> SICBL/ICB/NHSER/LAD (Apr
          2026), OA21 -> LSOA21 -> MSOA21 -> LAD23 (Apr 2023), LAD -> Region
          (Dec 2024).
5. OHID - NHS acute (hospital) trust catchment populations, April 2026 (ODS).
          Table 2 is MSOA21 x acute trust x patients admitted - the only
          published residence -> provider crosswalk.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BRONZE_DIR, download, sha256_of, write_metadata  # noqa: E402

HUB = "https://hub.arcgis.com/api/v3/datasets/{id}/downloads/data?format=csv&spatialRefId=4326&where=1%3D1"

RTT_MONTHS = [
    # (slug month, label, published, zip URL) - April-July 2026 so the Gold result can be checked month to month
    ("2026-04", "April 2026", "2026-06-11", "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/06/Full-CSV-data-file-Apr26-ZIP-3M-X7gGnn.zip"),
    ("2026-05", "May 2026", "2026-07-09", "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Full-CSV-data-file-May26-ZIP-3M-3jBgba.zip"),
    ("2026-06", "June 2026", "2026-08-13", "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/08/Full-CSV-data-file-Jun26-ZIP-3M-6jPlxd.zip"),
    ("2026-07", "July 2026", "2026-09-10", "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/09/Full-CSV-data-file-Jul26-ZIP-4M-97ylx5.zip"),
]

SOURCES = [
    {
        "slug": "ons_hsle_msoa",
        "publisher": "Office for National Statistics",
        "publication_name": "Health state life expectancy estimates for Middle layer Super Output Areas, England and Wales: 2019 to 2023",
        "published_date": "2026-07-30",
        "source_page": "https://www.ons.gov.uk/peoplepopulationandcommunity/healthandsocialcare/healthandlifeexpectancies/datasets/healthstatelifeexpectancyestimatesformiddlelayersuperoutputareasenglandandwales",
        "files": [
            ("hslemsoa.xlsx",
             "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/healthandsocialcare/healthandlifeexpectancies/datasets/healthstatelifeexpectancyestimatesformiddlelayersuperoutputareasenglandandwales/2019to2023/hslemsoa.xlsx",
             "Sheets 1-3: LE / HLE / DFLE at birth by sex, MSOA21 + England + Wales. Sheet 4: MSOAs with implausible LE."),
        ],
        "grain": "MSOA (2021) x sex; national rows for England and Wales",
        "note": "Sullivan method; health prevalence from Census 2021 general health; deaths and MYE pooled 2019-2023. ONS: NOT comparable with the APS-based national HLE series.",
    },
    {
        "slug": "fingertips_hle_msoa",
        "publisher": "Office for Health Improvement and Disparities",
        "publication_name": "Local health, public health data for small geographic areas - September 2026 update",
        "published_date": "2026-09-02",
        "source_page": "https://fingertips.phe.org.uk/profile/local-health",
        "files": [
            ("hle_94359_msoa.csv",
             "https://fingertips.phe.org.uk/api/all_data/csv/by_indicator_id?indicator_ids=94359&child_area_type_id=3&parent_area_type_id=15",
             "Indicator 94359 'Healthy life expectancy at birth 2021 Census based'; area type 3 (MSOA - codes are 2021 MSOAs) with England parent rows."),
            ("indicator_94359_metadata.json",
             "https://fingertips.phe.org.uk/api/indicator_metadata/by_indicator_id?indicator_ids=94359",
             "Indicator metadata as served by the Fingertips API."),
        ],
        "grain": "MSOA (2021) x sex; England rows",
        "note": "OHID redistributes the ONS MSOA HSLE release; the Fingertips England row is the figure the article calls 'OHID's published England HLE'.",
    },
    {
        "slug": "ons_geography_lookups",
        "publisher": "Office for National Statistics (Open Geography Portal)",
        "publication_name": "Open Geography Portal lookups",
        "published_date": "2026-04 (ICB/LSOA lookup); 2023-04 (OA-LSOA-MSOA-LAD); 2024-12 (LAD-Region)",
        "source_page": "https://geoportal.statistics.gov.uk/",
        "files": [
            ("LSOA21_SICBL26_ICB26_NHSER26_LAD26_EN_LU.csv",
             HUB.format(id="bebf631bb1ac40cf9ec7dc060897ca99_0"),
             "LSOA (2021) to SICBL to ICB to NHSER to LAD (April 2026) Lookup in EN. CDH columns are ODS codes."),
            ("OA21_LSOA21_MSOA21_LAD23_EN_LU.csv",
             HUB.format(id="821c4e07c07042e0bee806dfec5a1f77_0"),
             "Output Area (2021) to LSOA to MSOA to LEP to LAD (April 2023) Best Fit Lookup in EN. Used for LSOA21 -> MSOA21 nesting."),
            ("LAD24_RGN24_EN_LU.csv",
             HUB.format(id="3959874c514b470e9dd160acdc00c97a_0"),
             "Local Authority District to Region (December 2024) Lookup in EN."),
        ],
        "grain": "LSOA21 / OA21 / LAD",
        "note": "ICBs reorganised April 2026 (42 -> 36). LAD vintages differ between lookups (LAD23 vs LAD26); Silver checks coverage explicitly.",
    },
    {
        "slug": "ohid_trust_catchment_2026-04",
        "publisher": "Office for Health Improvement and Disparities",
        "publication_name": "NHS acute (hospital) trust catchment populations: April 2026",
        "published_date": "2026-04-28",
        "source_page": "https://www.gov.uk/government/statistics/nhs-acute-hospital-trust-catchment-populations-april-2026",
        "files": [
            ("nhs-acute-hospital-trust-catchment-populations-data_tables-april-2026.ods",
             "https://assets.publishing.service.gov.uk/media/6a199144050971fbebf3bc3f/nhs-acute-hospital-trust-catchment-populations-data_tables-april-2026.ods",
             "Table 2 (All_admissions): MSOA21 of residence x acute trust x patients admitted x share x first-past-the-post flag, catchment years 2023 and 2024. Table 7: trust lookup (type, HQ LSOA, LTLA, region)."),
        ],
        "grain": "MSOA (2021) x acute trust x catchment year",
        "note": "HES APC, 3-year pooled (FY2021/22-2023/24 for 2023; FY2022/23-2024/25 for 2024). Counts rounded to nearest 5; trusts with <8 admissions from an MSOA suppressed; shares <5% flagged 'not shown'. Acute trusts only (134).",
    },
]


for _slug, _label, _pub, _url in RTT_MONTHS:
    SOURCES.append({
        "slug": f"nhse_rtt_{_slug}",
        "publisher": "NHS England",
        "publication_name": f"Consultant-led Referral to Treatment Waiting Times Data 2026-27 - {_label}",
        "published_date": _pub,
        "source_page": "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2026-27/",
        "files": [(_url.rsplit("/", 1)[-1], _url,
                   "Full extract: provider x commissioner x RTT part x treatment function x weekly wait bands (0-104+).")],
        "grain": f"provider x commissioner x RTT part x treatment function (month = {_label})",
        "note": "Provider Parent Org Code is the provider's ICB (ODS code, post April 2026 reorganisation - 36 ICBs). "
                "Publication dates for Apr-Jun are the scheduled second-Thursday releases; the July date is confirmed from the press notice.",
    })


def main() -> None:
    for src in SOURCES:
        folder = BRONZE_DIR / src["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        files_meta = []
        for filename, url, desc in src["files"]:
            dest = folder / filename
            if dest.exists():
                print(f"  exists   {src['slug']}/{filename}")
            else:
                print(f"  download {src['slug']}/{filename}")
                download(url, dest)
            files_meta.append({
                "filename": filename,
                "source_url": url,
                "description": desc,
                "bytes": dest.stat().st_size,
                "sha256": sha256_of(dest),
            })
        write_metadata(
            folder,
            publisher=src["publisher"],
            publication_name=src["publication_name"],
            published_date=src["published_date"],
            source_page=src["source_page"],
            grain=src["grain"],
            note=src["note"],
            files=files_meta,
        )
        print(f"  metadata {src['slug']}/metadata.json")


if __name__ == "__main__":
    main()
