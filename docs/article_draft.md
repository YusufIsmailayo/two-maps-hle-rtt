<!--
DRAFT v6 — 2 Nov 2026. PRE-PUBLICATION CHECKLIST:
  1. Delete this whole comment block.
  2. Strip every [bracketed/file.csv] source tag — search for "[0" — there are
     about a dozen. They exist so each figure can be checked against the repo.
  3. Insert data/gold/04_chart/icb_strip_hle.png at the [CHART] marker.

Three different statistics about the same thing, deliberately kept distinct:
  ~25 years — the gap between the two ends of Wirral, a real named pair
  13.3 years — the typical English council's full internal range
  ~4 years  — the difference between two neighbourhoods picked at random
              inside the same council
The opening leads on the first, the second paragraph gives the second, and the
third corrects for the fact that the first two are extremes. Do not let an
edit collapse them into one number.

v6 fixes, all verified against data/gold/ on 2 Nov 2026:
  - no-footprint share 7.1% -> 7.2% (stale: the NONC correction cut the
    denominator to 7,131,685, moving the share to 7.1728%)
  - the correlation n is 6,688 for men, 6,689 for women; the draft gave the
    female n for both
  - the opening's 73/48 are MALE figures and said so nowhere, which also left
    "widest council in England" unqualified — true for men, but Bradford is
    widest for women

Title: settled on the paradox mode. The original — "Refuse to Line Up" — is
not true of what the data showed, and writing around it would have been the
dishonest option.
-->

# Two Maps of England, Finally Lined Up

*Healthy life expectancy, now published for 6,856 neighbourhoods. Waiting times, published for 533 providers. I joined them. The join says nothing — and that is the finding.*

---

Somewhere in England this morning, two people are getting up in the same borough.

One of them lives in a neighbourhood where healthy life expectancy for men is 73 years. The other lives in a neighbourhood where it is 48. Same country. Same NHS. Same council, same bin collection, same local election. Twenty-five years between the two places, before either person is ill.

Those are real neighbourhoods and I can name them: Wirral 028 and Wirral 016 [01_spread/lad_spread.csv]. Forty other Wirral neighbourhoods sit between them. And the gap is not an artefact of small numbers — take the cautious end of each estimate, the bottom of one interval against the top of the other, and they are still twenty-two years apart.

Wirral is the widest council in England on that measure; for women the widest is Bradford, at 25.9 years. Either way it is not a freak. Of the 277 English local authorities large enough to measure, the typical one spans 13.3 years of healthy life between its best neighbourhood and its worst for men, 13.6 for women — and 144 and 148 of them respectively span thirteen years or more [01_spread/lad_spread_summary.csv].

Pick two neighbourhoods in the same council at random, though, and they differ by about four years — not thirteen, and nothing like twenty-five. The wide pair is real, and it sits inside most councils in England — but you have to go looking for the ends of the range to find it. You do not need to cross a county. You need to know which bus.

## What was published on 2 September

The Office for Health Improvement and Disparities added one thing to its Local health profile this month: healthy life expectancy for 2019 to 2023, for every middle-layer super output area in England. An MSOA is a statistical neighbourhood of roughly five to fifteen thousand people. There are 6,856 of them.

Healthy life expectancy is not life expectancy. It is the number of years a newborn could expect to live in what people themselves describe as good health, if the conditions of the period held for their whole life. The figures are ONS's, built from five years of deaths and the health question on the 2021 Census. For England as a whole: 65.1 years for men, 66.5 for women [00_reconciliation/reconciliation.csv] — the England-level estimate, which is not the same statistic as the median across England's neighbourhoods, 65.3 and 66.8. The pandemic sits inside every one of those numbers.

I had been waiting for this release. Last year I built a pipeline over NHS England's referral-to-treatment data — the waiting-time half of the postcode lottery — and the obvious question was always the one I couldn't answer: does living in a place that costs you healthy years also cost you time on the waiting list? The waiting-time figures are published by the trust that treats you. The health figures are published by the place you live. Nobody publishes the map that joins them.

