<!--
DRAFT v1 — 14 Sep 2026. Every figure below is in data/gold/ (file named in
[brackets] on first use; strip the brackets before publishing). Nothing is
estimated in prose.

Title options — the original no longer describes what the data showed:
  (a) I Laid the Two Halves of the Postcode Lottery on Top of Each Other. They Don't Touch.
  (b) Two Maps of England, Finally Lined Up  — (paradox mode: quieter)
  (c) Where You Live and Where You Wait Are Two Different Lotteries
-->

# Two Maps of England, Finally Lined Up

*Healthy life expectancy, now published for 6,856 neighbourhoods. Waiting times, published for 533 providers. I joined them. The join says nothing — and that is the finding.*

---

Somewhere in England this morning, two people are getting up in houses twenty minutes apart by car.

One of them can expect to reach 71 in good health. The other will be lucky to see 58 that way. Same country. Same NHS. Same region, probably the same integrated care board. Thirteen years apart before either of them is ill.

That is not a worst case. It is the gap between the tenth-best and the tenth-worst neighbourhood in every hundred.

## What was published on 2 September

The Office for Health Improvement and Disparities added one thing to its Local health profile this month: healthy life expectancy for 2019 to 2023, for every middle-layer super output area in England. An MSOA is a statistical neighbourhood of roughly five to fifteen thousand people. There are 6,856 of them.

Healthy life expectancy is not life expectancy. It is the number of years a newborn could expect to live in what people themselves describe as good health, if the conditions of the period held for their whole life. The figures are ONS's, built from five years of deaths and the health question on the 2021 Census. For England as a whole: 65.1 years for men, 66.5 for women [00_reconciliation/reconciliation.csv]. The pandemic sits inside every one of those numbers.

I had been waiting for this release. Last year I built a pipeline over NHS England's referral-to-treatment data — the waiting-time half of the postcode lottery — and the obvious question was always the one I couldn't answer: does living in a place that costs you healthy years also cost you time on the waiting list? The waiting-time figures are published by the trust that treats you. The health figures are published by the place you live. Nobody publishes the map that joins them.

So I set out to prove the map doesn't exist. That's not what happened.

## The access side, for scale

At the end of July 2026 there were 7.16 million open referral-to-treatment pathways in England [05_silver rtt; 00_reconciliation]. The standard says 92% of patients should have waited 18 weeks or less. In July, 65.3% had. In 111,429 cases the patient had been waiting more than a year.

The 18-week share is not one number, it is 533 numbers, one per provider. Among the acute trusts that serve as the main hospital for at least ten neighbourhoods, it runs from about 50% to about 84% [03_joined/trust_catchment_hle_male.csv] — a 34-point spread. Oral surgery is the specialty furthest from the standard nationally, at 54% within 18 weeks.

That spread is the reason the question matters. If the trusts doing worst on waiting are the ones serving the places doing worst on health, the two halves of the lottery compound. If they aren't, they don't.

## The join that wasn't supposed to exist

The premise I started with was that there is no clean way to get from a neighbourhood to the hospital its residents actually use. There is — it just isn't the sort of thing you'd find unless you went looking for it. OHID publishes, once a year, its acute trust catchment populations: for every MSOA and every acute trust, how many of that neighbourhood's residents were admitted there over three pooled years, and which trust took the largest share. They call that trust "first past the post".

It is a crosswalk. It is not a clean one, and the pipeline measures how unclean [02_crosswalk/crosswalk_findings.csv]:

- The dominant trust takes, for the typical neighbourhood, 76% of its elective admissions. For one neighbourhood in twelve it takes under half.
- It covers acute trusts only. 403 of the 533 providers reporting waiting lists — independent-sector clinics, community services, the smaller NHS bodies — have no residence footprint at all. Between them they hold 7.1% of the national waiting list.
- It is built on admissions, not on referrals. Change from all admissions to elective ones and 126 neighbourhoods change their main hospital.
- And it is only as good as the month's return. In July, Sheffield Teaching Hospitals, Torbay, Plymouth and North Bristol submitted no waiting-time data. That left 228 neighbourhoods with a main hospital and no figure for it.

I used it anyway, because the honest alternative — declaring the join impossible — would have been wrong. Every neighbourhood got its dominant trust's 18-week share, and, as a check, an average across all the trusts it uses weighted by how many of its residents go to each. Treating the join as clean moves a neighbourhood's figure by less than a point in the typical case, three points at the ninetieth percentile, thirteen at the very worst.

Then I ran the correlation.

## Nothing

The correlation between a neighbourhood's healthy life expectancy and the 18-week performance of the hospital its residents mostly use is −0.008 for men and −0.006 for women [03_joined/joined_summary.csv]. Rank-order correlation: the same. The weighted version: the same. Run it for April, May and June as well as July and it never leaves the band between −0.02 and −0.01 [05_months/by_month.csv].

