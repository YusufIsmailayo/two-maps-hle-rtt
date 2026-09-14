"""
Gold 2: the residence -> provider crosswalk, attempted four ways.

Each route is a real join attempted on the Silver tables, with the loss at
each step measured rather than assumed. Outputs in data/gold/02_crosswalk/.

Route A  ICB footprint      MSOA -> LSOA -> ICB (Apr 2026); provider -> parent
                            ICB (RTT file). Key-level join is clean. Tested
                            for what it hides: leakage - the share of an
                            ICB's residents' admissions that go to trusts
                            parented by a different ICB, and the share of a
                            trust's admitted patients who live outside its
                            parent ICB (from the catchment file).
Route B  First past the post MSOA -> dominant acute trust (OHID FPTP flag) ->
                            RTT provider row. Tested for: how much of the
                            MSOA's admissions the FPTP trust actually takes;
                            RTT coverage of FPTP trusts (non-submitters);
                            and the share of England's waiting list sitting
                            at providers with no residence footprint at all.
Route C  Commissioner       MSOA -> LSOA -> Sub-ICB location -> RTT
                            commissioner rows. Tested for: commissioner
                            codes in RTT that are not SICBLs, and the point
                            that a commissioner is a GP-registration
                            population, not a residence.
Route D  Trust address      trust HQ LSOA -> MSOA. Included because it is
                            what a naive spatial join does. 134 points.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR, SILVER_DIR  # noqa: E402

OUT = GOLD_DIR / "02_crosswalk"
OUT.mkdir(parents=True, exist_ok=True)

NON_SUBMITTERS_JUL26 = {"RHQ": "Sheffield Teaching Hospitals", "RA9": "Torbay and South Devon",
                        "RK9": "University Hospitals Plymouth", "NMG": "Cora Health MSK (ISP)"}


def main() -> None:
    geo = pd.read_parquet(SILVER_DIR / "geography" / "msoa_geography.parquet")
    lsoa = pd.read_parquet(SILVER_DIR / "geography" / "lsoa_geography.parquet")
    prov = pd.read_parquet(SILVER_DIR / "rtt" / "rtt_provider.parquet")
    cat_all = pd.read_parquet(SILVER_DIR / "catchment" / "msoa_trust_admissions.parquet")
    cat_all = cat_all[cat_all.catchment_year == 2024]
    cat = cat_all[cat_all.admission_type == "elective"].copy()      # RTT is elective: join on elective catchment
    cat_any = cat_all[cat_all.admission_type == "all"].copy()       # comparison
    trust_lu = pd.read_parquet(SILVER_DIR / "catchment" / "trust_lookup.parquet")
    hle = pd.read_parquet(GOLD_DIR / "01_spread" / "msoa_hle_icb.parquet")

    findings = []
    eng_waiting = prov.total_waiting.sum()

    # ------------------------------------------------------------------ Route A
    icb_rtt = (prov.groupby(["provider_icb_ods", "provider_icb_name"], as_index=False)
                   [["total_waiting", "within_18", "over_52"]].sum())
    icb_rtt["pct_within_18"] = icb_rtt.within_18 / icb_rtt.total_waiting
    icb_rtt["n_providers"] = prov.groupby("provider_icb_ods").size().values
    icb_msoa = geo.groupby("icb_ods").size().rename("n_msoa")
    a = icb_rtt.merge(icb_msoa, left_on="provider_icb_ods", right_index=True, how="outer", indicator=True)
    findings.append({"route": "A_icb_footprint", "test": "ICB keys join (RTT parent ODS vs ONS ICB26CDH)",
                     "value": f"{(a._merge == 'both').sum()} of {len(a)} both sides", "verdict": "clean at key level"})
    findings.append({"route": "A_icb_footprint", "test": "MSOAs straddling two ICBs (LSOA-level)",
                     "value": int(geo.straddles_icb.sum()), "verdict": "assigned by LSOA majority, flagged"})

    # Leakage, from the catchment file: attach resident ICB (MSOA) and parent ICB (trust).
    trust_parent = prov[["provider_code", "provider_icb_ods"]].rename(
        columns={"provider_code": "trust_code", "provider_icb_ods": "trust_parent_icb"})
    c = cat_any.merge(geo[["msoa_code", "icb_ods", "icb_name_short"]], on="msoa_code", how="left") \
               .merge(trust_parent, on="trust_code", how="left")
    no_parent = c[c.trust_parent_icb.isna()].trust_code.unique()
    findings.append({"route": "A_icb_footprint", "test": "catchment trusts absent from July 2026 RTT provider list",
                     "value": f"{len(no_parent)} of {cat.trust_code.nunique()}: {sorted(no_parent)}",
                     "verdict": "non-submitters / merged codes - no parent ICB assignable"})
    c2 = c.dropna(subset=["trust_parent_icb"]).copy()
    c2["same_icb"] = c2.icb_ods == c2.trust_parent_icb
    # resident view: of admissions from this ICB's residents, share going to trusts parented elsewhere
    res = c2.groupby(["icb_ods", "icb_name_short"]).apply(
        lambda g: pd.Series({"admissions": g.patients_admitted.sum(),
                             "pct_admitted_outside_parent_icb": 1 - g.loc[g.same_icb, "patients_admitted"].sum() / g.patients_admitted.sum()}),
        include_groups=False).reset_index()
    # trust view: of this trust's admitted patients, share living outside its parent ICB
    tr = c2.groupby(["trust_code", "trust_name", "trust_parent_icb"]).apply(
        lambda g: pd.Series({"admissions": g.patients_admitted.sum(),
                             "pct_patients_from_outside_parent_icb": 1 - g.loc[g.same_icb, "patients_admitted"].sum() / g.patients_admitted.sum()}),
        include_groups=False).reset_index()
    nat_leak = 1 - c2.loc[c2.same_icb, "patients_admitted"].sum() / c2.patients_admitted.sum()
    el = cat.merge(geo[["msoa_code", "icb_ods"]], on="msoa_code").merge(trust_parent, on="trust_code")
    el_leak = 1 - el.loc[el.icb_ods == el.trust_parent_icb, "patients_admitted"].sum() / el.patients_admitted.sum()
    findings.append({"route": "A_icb_footprint", "test": "England: share of ELECTIVE acute admissions treated by a trust parented by a different ICB from the patient's residence",
                     "value": f"{el_leak:.1%}", "verdict": "the elective (RTT-relevant) leakage"})
    findings.append({"route": "A_icb_footprint", "test": "England: share of ALL acute admissions treated by a trust parented by a different ICB from the patient's residence",
                     "value": f"{nat_leak:.1%}", "verdict": "ICB footprint is not a closed system"})
    findings.append({"route": "A_icb_footprint", "test": "resident view: ICB leakage, median / max",
                     "value": f"{res.pct_admitted_outside_parent_icb.median():.1%} / {res.pct_admitted_outside_parent_icb.max():.1%} "
                              f"({res.loc[res.pct_admitted_outside_parent_icb.idxmax(), 'icb_name_short']})", "verdict": ""})
    findings.append({"route": "A_icb_footprint", "test": "trust view: share of trusts with >25% of admitted patients from outside parent ICB",
                     "value": f"{(tr.pct_patients_from_outside_parent_icb > .25).sum()} of {len(tr)}", "verdict": ""})
    # ICB-level table for the objection chart: RTT % within 18 (by provider parent) alongside HLE spread.
    spread = pd.read_csv(GOLD_DIR / "01_spread" / "icb_spread_by_sex.csv")
    icb_table = (spread.pivot(index=["icb_ods", "icb_name_short"], columns="sex", values=["median", "range", "iqr"]))
    icb_table.columns = [f"hle_{a}_{b.lower()}" for a, b in icb_table.columns]
    icb_table = icb_table.reset_index().merge(icb_rtt.drop(columns="provider_icb_name"), left_on="icb_ods",
                                              right_on="provider_icb_ods").drop(columns="provider_icb_ods") \
                         .merge(res.drop(columns="icb_name_short"), on="icb_ods", how="left")
    icb_table.round(3).to_csv(OUT / "A_icb_table.csv", index=False)
    res.round(3).to_csv(OUT / "A_icb_resident_leakage.csv", index=False)
    tr.round(3).to_csv(OUT / "A_trust_patient_leakage.csv", index=False)

    # ------------------------------------------------------------------ Route B
    fp = cat[cat.fptp][["msoa_code", "trust_code", "trust_name", "share_of_msoa_patients", "msoa_total_patients"]]
    assert fp.msoa_code.is_unique and len(fp) == 6856
    b = fp.merge(prov[["provider_code", "total_waiting", "within_18", "pct_within_18", "pct_over_52"]],
                 left_on="trust_code", right_on="provider_code", how="left")
    b["fptp_trust_in_rtt"] = b.provider_code.notna()
    b["fptp_trust_note"] = b.trust_code.map(NON_SUBMITTERS_JUL26).fillna("")
    sh = fp.share_of_msoa_patients
    findings.append({"route": "B_first_past_the_post", "test": "MSOAs with exactly one FPTP trust (elective admissions)", "value": f"{len(fp)} of 6856", "verdict": "join key exists"})
    fpa = cat_any[cat_any.fptp][["msoa_code", "trust_code"]].rename(columns={"trust_code": "fptp_all_admissions"})
    diff_fp = fp.merge(fpa, on="msoa_code")
    findings.append({"route": "B_first_past_the_post", "test": "MSOAs whose dominant trust differs between elective and all-admissions catchments",
                     "value": int((diff_fp.trust_code != diff_fp.fptp_all_admissions).sum()), "verdict": "the 'main trust' depends on which admissions you count"})
    findings.append({"route": "B_first_past_the_post", "test": "share of MSOA's ELECTIVE admissions taken by its FPTP trust: p10 / median / p90",
                     "value": f"{sh.quantile(.1):.0%} / {sh.median():.0%} / {sh.quantile(.9):.0%}", "verdict": "a majority, not a mapping"})
    findings.append({"route": "B_first_past_the_post", "test": "MSOAs whose FPTP trust takes under half their admissions",
                     "value": f"{(sh < .5).sum()} ({(sh < .5).mean():.1%})", "verdict": ""})
    findings.append({"route": "B_first_past_the_post", "test": "MSOAs whose FPTP trust did not submit RTT in July 2026",
                     "value": f"{(~b.fptp_trust_in_rtt).sum()} ({b.loc[~b.fptp_trust_in_rtt, 'trust_name'].unique().tolist()})",
                     "verdict": "no access figure at all for these neighbourhoods this month"})
    in_cat = prov.provider_code.isin(cat.trust_code.unique())
    findings.append({"route": "B_first_past_the_post", "test": "England waiting list at providers with NO residence footprint (not in catchment file)",
                     "value": f"{prov.loc[~in_cat, 'total_waiting'].sum() / eng_waiting:.1%} of pathways, {(~in_cat).sum()} of {len(prov)} providers",
                     "verdict": "acute-only crosswalk misses every ISP, community and mental health provider"})
    kinds = prov[~in_cat].groupby("provider_kind").total_waiting.sum().sort_values(ascending=False)
    findings.append({"route": "B_first_past_the_post", "test": "...of which, by provider kind (pathways)",
                     "value": {k: int(v) for k, v in kinds.items()}, "verdict": ""})
    # Cost of pretending: admissions-weighted RTT across all the MSOA's trusts vs the FPTP trust alone.
    w = cat.merge(prov[["provider_code", "pct_within_18"]], left_on="trust_code", right_on="provider_code", how="inner")
    w["wt"] = w.patients_admitted * w.pct_within_18
    wm = w.groupby("msoa_code").agg(weighted_pct_within_18=("wt", "sum"), adm=("patients_admitted", "sum"))
    wm["weighted_pct_within_18"] /= wm.adm
    b = b.merge(wm[["weighted_pct_within_18"]], left_on="msoa_code", right_index=True, how="left")
    b["fptp_minus_weighted_pp"] = 100 * (b.pct_within_18 - b.weighted_pct_within_18)
    gap = b.fptp_minus_weighted_pp.abs()
    findings.append({"route": "B_first_past_the_post", "test": "|FPTP trust 18wk% - admissions-weighted 18wk% across all the MSOA's trusts|: median / p90 / max (pp)",
                     "value": f"{gap.median():.1f} / {gap.quantile(.9):.1f} / {gap.max():.1f}",
                     "verdict": "the error you accept by calling the join clean"})
    b = b.merge(hle.pivot(index="msoa_code", columns="sex", values="hle").rename(columns={"Male": "hle_male", "Female": "hle_female"}),
                left_on="msoa_code", right_index=True, how="left")
    b.round(3).to_csv(OUT / "B_msoa_fptp_rtt.csv", index=False)

    # ------------------------------------------------------------------ Route C
    # Needs the commissioner-grain rows, which Silver rolled up; re-read the raw incomplete rows' commissioner codes.
    import zipfile
    from _common import BRONZE_DIR
    with zipfile.ZipFile(BRONZE_DIR / "nhse_rtt_2026-07" / "Full-CSV-data-file-Jul26.zip") as z:
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        raw = pd.read_csv(z.open(name), usecols=["RTT Part Description", "Commissioner Org Code", "Commissioner Org Name",
                                                 "Treatment Function Code", "Total All"], low_memory=False)
    inc = raw[(raw["RTT Part Description"] == "Incomplete Pathways") & (raw["Treatment Function Code"] == "C_999")]
    comm = inc.groupby(["Commissioner Org Code", "Commissioner Org Name"], as_index=False)["Total All"].sum()
    sicbl = lsoa[["SICBL26CDH", "SICBL26NM"]].drop_duplicates()
    comm["is_sicbl"] = comm["Commissioner Org Code"].isin(sicbl.SICBL26CDH)
    findings.append({"route": "C_commissioner", "test": "RTT commissioner codes that are Sub-ICB locations",
                     "value": f"{comm.is_sicbl.sum()} of {len(comm)}", "verdict": ""})
    findings.append({"route": "C_commissioner", "test": "share of England waiting list commissioned by a non-SICBL body",
                     "value": f"{comm.loc[~comm.is_sicbl, 'Total All'].sum() / comm['Total All'].sum():.1%}",
                     "verdict": "NHS England specialised commissioning etc. - no residence"})
    findings.append({"route": "C_commissioner", "test": "MSOAs straddling two SICBLs", "value": int(geo.straddles_sicbl.sum()), "verdict": "flagged"})
    findings.append({"route": "C_commissioner", "test": "what a SICBL is",
                     "value": "GP-registered population of the sub-ICB location, 106 units of ~500k people",
                     "verdict": "residence-adjacent, not residence; and it measures who pays, not where you are treated"})
    comm.sort_values("Total All", ascending=False).to_csv(OUT / "C_commissioner_codes.csv", index=False)

    # ------------------------------------------------------------------ Route D
    d = trust_lu.merge(lsoa[["LSOA21CD", "MSOA21CD"]], left_on="hq_lsoa_code", right_on="LSOA21CD", how="left")
    findings.append({"route": "D_trust_address", "test": "MSOAs containing an acute trust HQ",
                     "value": f"{d.MSOA21CD.nunique()} of 6856", "verdict": "a point, not a population"})

    f = pd.DataFrame(findings)
    f.to_csv(OUT / "crosswalk_findings.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 140)
    print(f.to_string(index=False))


if __name__ == "__main__":
    main()