So I set out to prove the map doesn't exist. That's not what happened.

## The access side, for scale

At the end of July 2026 there were 7.13 million open referral-to-treatment pathways in England [00_reconciliation/reconciliation.csv]. The standard says 92% of patients should have waited 18 weeks or less. In July, 65.3% had. In 108,263 cases the pathway had been open more than a year.

Those are the providers that actually reported; the national headline you'll see quoted is slightly higher because it adds estimates for four that didn't. Which figure you use turns out to matter, and I'll come back to it.

The 18-week share is not one number, it is 533 numbers, one per provider. Among the acute trusts that serve as the main hospital for at least ten neighbourhoods, it runs from about 50% to about 84% [03_joined/trust_catchment_hle_male.csv] — a 34-point spread. No treatment function in England met the 92% standard in July. Oral surgery was furthest from it at 54.2%, then ear, nose and throat at 57.6%; the best of the twenty-three, elderly medicine, reached 83.8% [06_specialty/specialty_headline.csv].

That spread is the reason the question matters. If the trusts doing worst on waiting are the ones serving the places doing worst on health, the two halves of the lottery compound. If they aren't, they don't.

## The join that wasn't supposed to exist

The premise I started with was that there is no clean way to get from a neighbourhood to the hospital its residents actually use. There is — it just isn't the sort of thing you'd find unless you went looking for it. OHID publishes, once a year, its acute trust catchment populations: for every MSOA and every acute trust, how many of that neighbourhood's residents were admitted there over three pooled years, and which trust took the largest share. They call that trust "first past the post".

It is a crosswalk. It is not a clean one, and the pipeline measures how unclean [02_crosswalk/crosswalk_findings.csv]:

- The dominant trust takes, for the typical neighbourhood, 76% of its elective admissions. For one neighbourhood in twelve it takes under half.
- It covers acute trusts only. 403 of the 533 providers reporting waiting lists — independent-sector clinics, community services, the smaller NHS bodies — have no residence footprint at all. Between them they hold 7.2% of the national waiting list.
- It is built on admissions, not on referrals. Change from all admissions to elective ones and 126 neighbourhoods change their main hospital.
- And it is only as good as the month's return. Sheffield Teaching Hospitals and Torbay are absent from every month I pulled; Plymouth stopped in July. That leaves 167 neighbourhoods with a main hospital and no figure for it.

I used it anyway, because the honest alternative — declaring the join impossible — would have been wrong. Every neighbourhood got its dominant trust's 18-week share, and, as a check, an average across all the trusts it uses weighted by how many of its residents go to each. Using the dominant trust rather than that weighted alternative changes a neighbourhood's figure by less than a point in the typical case, three points at the ninetieth percentile, thirteen points at the very worst.

Then I ran the correlation.

## Nothing

The correlation between a neighbourhood's healthy life expectancy and the 18-week performance of the hospital its residents mostly use is −0.004 for men and −0.002 for women, across 6,688 neighbourhoods and 6,689 respectively [03_joined/joined_summary.csv]. Weighting by every trust a neighbourhood uses rather than just the biggest: −0.004 and −0.004. Rank-order correlation comes out marginally positive, +0.007 and +0.010, which at this magnitude means the same thing as marginally negative — nothing. Run it for April, May and June as well and it stays between −0.020 and −0.002 across all four months [05_months/by_month.csv].

Before going further: healthy life expectancy here describes 2019 to 2023 and the waiting figures describe 2026. What this tests is whether places with different historical health profiles are currently served by providers with systematically different waiting performance. It is not a test of whether waiting harms health, and nothing below should be read as one.

In plain terms, and measured rather than inferred — a correlation of zero doesn't by itself tell you the extremes behave: take England's tenth of neighbourhoods with the lowest healthy life expectancy and its healthiest tenth, and the hospitals they mostly use sit 0.9 percentage points apart on eighteen-week performance, 64.0% against 64.9% [03_joined/joined_summary.csv]. Across all trusts the spread is thirty-four points.

