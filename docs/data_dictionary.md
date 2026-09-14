# Data dictionary

## Silver

### `hle/hle_ons.parquet` — grain: area_code × sex
| column | meaning |
|---|---|
| source, period | "ONS hslemsoa.xlsx (30 Jul 2026)", "2019 to 2023" |
| country, area_type | England/Wales; MSOA, Local Areas, Integrated Care Board (pre-Apr-2026, 42), Combined Authority, Region, Welsh Health Board, Country |
| area_code, area_name | ONS codes (E02… for MSOA) |
| sex | Male / Female |
| hle, hle_lci, hle_uci | healthy life expectancy at birth, years, 95% CI |
| pct_life_in_good_health | ONS "Proportion (%)" |
| le, le_lci, le_uci | life expectancy at birth (sheet 1) |
| le_imputed_age_groups, health_prev_imputed | ONS imputation flags |
| hle_excluded_reason | non-empty for the one MSOA-sex ONS excluded (sheet 4); hle is NaN |

### `hle/hle_fingertips.parquet` — grain: area_code × sex
Same measures from the Fingertips API (indicator 94359). `value_note` as served.

### `geography/msoa_geography.parquet` — grain: msoa_code (6,856)
| column | meaning |
|---|---|
| lad_code/name | LAD, April 2026 vintage (LSOA-level lookup) |
| region_code/name | ONS region (Dec 2024 lookup; Barnsley and Sheffield resolved by name after 2026 re-coding) |
| sicbl_code/ods/name, icb_code/ods/name, nhser_code/name | April 2026; `*_ods` are the ODS codes used in NHS files |
| n_lsoa, n_icb, n_sicbl | constituent LSOAs and the distinct ICBs/SICBLs among them |
| straddles_icb, straddles_sicbl | true if the MSOA's LSOAs sit in more than one; assignment is by LSOA majority |
| icb_name_short | "NHS … Integrated Care Board" trimmed |

### `rtt/rtt_provider.parquet` — grain: provider_code (533)
| column | meaning |
|---|---|
| provider_icb_ods/name | Provider Parent Org Code — the provider's ICB |
| total_waiting | incomplete pathways, sum of all wait bands (= "Total All") |
| within_18, over_52 | bands 0–18 weeks; bands >52 weeks |
| pct_within_18, pct_over_52 | recomputed, not published percentages |
| provider_kind | NHS trust (R-code) / independent sector (N-code) / other |

`rtt/rtt_provider_tfc.parquet` — same at provider × treatment function.

### `catchment/msoa_trust_admissions.parquet` — grain: admission_type × catchment_year × msoa_code × trust_code
| column | meaning |
|---|---|
| admission_type | all / elective / emergency (OHID Tables 2/3/4) |
| catchment_year | 2023 (HES FY21/22–23/24) or 2024 (FY22/23–24/25) |
| patients_admitted | unique patients from this MSOA admitted to this trust, rounded to 5 |
| msoa_total_patients | unique patients from this MSOA admitted anywhere |
| share_of_msoa_patients | the former / the latter, as OHID rounded it (3 dp) |
| fptp | OHID's first-past-the-post flag: the trust with the largest share |
| share_band | OHID's banding; "<5% not shown" |

`catchment/trust_lookup.parquet` — 134 acute trusts, type, HQ LSOA/LTLA/region.

## Gold

- `00_reconciliation/reconciliation.csv` — checks A–D, pass/fail, notes.
- `01_spread/icb_spread_by_sex.csv` — ICB × sex: n_msoa, min/p10/p25/median/p75/p90/max, iqr, range, interdecile, rank.
- `01_spread/spread_summary.csv` — within vs between, per sex and measure; variance split; ONS-42-ICB benchmark.
- `01_spread/msoa_hle_icb.parquet` — chart input.
- `02_crosswalk/crosswalk_findings.csv` — routes A–D, each test and result.
- `02_crosswalk/A_icb_table.csv` — ICB × HLE summary × RTT × leakage.
- `02_crosswalk/A_icb_resident_leakage.csv`, `A_trust_patient_leakage.csv`.
- `02_crosswalk/B_msoa_fptp_rtt.csv` — MSOA × dominant trust × RTT (FPTP and admissions-weighted) × HLE.
- `02_crosswalk/C_commissioner_codes.csv`.
- `03_joined/joined_summary.csv`, `msoa_joined.csv`, `trust_catchment_hle_{male,female}.csv`.
- `04_chart/icb_strip_hle.png`.
