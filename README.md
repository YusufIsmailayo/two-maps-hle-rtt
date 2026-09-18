# Two Maps — healthy life expectancy by neighbourhood vs RTT waiting times by provider

A Bronze → Silver → Gold pipeline (Python, pandas, Parquet) built to test a
claim *before* writing about it: that England's two halves of the "postcode
lottery" — healthy life expectancy (HLE), published by where you live, and
RTT waiting-time performance, published by where you are treated — cannot be
cleanly joined, and that the failure to join is itself the finding.

**Short version of what the data said:** one of the three claims holds
outright, one is false as stated and true in a more useful form, and the
third is answered by a number rather than an assumption. Details in
[docs/findings.md](docs/findings.md).

## Sources (all open data, all in `data/bronze/*/metadata.json` with SHA-256)

| Source | What | Grain | Date |
|---|---|---|---|
| ONS, *Health state life expectancy estimates for MSOAs, England and Wales: 2019 to 2023* | HLE, DFLE, LE at birth by sex; Census 2021 health prevalence, Sullivan method | MSOA (2021) | 30 Jul 2026 |
| OHID Local health (Fingertips), indicator 94359 | The same HLE, as redistributed by OHID | MSOA (2021) | 2 Sep 2026 |
| NHS England, RTT full CSV extracts, April–July 2026 | Incomplete pathways by weekly wait band | provider × commissioner × treatment function | monthly, latest 10 Sep 2026 |
| ONS Open Geography Portal | LSOA21 → SICBL → ICB → NHSER → LAD (Apr 2026); OA21 → LSOA → MSOA (Apr 2023); LAD → Region (Dec 2024) | LSOA / OA / LAD | Apr 2026 |
| OHID, *NHS acute (hospital) trust catchment populations: April 2026* | Patients admitted by MSOA of residence × acute trust, with first-past-the-post flag; all / elective / emergency | MSOA (2021) × trust | 28 Apr 2026 |

## Reconciliation gate (`src/pipeline/03_reconciliation_gate.py`)

HLE is a life-table quantity, not an additive one, so "rebuild the England
figure" means three independent checks, all of which pass
(`data/gold/00_reconciliation/reconciliation.csv`):

- **A.** Fingertips England HLE = ONS England HLE: **65.1 (male), 66.5 (female)**, CIs identical.
- **B.** All 13,712 English MSOA × sex rows identical between Fingertips and ONS; the one MSOA-sex ONS excluded as implausible (Barnet 042, male, LE 97.1) is absent from both.
- **C.** The ONS bulletin's distribution statistics reproduce from the Silver rows: median 65.3 / 66.8, IQR 7.4 / 7.8, 10th–90th percentile 57.7–71.0 / 58.6–72.6. (One 0.1-year rounding artefact on the male interdecile range — ONS computes it from unrounded values — is tolerated and recorded, not hidden.)
- **D.** RTT (July 2026): **7,131,685 incomplete pathways, matched exactly** against NHS England's published Incomplete-Provider-Jul26 workbook. 65.3% within 18 weeks and 108,263 over 52 weeks, both sitting below the statistical press notice's 65.4% / 111,379, which adds estimates for the three non-submitting acute trusts and Cora Health MSK.

The Census-2021-based HLE (65.1) is **not** the APS-based national HLE that
is usually quoted (~61–62). ONS states they are not comparable.

This gate previously skipped check D in silence: it runs at step 03, and RTT
Silver is not written until step 05, so on a clean clone the RTT reconciliation
never executed. It now says so and exits non-zero. That defect is why the two
corrections below survived to a published draft.

## Corrections after audit

An independent audit of the first published commit found two pipeline defects.
Both are fixed; both are worth recording, because both were invisible to a
pipeline full of assertions.

**Unidentified commissioner rows.** The RTT full extract carries rows with
commissioner code `NONC` — real activity with no identified commissioner.
NHS England's published provider workbook excludes them; my rollup did not.
July 2026 totalled 7,162,692 pathways instead of the published 7,131,685, a
difference of exactly 31,007. `05_silver_rtt.py` now drops them from the
published measure and prints what it dropped.

**A merger read as a non-submission.** North Bristol NHS Trust (`RVJ`) merged
into Bristol NHS Foundation Trust (`RA7`) on 1 July 2026. Joining on trust
code alone, `RVJ` simply vanishes — indistinguishable from a trust that failed
to report. The evidence is unambiguous: RA7 goes from 50,868 pathways in June
to 95,525 in July, in the month RVJ's 42,365 disappear. 61 neighbourhoods were
wrongly recorded as having no waiting-time figure; unmatched MSOAs fall from
228 to **167**. `_common.py` now carries a dated succession map applied per
period, so April–June still treat RVJ and RA7 as the two distinct trusts they
were.

Worth naming the shape of the second error: `08_gold_crosswalk.py` already held
a hard-coded `NON_SUBMITTERS_JUL26` constant with the correct list — Sheffield,
Torbay, Plymouth and Cora Health MSK — while the join beside it derived a
different list including North Bristol. Two files in the same repository
contradicted each other and nothing caught it. Sheffield and Torbay, meanwhile,
are absent from all four months, not just July; the drop from 6,748 to 6,689
matched MSOAs in July is the Bristol merger plus Plymouth.

## Pipeline