You can come at it from the other direction and get the same answer. Take the quarter of main hospitals with the worst 18-week performance and the quarter doing best, and compare the neighbourhoods behind them. Pool those neighbourhoods and the median healthy life expectancy for men is 65.0 years for the worst-waiting group against 65.2 for the best — 1,890 neighbourhoods against 1,352 [03_joined/joined_summary.csv]. Count each hospital once instead, taking the median of their catchment medians, and it comes out 65.8 against 65.1, tilted the other way. Two defensible statistics, two-tenths and seven-tenths of a year apart, pointing in opposite directions. Against a twenty-year spread inside a single ICB, neither is a gradient.

In these data, the places with the lowest healthy life expectancy are not, as a group, served by hospitals with systematically worse waiting performance. Nor systematically better.

The obvious explanation is that my join is too rough to see it. That deserves a test rather than a denial, and there is one worth running: if the result came mainly from pinning each neighbourhood to a single dominant hospital, I would expect the admissions-weighted version — every trust a neighbourhood uses, in proportion — to move it. It doesn't. Both land at −0.004.

That is narrower than it sounds, and I want to be exact about how narrow. It tells me the near-zero result is not an artefact of the dominant-trust simplification. It does not tell me that crosswalk error cannot hide an association, because both versions are built from the same admissions data, and admissions are not referral pathways. A join can be accurate for each neighbourhood and still be the wrong unit of analysis altogether. What I can say is what I observed: at this level, between these measures, I cannot find a relationship.

## The objection, and what the chart does to it

The reply I expected to this piece was: you don't need a neighbourhood-to-hospital join, because integrated care boards already tie residents to providers. Every trust has a parent ICB. Every neighbourhood sits in one. Join there.

Two things happen when you do [02_crosswalk/A_icb_table.csv].

The first is leakage. Fourteen per cent of elective admissions in England are treated by a trust whose parent ICB is not the patient's. Turn that around and view it from where people live: the typical ICB sees 14% of its residents' acute admissions go to trusts it does not manage, and Staffordshire and Stoke-on-Trent sees 47% — to Burton, to Wolverhampton, to Birmingham, none of which report to it. The traffic runs the other way too. Frimley Health draws four-fifths of its patients from outside the ICB it belongs to.

The second is the chart.

[CHART: data/gold/04_chart/icb_strip_hle.png]

Each row is one of England's 36 ICBs. Each grey mark is a neighbourhood's healthy life expectancy. The blue mark is the ICB's median. The orange band is the entire distance between the highest-median ICB and the lowest — Thames Valley to Birmingham and Solihull, 9.2 years for men, 10.0 for women [01_spread/spread_summary.csv].

Every row is wider than the band. Not most rows: every one. Cornwall, the tightest ICB in England, spans 14.2 years of healthy life between its best neighbourhood and its worst. Cheshire and Merseyside spans 28. The median ICB spans 20. Four-fifths of all the variation in healthy life expectancy between English neighbourhoods is variation *inside* ICBs, not between them.

You might reasonably ask whether that survives the estimates' error bars — each neighbourhood's figure carries a 95% interval about three years wide, and the chart plots points. So I gave the claim a deliberately conservative test: take each ICB's healthiest neighbourhood at the bottom of its interval and its least healthy at the top, shrinking every row by roughly two intervals' worth before comparing. All 36 rows are still wider than the band [07_ci_robustness/ci_robustness.csv]. The narrowest survivor clears it by a year and a half.

The two rows I've annotated are the top and bottom of the chart. Thames Valley's providers had 67% of their pathways within 18 weeks in July. Birmingham and Solihull's had 69%. Nine and a half years of healthy life apart, and the better-waiting one is the one at the bottom.

An ICB-level waiting figure, attached to a neighbourhood, is a number for a population that differs from itself by twenty years. That isn't a join. It's an average wearing a postcode.

