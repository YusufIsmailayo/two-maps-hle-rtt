"""
Silver: RTT incomplete pathways, July 2026, at provider grain.

Compliance is recomputed from the weekly wait bands (weeks 0-18 waiting /
total with known clock start), not taken from any published percentage, so
the England figure can be checked against NHS England's statistical press
notice independently.

Two tables:
  rtt_provider           - one row per provider (Total treatment function):
                           total waiting, within 18 weeks, over 52 weeks,
                           % within 18, parent ICB.
  (The extract's 'Total' column is blank for incomplete pathways; totals are
   rebuilt from the bands and asserted equal to 'Total All'.)
  rtt_provider_tfc       - provider x treatment function, same measures.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BRONZE_DIR, SILVER_DIR  # noqa: E402

ZIP = BRONZE_DIR / "nhse_rtt_2026-07" / "Full-CSV-data-file-Jul26.zip"
OUT = SILVER_DIR / "rtt"
OUT.mkdir(parents=True, exist_ok=True)


def band_cols(cols: list[str]) -> tuple[list[str], list[str]]:
    """Return (columns for weeks 0-18, columns for weeks >52) from the wide band headers."""
    within18, over52 = [], []
    for c in cols:
        if not c.startswith("Gt "):
            continue
        parts = c.split()
        lo = int(parts[1])
        if parts[2] == "To":
            hi = int(parts[3])
            if hi <= 18:
                within18.append(c)
            if lo >= 52:
                over52.append(c)
        else:  # "Gt 104 Weeks SUM 1"
            over52.append(c)
    return within18, over52


def main() -> None:
    with zipfile.ZipFile(ZIP) as z:
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        with z.open(name) as f:
            raw = pd.read_csv(f, low_memory=False)
    print("raw rows:", len(raw), "| period:", raw.Period.unique())

    inc = raw[raw["RTT Part Description"] == "Incomplete Pathways"].copy()
    w18, o52 = band_cols(list(inc.columns))
    assert len(w18) == 18 and len(o52) == 53, (len(w18), len(o52))

    all_bands = [c for c in inc.columns if c.startswith("Gt ")]
    inc["within_18"] = inc[w18].sum(axis=1)
    inc["over_52"] = inc[o52].sum(axis=1)
    # For incomplete pathways the 'Total' and 'unknown clock start' columns are
    # blank in the full extract; 'Total All' is populated and equals the band
    # sum exactly (asserted). Total is therefore rebuilt from the bands.
    inc["total_waiting"] = inc[all_bands].sum(axis=1)
    assert (inc["total_waiting"] - inc["Total All"]).abs().max() == 0, "band sum != Total All"

    keys = {"Provider Org Code": "provider_code", "Provider Org Name": "provider_name",
            "Provider Parent Org Code": "provider_icb_ods", "Provider Parent Name": "provider_icb_name",
            "Treatment Function Code": "tfc_code", "Treatment Function Name": "tfc_name"}
    inc = inc.rename(columns=keys)

    # The file is provider x commissioner x TFC; roll commissioner out so grain is provider x TFC.
    tfc = (inc.groupby(["provider_code", "provider_name", "provider_icb_ods", "provider_icb_name", "tfc_code", "tfc_name"],
                       as_index=False)[["within_18", "over_52", "total_waiting"]].sum())
    tfc["pct_within_18"] = tfc.within_18 / tfc.total_waiting
    tfc["pct_over_52"] = tfc.over_52 / tfc.total_waiting
    assert not tfc.duplicated(["provider_code", "tfc_code"]).any(), "grain violated: provider x tfc"

    prov = tfc[tfc.tfc_code == "C_999"].drop(columns=["tfc_code", "tfc_name"]).reset_index(drop=True)
    assert prov.provider_code.is_unique, "grain violated: provider"
    # Cross-check: C_999 'Total' row equals the sum of the named TFCs for each provider.
    named = tfc[tfc.tfc_code != "C_999"].groupby("provider_code").total_waiting.sum()
    chk = prov.set_index("provider_code").total_waiting.sub(named, fill_value=0)
    assert (chk.abs() < 1).all(), f"C_999 total != sum of TFCs for {int((chk.abs() >= 1).sum())} providers"

    prov["provider_kind"] = prov.provider_code.str[0].map(
        {"R": "NHS trust", "N": "independent sector (N-code)"}).fillna("other (non-R/N ODS code)")

    prov.to_parquet(OUT / "rtt_provider.parquet", index=False)
    tfc.to_parquet(OUT / "rtt_provider_tfc.parquet", index=False)

    eng_total = prov.total_waiting.sum()
    eng_w18 = prov.within_18.sum()
    print(f"providers: {len(prov)} | kinds: {prov.provider_kind.value_counts().to_dict()}")
    print(f"England incomplete pathways: {eng_total:,.0f} | within 18wk: {eng_w18/eng_total:.1%} "
          f"| >52wk: {prov.over_52.sum():,.0f} ({prov.over_52.sum()/eng_total:.2%})")
    print("ICB parents:", prov.provider_icb_ods.nunique())


if __name__ == "__main__":
    main()