```
src/pipeline/
  01_bronze_ingest.py          five raw sources, unmodified, with provenance
  02_silver_hle.py             ONS and Fingertips HLE on one schema; grain MSOA × sex asserted
  03_reconciliation_gate.py    the gate above; exits non-zero on failure
  04_silver_geography.py       MSOA → LAD → region → SICBL → ICB → NHS region; ICB nesting asserted
  05_silver_rtt.py             period × provider RTT, April–July 2026; 18-week and 52-week shares rebuilt from bands
  06_silver_catchment.py       MSOA × trust admissions crosswalk; grain asserted
  07_gold_spread.py            within-ICB vs between-ICB HLE spread, by sex
  08_gold_crosswalk.py         four crosswalk routes attempted and measured
  09_gold_joined.py            what the join says once you make it
  10_gold_chart.py             the strip chart
  11_gold_months.py            the RTT-dependent results repeated for each of the four months
  12_gold_specialty.py         the national 18-week picture by treatment function
  13_gold_ci_robustness.py     does the within-ICB finding survive the estimates' 95% intervals
```

Run in order: `for f in src/pipeline/0*.py src/pipeline/1*.py; do python3 $f || break; done` — or follow the three notebooks in `notebooks/` (`01_bronze`, `02_silver`, `03_gold`), which run the same steps and inspect what each produced.

## Headline numbers (all reproducible from `data/gold/`)

- 6,856 English MSOAs; 36 ICBs (post-April-2026); 533 RTT providers of which 151 NHS trusts; 134 acute trusts in the catchment file.
- Spread of the 36 ICB medians: **9.2 years (male), 10.0 (female)**. Median within-ICB range: **20.3 / 20.5 years**. Narrowest ICB (Cornwall): 14.2 / 15.6. **All 36 ICBs** have an internal range, interdecile range *and* IQR wider than the corresponding between-ICB measure. 81–82% of MSOA HLE variance is within ICBs.
- A residence → trust crosswalk exists (OHID catchment file). The dominant trust takes a median **76%** of a neighbourhood's elective admissions (p10 52%, p90 91%); for 8.1% of MSOAs it takes under half. Using it as if it were clean changes a neighbourhood's 18-week figure by a median 0.8 pp, p90 3.0 pp, max 12.8 pp.
- Within a single **local authority**, the median HLE range is **13.3 years (male) / 13.6 (female)** across the 277 LADs with at least ten MSOAs; 144 span 13 years or more internally; widest is Wirral, 47.8 to 73.2 (male). That range is a distance between a council's two *extreme* neighbourhoods. Two neighbourhoods picked at random inside the same council differ by a median **3.8 years (male) / 4.0 (female)**, and only 4.0% / 5.0% of within-council pairs differ by 13 years or more. Both statistics are in `lad_spread_summary.csv`; conflating them is the error the audit caught in the first draft.
- No treatment function meets the 92% standard. Oral surgery is furthest from it: **54.2%** within 18 weeks in July 2026, 37.8 pp short (`data/gold/06_specialty/`).
- 7.2% of the national waiting list sits at providers with no residence footprint at all (403 of 533 providers, mostly independent sector). **167** MSOAs' dominant trust did not submit RTT data for July 2026 — Sheffield, Torbay and Plymouth.
- ICB footprints leak: **14.0%** of elective acute admissions are treated by a trust parented by a different ICB from the patient's; Staffordshire and Stoke-on-Trent 47%.
- Once joined, MSOA HLE and the dominant trust's 18-week share are uncorrelated: **r = −0.004 (male), −0.002 (female)** in July 2026 across 6,689 MSOAs; the admissions-weighted version gives −0.004 / −0.004; July's Spearman coefficients are marginally *positive* (0.007 / 0.010). Across April–July 2026 Pearson r runs −0.020 to −0.004 (male) and −0.016 to −0.002 (female) (`data/gold/05_months/by_month.csv`).
- Two different ways of comparing the worst- and best-waiting quartiles of trusts, because they disagree and the distinction matters: the **median of trust-level medians** is 65.8 vs 65.1 male years, while **pooling the actual neighbourhoods** those trusts serve gives 65.0 vs 65.2 (1,890 vs 1,352 MSOAs). Neither shows a meaningful gradient, and the pooled one runs mildly *against* the "poorer areas wait longer" story.
- The within-ICB finding survives the estimates' uncertainty. Taking the *lower* bound of each ICB's healthiest neighbourhood against the *upper* bound of its least healthy — shrinking every internal range by about two interval widths before comparing — **all 36 ICBs still exceed** the between-ICB median spread (minimum 10.7 male / 11.6 female against 9.2 / 10.0). The same penalty applied to the interdecile leaves only 14 / 13 of 36, and that version is noted rather than buried (`data/gold/07_ci_robustness/`).

![ICB strip chart](data/gold/04_chart/icb_strip_hle.png)

## Re-running this

`pip install -r requirements.txt`, then the run line above. `06_silver_catchment.py`
parses an 18 MB ODS workbook and wants roughly 4 GB of RAM to do it; on a small
container it is the step that gets killed. Bronze is not in
git — the raw payloads are re-downloaded from the URLs in each
`metadata.json`, and the recorded SHA-256 tells you whether you got the same
bytes I did.

One caveat on that: NHS England publishes each month's RTT extract at a URL
with a random suffix (`…Full-CSV-data-file-Jul26-ZIP-4M-97ylx5.zip`), and
those links are rotated and retired. If Bronze ingest 404s on the RTT
sources, the file has moved rather than vanished — find the month's extract
on the NHS England RTT statistics page and update the URL in
`01_bronze_ingest.py`. The hash in `metadata.json` still tells you whether
the replacement is the same file.

## Licensing

Code: MIT (`LICENSE`). Data: all five sources are Crown copyright, published
under the [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/);
the Gold tables committed here are derived from them under the same terms
and should be attributed to ONS, OHID and NHS England as listed above.

## Guardrails

Published open data only; no pupil- or patient-level records. OHID's rounding
(nearest 5), suppression (<8 admissions) and "<5% not shown" flags are kept
as published and not back-calculated. The one ONS-excluded MSOA-sex is
carried with an explicit reason, not dropped silently.