## What the data cannot tell you

It cannot tell you that waiting doesn't harm health. It says that, at the level of neighbourhoods and their main hospitals, in the summer of 2026, the two measures don't move together. Individuals are not neighbourhoods, and a year on a list can cost a person a great deal without showing up in a Census health question averaged over five years.

The health figures straddle the pandemic and assume the 2021 Census health picture held from 2019 to 2023. They are built on a different basis from the figure usually quoted for England — the Census-based 65.1 is not the survey-based figure of around 61, and ONS says the two should not be compared. One neighbourhood-sex, Barnet 042 for men, was excluded by ONS as implausible and is excluded here.

The waiting figures are a monthly snapshot, and four providers didn't submit July's. The crosswalk is admissions, rounded to the nearest five, with anything under eight suppressed. And the neighbourhood figures are estimates: each carries a 95% interval averaging about three years, wide enough that any single neighbourhood's number should be read loosely, even where the shape of the whole distribution survives the test above.

And there is one thing I have not done, which someone should: the same join with a deprivation measure in place of healthy life expectancy. If waiting does not follow health, the next question is whether it follows money.

## The pipeline

Bronze, silver, gold — the same shape as my previous work. Five sources, each downloaded unmodified and hashed. Silver puts the health figures from ONS and OHID on one schema and asserts the grain; builds the neighbourhood-to-ICB geography and asserts that every neighbourhood sits in one ICB (five don't, cleanly; they're flagged); recomputes every 18-week share from the weekly wait bands rather than trusting a published percentage. Gold is the spread test, the four crosswalk routes and what each one loses, and the join.

Before any of that ran, I rebuilt OHID's published England figure from my own extract. Healthy life expectancy isn't additive — you can't average 6,856 neighbourhoods and get the country — so the test was three tests: OHID's England row against ONS's, all 13,712 neighbourhood rows against each other, and the ONS bulletin's own medians and percentiles against mine. 65.1 and 66.5, to the decimal. Every row. Every percentile. Then, and only then, the rest.

The repo is public. Anyone can clone it and get the same numbers — which is how this piece got better, because someone did.

An audit of the first published commit found two things I had wrong, and neither was the kind of error assertions catch.

The first is the one I promised to come back to. The waiting-list extract carries rows with no identified commissioner. NHS England's published provider workbook excludes them; mine didn't, which put exactly 31,007 pathways on the national total — 7.16 million where the published figure is 7,131,685. The numbers in this piece are now the reported provider measure, reconciled to that workbook to the pathway, rather than to the estimated headline of around 7.3 million that adds back the four non-submitters.

The second: North Bristol NHS Trust merged into Bristol NHS Foundation Trust on the first of July — so its code stopped appearing, and my join read a merger as a failure to report, wrongly stripping the waiting figure from 61 neighbourhoods. Both are fixed; the figures above are the corrected ones. The reconciliation gate that should have caught the first ran before the waiting-time data it was meant to check even existed, and skipped itself in silence. It doesn't any more.

I'd rather say that plainly than quietly reissue the numbers. A pipeline full of assertions still shipped a merged hospital as a missing one, and the constant naming the genuinely missing trusts was sitting in the same file as the join that contradicted it.

---

The two people from the opening are still in the same borough. Their neighbourhoods are twenty-five years apart in healthy life. Nothing in this analysis shows that gap tracking the waiting-time performance of the hospitals serving them — not at this grain, not across these months.

Neither map is wrong. They are answers to different questions, measured over different periods, on geographies built for different purposes. The mistake would be treating them as one.

*Sources: ONS, Health state life expectancy estimates for MSOAs, England and Wales: 2019 to 2023 (30 July 2026); OHID Local health, September 2026 update; NHS England, RTT waiting times, April–July 2026; OHID, NHS acute (hospital) trust catchment populations, April 2026; ONS Open Geography Portal. Code and every table: https://github.com/YusufIsmailayo/two-maps-hle-rtt*
