"""
Reconciliation gate. Nothing downstream is trusted until this passes.

HLE is a life-table quantity, not an additive one: England's HLE cannot be
rebuilt by aggregating MSOA HLEs. So "rebuild OHID's published England
figure" is done the only honest way - three independent checks:

  A. Fingertips England row == ONS sheet 2 England row (the figure OHID
     publishes is the figure ONS published, to the decimal).
  B. Every English MSOA x sex value in Fingertips == the ONS value (row for
     row, including the one MSOA-sex ONS excluded as implausible).
  C. The ONS bulletin's headline distribution statistics - median, IQR, min,
     max of MSOA HLE by sex - reproduced from our own Silver rows.

Bulletin figures (ONS, 30 Jul 2026), verbatim: males median 65.3, IQR 7.4,
"lowest 10% (57.7 years) and highest 10% (71.0 years)", interdecile range
13.4; females median 66.8, IQR 7.8, 58.6 / 72.6, interdecile range 14.0.
The 10th/90th percentiles are what the bulletin quotes - not min/max.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GOLD_DIR, SILVER_DIR  # noqa: E402

OUT = GOLD_DIR / "00_reconciliation"
OUT.mkdir(parents=True, exist_ok=True)

BULLETIN = {
    "Male":   {"median": 65.3, "iqr": 7.4, "p10": 57.7, "p90": 71.0, "interdecile": 13.4},
    "Female": {"median": 66.8, "iqr": 7.8, "p10": 58.6, "p90": 72.6, "interdecile": 14.0},
}


def main() -> None:
    ons = pd.read_parquet(SILVER_DIR / "hle" / "hle_ons.parquet")
    ft = pd.read_parquet(SILVER_DIR / "hle" / "hle_fingertips.parquet")
    rows = []

    # --- A: England headline ---------------------------------------------
    ons_eng = ons[(ons.area_code == "E92000001")].set_index("sex")
    ft_eng = ft[(ft.area_code == "E92000001")].set_index("sex")
    for sex in ["Male", "Female"]:
        o, f = ons_eng.loc[sex], ft_eng.loc[sex]
        rows.append({"check": "A_england_headline", "sex": sex, "metric": "hle",
                     "ons": o.hle, "fingertips": f.hle, "diff": round(f.hle - o.hle, 3),
                     "pass": abs(f.hle - o.hle) < 0.05})
        rows.append({"check": "A_england_headline", "sex": sex, "metric": "hle_lci",
                     "ons": o.hle_lci, "fingertips": f.hle_lci, "diff": round(f.hle_lci - o.hle_lci, 3),
                     "pass": abs(f.hle_lci - o.hle_lci) < 0.05})
        rows.append({"check": "A_england_headline", "sex": sex, "metric": "hle_uci",
                     "ons": o.hle_uci, "fingertips": f.hle_uci, "diff": round(f.hle_uci - o.hle_uci, 3),
                     "pass": abs(f.hle_uci - o.hle_uci) < 0.05})

    # --- B: row-for-row MSOA ----------------------------------------------
    om = ons[(ons.country == "England") & (ons.area_type == "MSOA")][["area_code", "sex", "hle", "hle_excluded_reason"]]
    fm = ft[ft.area_type == "MSOA"][["area_code", "sex", "hle", "value_note"]]
    m = om.merge(fm, on=["area_code", "sex"], how="outer", suffixes=("_ons", "_ft"), indicator=True)
    both_null = m.hle_ons.isna() & m.hle_ft.isna()
    diff = (m.hle_ons - m.hle_ft).abs()
    mismatch = m[~both_null & ~(diff < 0.05)]
    rows.append({"check": "B_msoa_row_for_row", "sex": "both", "metric": "rows_compared",
                 "ons": len(om), "fingertips": len(fm), "diff": int((m._merge != "both").sum()),
                 "pass": (m._merge == "both").all()})
    rows.append({"check": "B_msoa_row_for_row", "sex": "both", "metric": "value_mismatches",
                 "ons": None, "fingertips": None, "diff": len(mismatch), "pass": len(mismatch) == 0})
    rows.append({"check": "B_msoa_row_for_row", "sex": "both", "metric": "excluded_in_both",
                 "ons": int(om.hle.isna().sum()), "fingertips": int(fm.hle.isna().sum()),
                 "diff": int(both_null.sum()), "pass": bool(both_null.sum() == om.hle.isna().sum() == fm.hle.isna().sum())})
    mismatch.to_csv(OUT / "B_mismatches.csv", index=False)

    # --- C: bulletin distribution stats from our rows ----------------------
    for sex, b in BULLETIN.items():
        v = om[(om.sex == sex)].hle.dropna()
        got = {"median": v.median(), "iqr": v.quantile(0.75) - v.quantile(0.25),
               "p10": v.quantile(0.10), "p90": v.quantile(0.90),
               "interdecile": v.quantile(0.90) - v.quantile(0.10)}
        for k, pub in b.items():
            # Published MSOA values are to 1 d.p.; ONS derives the interdecile
            # range from its unrounded internal estimates, so 71.0 - 57.7 = 13.3
            # here against 13.4 in the bulletin. That 0.1 is a rounding
            # artefact, not a data difference - tolerated and noted, not hidden.
            tol = 0.15 if k == "interdecile" else 0.05
            rows.append({"check": "C_bulletin_distribution", "sex": sex, "metric": k,
                         "ons": pub, "fingertips": round(got[k], 1), "diff": round(got[k] - pub, 2),
                         "pass": abs(round(got[k], 1) - pub) < tol + 1e-9,
                         "note": "derived from 1dp published values; ONS uses unrounded" if k == "interdecile" else ""})

    # --- D: RTT England headline vs NHS England statistical press notice ---
    # SPN (10 Sep 2026) figures INCLUDE estimates for non-reporting trusts
    # (RHQ Sheffield, RA9 Torbay, RK9 Plymouth, NMG Cora Health MSK). The
    # published extract does not, so totals must sit just below the SPN and
    # the 18-week share within a few tenths of a point.
    rtt_path = SILVER_DIR / "rtt" / "rtt_provider.parquet"
    if rtt_path.exists():
        prov = pd.read_parquet(rtt_path)
        prov = prov[prov.period == "2026-07"]   # the press notice being reconciled against is July 2026
        tot, w18, o52 = prov.total_waiting.sum(), prov.within_18.sum(), prov.over_52.sum()
        rows.append({"check": "D_rtt_vs_press_notice", "sex": "n/a", "metric": "incomplete_pathways_millions",
                     "ons": 7.3, "fingertips": round(tot / 1e6, 2), "diff": round(tot / 1e6 - 7.3, 2),
                     "pass": 7.0 <= tot / 1e6 <= 7.3, "note": "SPN includes estimates for 4 non-reporting providers; extract does not"})
        rows.append({"check": "D_rtt_vs_press_notice", "sex": "n/a", "metric": "pct_within_18_weeks",
                     "ons": 65.4, "fingertips": round(100 * w18 / tot, 1), "diff": round(100 * w18 / tot - 65.4, 1),
                     "pass": abs(100 * w18 / tot - 65.4) < 0.5, "note": "'ons' column = NHS England SPN"})
        rows.append({"check": "D_rtt_vs_press_notice", "sex": "n/a", "metric": "over_52_weeks",
                     "ons": 111379, "fingertips": int(o52), "diff": int(o52 - 111379),
                     "pass": abs(o52 - 111379) / 111379 < 0.01, "note": "'ons' column = NHS England SPN"})

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "reconciliation.csv", index=False)
    print(res.to_string(index=False))
    print("\nGATE:", "PASS" if res["pass"].all() else "FAIL")
    if not res["pass"].all():
        sys.exit(1)


if __name__ == "__main__":
    main()