Put it another way. Take the quarter of main hospitals with the worst 18-week performance and look at the neighbourhoods they serve: their median healthy life expectancy for men is 65.8 years. Take the quarter doing best: 65.0. There is no gradient. The places losing the most healthy years are not, as a group, waiting any longer than anyone else. Nor any less.

The obvious explanation is that my join is too rough to see it. I don't think that survives the numbers above — a join that shifts the typical neighbourhood's figure by under a point cannot hide a relationship that exists. The less comfortable explanation is that the relationship, at this level, isn't there.

## The objection, and what the chart does to it

The reply I expected to this piece was: you don't need a neighbourhood-to-hospital join, because integrated care boards already tie residents to providers. Every trust has a parent ICB. Every neighbourhood sits in one. Join there.

Two things happen when you do [02_crosswalk/A_icb_table.csv].

The first is leakage. Fourteen per cent of elective admissions in England are treated by a trust whose parent ICB is not the patient's. In Staffordshire and Stoke-on-Trent, 47% of residents' acute admissions are to trusts outside its ICB — Burton, Wolverhampton, Birmingham — none of which report to Staffordshire. Frimley Health draws four-fifths of its patients from outside the ICB it belongs to.

The second is the chart.

[CHART: data/gold/04_chart/icb_strip_hle.png]

Each row is one of England's 36 ICBs. Each grey mark is a neighbourhood's healthy life expectancy. The blue mark is the ICB's median. The orange band is the entire distance between the highest-median ICB and the lowest — Thames Valley to Birmingham and Solihull, 9.2 years for men, 10.0 for women [01_spread/spread_summary.csv].

Every row is wider than the band. Not most rows: every one. Cornwall, the tightest ICB in England, spans 14.2 years of healthy life between its best neighbourhood and its worst. Cheshire and Merseyside spans 28. The median ICB spans 20. Four-fifths of all the variation in healthy life expectancy between English neighbourhoods is variation *inside* ICBs, not between them.

The two rows I've annotated are the top and bottom of the chart. Thames Valley's providers had 67% of their pathways within 18 weeks in July. Birmingham and Solihull's had 69%. Nine and a half years of healthy life apart, and the better-waiting one is the one at the bottom.

An ICB-level waiting figure, attached to a neighbourhood, is a number for a population that differs from itself by twenty years. That isn't a join. It's an average wearing a postcode.

## What the data cannot tell you

It cannot tell you that waiting doesn't harm health. It says that, at the level of neighbourhoods and their main hospitals, in the summer of 2026, the two measures don't move together. Individuals are not neighbourhoods, and a year on a list can cost a person a great deal without showing up in a Census health question averaged over five years.

The health figures straddle the pandemic and assume the 2021 Census health picture held from 2019 to 2023. They are built on a different basis from the healthy life expectancy figure usually quoted for England — the Census-based 65.1 is not the survey-based figure of around 61, and ONS says the two should not be compared. One neighbourhood-sex — Barnet 042, men — was excluded by ONS as implausible and is excluded here.

The waiting figures are a monthly snapshot, and four providers didn't submit July's. The crosswalk is admissions, rounded to the nearest five, with anything under eight suppressed. I have not tried to back-calculate any of it.

And there is one thing I have not done, which someone should: the same join with a deprivation measure in place of healthy life expectancy. If waiting does not follow health, the next question is whether it follows money.

## The pipeline

Bronze, silver, gold — the same shape as my previous work. Five sources, each downloaded unmodified and hashed. Silver puts the health figures from ONS and OHID on one schema and asserts the grain; builds the neighbourhood-to-ICB geography and asserts that every neighbourhood sits in one ICB (five don't, cleanly; they're flagged); recomputes every 18-week share from the weekly wait bands rather than trusting a published percentage. Gold is the spread test, the four crosswalk routes and what each one loses, and the join.

Before any of that ran, I rebuilt OHID's published England figure from my own extract. Healthy life expectancy isn't additive — you can't average 6,856 neighbourhoods and get the country — so the test was three tests: OHID's England row against ONS's, all 13,712 neighbourhood rows against each other, and the ONS bulletin's own medians and percentiles against mine. 65.1 and 66.5, to the decimal. Every row. Every percentile. Then, and only then, the rest.

The repo is public. Anyone can clone it and get the same numbers.

---

The two people from the opening are still twenty minutes apart. One of them will spend thirteen more years in good health than the other, and nothing on the waiting list explains why — because the waiting list doesn't know where either of them lives. Neither map is wrong. They are just answers to different questions, and the country has been asking them as if they were one.

*Sources: ONS, Health state life expectancy estimates for MSOAs, England and Wales: 2019 to 2023 (30 July 2026); OHID Local health, September 2026 update; NHS England, RTT waiting times, April–July 2026; OHID, NHS acute (hospital) trust catchment populations, April 2026; ONS Open Geography Portal. Code and every table: [GitHub link].*
