# Findings against the three claims

Every number here is in `data/gold/`. Nothing below is estimated.

> **Revised after audit.** An independent audit of the first published commit
> found two pipeline defects — unidentified-commissioner (`NONC`) rows retained
> in the RTT rollup, and the North Bristol/Bristol trust merger read as a
> non-submission — plus three places where this document described a statistic
> it was not actually computing. All are corrected below and in the code; the
> README records what changed. The three claims are unaffected in substance.

## Claim 1 — "There is no clean MSOA-of-residence → treatment-provider crosswalk"

**False as stated; true in a more precise form.**

There *is* a published crosswalk: OHID's *NHS acute (hospital) trust
catchment populations* (April 2026), Table 2/3/4 — every MSOA (2021) ×
every acute trust, patients admitted (HES APC, three pooled financial
years), the trust's share of that MSOA's admitted patients, and OHID's own
"first past the post" flag for the dominant trust. All 6,856 MSOAs have
exactly one FPTP trust for all, elective and emergency admissions.

What is true is that it is not *clean*, and the pipeline measures exactly
how unclean (`data/gold/02_crosswalk/crosswalk_findings.csv`):

| Route | What it is | What breaks |
|---|---|---|
| **A. ICB footprint** | MSOA → LSOA → ICB (Apr 2026); provider → parent ICB (RTT file) | Keys join 36/36. But 14.0% of elective admissions are treated by a trust parented by a different ICB (all admissions 13.1%); resident-view leakage median 13.8%, max 47.0% (Staffordshire & Stoke — Burton, Wolverhampton, UHB). 22 of 130 trusts take >25% of patients from outside their parent ICB; Frimley 80%, Royal Marsden 82%. Five MSOAs straddle two ICBs. |
| **B. First past the post** | MSOA → dominant elective trust → RTT provider | Dominant trust takes median 76% of elective admissions (p10 52%, p90 91%); 556 MSOAs (8.1%) under half. 126 MSOAs change dominant trust between elective and all-admissions. 167 MSOAs' dominant trust (Sheffield, Torbay, Plymouth) submitted no RTT data for July 2026. 7.2% of the national waiting list is at 403 providers with no residence footprint (ISPs 325k pathways, other non-trust 117k, non-acute NHS 70k). Treating the join as clean changes the MSOA's 18-week figure by median 0.8 pp, p90 3.0 pp, max 12.8 pp. |
| **C. Commissioner** | MSOA → LSOA → Sub-ICB location → RTT commissioner | 106 of 121 commissioner codes are SICBLs; 1.7% of pathways have a non-SICBL commissioner (specialised commissioning). 22 MSOAs straddle two SICBLs. The deeper problem: a SICBL is a GP-registered population (~500k), not a residence, and it records who pays, not where you are treated. |
| **D. Trust address** | trust HQ LSOA → MSOA | 131 MSOAs contain a trust HQ. A point, not a population. The naive spatial join. |

The "version that looked like it worked" is B. It works better than the
thesis assumed — well enough that the article cannot say the join is
impossible. What it can say is that the join is a modelling choice with a
measured error, built on admissions rather than pathways, covering acute
trusts only, and unavailable for 228 neighbourhoods in any month a large
trust fails to submit.

## Claim 2 — "Within-ICB HLE spread is wider than between-ICB spread"

**True, without qualification, for both sexes and every measure**
(`data/gold/01_spread/spread_summary.csv`).

| | Male | Female |
|---|---|---|
| Spread of the 36 ICB medians (max − min) | 9.2 | 10.0 |
| Median within-ICB range | 20.3 | 20.5 |
| Narrowest within-ICB range (Cornwall) | 14.2 | 15.6 |
| Widest within-ICB range | 28.2 (Cheshire & Merseyside) | 27.0 (Humber & N. Yorks) |
| IQR of ICB medians | 3.4 | 3.5 |
| Median within-ICB IQR | 6.2 | 6.6 |
| ICBs whose internal range > between-ICB range | 36 of 36 | 36 of 36 |
| ICBs whose internal IQR > IQR of medians | 36 of 36 | 36 of 36 |
| Share of MSOA HLE variance that is within-ICB | 81.6% | 80.7% |

One level down, the same thing is true of the geography readers actually
recognise (`data/gold/01_spread/lad_spread_summary.csv`). Across the 277
local authorities with at least ten MSOAs, the median internal HLE range is
**13.3 years for men, 13.6 for women**; 144 of those LADs span 13 years or
more between their best and worst neighbourhood. The widest is Wirral: 47.8
to 73.2 for men, a 25.4-year gap inside one council area.

**That range is a distance between extremes, and the first draft used it as
though it were a typical comparison.** Two neighbourhoods picked at random
inside the same council differ by a median of **3.8 years for men, 4.0 for
women** (p90 10.1 / 10.6), and only **4.0% / 5.0%** of within-council pairs
differ by 13 years or more. Both figures now sit in the same file. The
article's opening has to say which one it means: thirteen years apart is a
real pair of neighbourhoods in most councils, but it is not the average
pair.

**Does the ICB finding survive the uncertainty?**
(`data/gold/07_ci_robustness/ci_robustness.csv`.) The MSOA estimates carry
95% intervals with a median width of 2.9 years, and the chart plots points.
So: take each ICB's healthiest neighbourhood at its *lower* bound and its
least healthy at its *upper* bound — shrinking every internal range by about
two interval widths — and compare with the between-ICB median spread.
**All 36 ICBs still exceed it**, minimum 10.7 (M) / 11.6 (F) against 9.2 /
10.0. The headline claim holds under a deliberately hostile test.

Two honest qualifications. This is a fixed-extremes check on individual
intervals, not a simultaneous confidence band over all 6,856 neighbourhoods.
And it is not symmetric: the between-ICB side stays on point estimates, so
the penalty falls only on the within-ICB side. Applying the same shrinkage
to the interdecile instead of the range leaves only 14 of 36 (M) and 13 of
36 (F) — that measure does not survive, and it is recorded rather than
dropped.

Robustness: against ONS's own ICB-level HLE on the pre-April-2026 42 ICBs
(an independent between-ICB benchmark, range 8.6 / 9.5), the result is the
same. Top ICB by median: Thames Valley (69.5 / 71.3); bottom: Birmingham &
Solihull (60.3) / Black Country (61.3).

Caveat carried into the article: ranges are sensitive to single extreme
MSOAs (max HLE 78.3 M / 81.2 F; min 47.7 / 49.0). That is why IQR and
interdecile are reported alongside — they say the same thing.

## Claim 3 — "ICB footprints solve the join problem"

**They do not, and the pipeline gives two numbers for why**
(`data/gold/02_crosswalk/A_icb_table.csv`, `A_icb_resident_leakage.csv`).

1. An ICB is not a closed system for treatment: 14% of elective admissions
   cross ICB lines nationally, 47% in the worst case, and the London
   specialist trusts draw most of their patients from outside their
   parent ICB.
2. Even where it were closed, the ICB is the wrong unit for the outcome:
   ~81% of HLE variation is inside ICBs. An ICB-level 18-week figure is
   being attached to neighbourhoods that differ from each other by up to
   28 years of healthy life.

At ICB level the correlation between HLE median and providers' 18-week
share is −0.17 (M) / −0.14 (F) across 36 points — weak and, if anything,
the wrong sign for the "poor areas wait longer" story.

## What the join says once you make it (`data/gold/03_joined/`)

This is the finding the original outline did not anticipate. Route B is
feasible enough to try, so the pipeline tries it: every MSOA gets its
dominant elective trust's 18-week share, and an admissions-weighted share
across all the trusts it uses.

- Pearson r, MSOA HLE vs dominant trust's 18-week share: **−0.004 (M), −0.002 (F)** for July 2026, n = 6,689. Spearman: +0.007 / +0.010 — marginally positive, and near enough zero that the sign is not worth reading. Admissions-weighted: −0.004 / −0.004.
- Not a one-month artefact (`data/gold/05_months/by_month.csv`):

  | month | England ≤18 wks | MSOAs with an RTT figure | r (M) | r (F) | ICB-level r (M) | ICB-level r (F) |
  |---|---|---|---|---|---|---|
  | Apr 2026 | 65.0% | 6,748 | −0.020 | −0.016 | −0.15 | −0.11 |
  | May 2026 | 65.6% | 6,748 | −0.019 | −0.015 | −0.15 | −0.11 |
  | Jun 2026 | 65.8% | 6,748 | −0.017 | −0.014 | −0.18 | −0.15 |
  | Jul 2026 | 65.3% | 6,689 | −0.004 | −0.002 | −0.16 | −0.12 |

  July's lower MSOA count is the Bristol merger (61 MSOAs) plus Plymouth (59)
  — not Sheffield, which is absent from all four months, as is Torbay.
- 73–74% of MSOA HLE variance is within trust catchments.
- Median within-catchment HLE range (trusts with ≥10 MSOAs): 16.7 (M) / 17.4 (F) years, against a 13.5 / 14.5 range of catchment medians.
- Trusts' 18-week share ranges 34 pp (IQR 7 pp). Comparing the worst- and best-waiting quartiles of trusts gives two different answers depending on the statistic, and the first draft named the wrong one: the **median of trust-level medians** is 65.8 vs 65.1 (M), each trust counting once; **pooling the neighbourhoods** those trusts actually serve gives 65.0 vs 65.2 (M) and 66.2 vs 66.9 (F), 1,890 against 1,352 MSOAs. No meaningful gradient either way, and the pooled version tilts mildly against the expected direction.

So the honest thesis is not "the two maps can't be joined, so nobody can
prove the link". It is: **the two maps can be joined, imperfectly but
defensibly, and when you do, there is no link at this level** — the
outcome lottery and the access lottery are drawn on different maps in a
stronger sense than a missing crosswalk. Where you live sets your healthy
years within a 20-year band that no provider figure explains; where you
are treated sets your wait within a 34-point band that has nothing to do
with the healthy years of the people waiting.

## Context: the specialty spread (`data/gold/06_specialty/`)

Not evidence for the thesis, but the reason a single national 18-week figure
is worth interrogating. In July 2026 **no treatment function met the 92%
standard**. Oral surgery was furthest from it at 54.2% within 18 weeks — 37.8
percentage points short — followed by ENT (57.6%) and plastic surgery
(59.5%). The best-performing, elderly medicine, still only reached 83.8%.
Every share is rebuilt from the weekly wait bands, and the specialties
reconcile to the provider-level England total for each month.

## What the data cannot say

- HLE 2019–2023 straddles the pandemic; five-year pooling; Census 2021 health prevalence assumed constant across the period.
- Not comparable with the APS-based national HLE (England ~61–62). The 65.1 / 66.5 here is the Census-based figure.
- RTT is a monthly snapshot; July 2026 is the headline month and three acute trusts plus one independent provider did not submit it. April–June are used only to check the result is stable.
- HLE describes 2019–2023; RTT describes 2026. The test is whether places with different *historical* healthy-life profiles are *currently* served by providers with systematically different waiting performance. It is not a test of whether waiting affects health.
- The catchment crosswalk is admissions, not RTT pathways; acute only; rounded to 5; <8 admissions suppressed.
- No causal claim in either direction. Zero correlation at neighbourhood-by-dominant-trust level does not mean waiting is unrelated to health for individuals.
