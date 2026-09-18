"""
Silver: RTT incomplete pathways, April-July 2026, at provider grain.

Compliance is recomputed from the weekly wait bands (weeks 0-18 waiting /
total with known clock start), not taken from any published percentage, so
the England figure can be checked against NHS England's statistical press
notice independently.

Two tables:
  rtt_provider           - one row per period x provider (Total treatment function):
                           total waiting, within 18 weeks, over 52 weeks,
                           % within 18, parent ICB.
  (The extract's 'Total' column is blank for incomplete pathways; totals are
   rebuilt from the bands and asserted equal to 'Total All'.)
  rtt_provider_tfc       - period x provider x treatment function, same measures.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BRONZE_DIR, SILVER_DIR, RTT_UNIDENTIFIED_COMMISSIONER  # noqa: E402

OUT = SILVER_DIR / "rtt"
OUT.mkdir(parents=True, exist_ok=True)


def rtt_zips() -> list[tuple[str, Path]]:
    """(period 'YYYY-MM', zip path) for every Bronze RTT month, oldest first."""
    out = []
    for folder in sorted(BRONZE_DIR.glob("nhse_rtt_*")):
        zips = list(folder.glob("*.zip"))
        assert len(zips) == 1, f"{folder}: expected one zip, found {len(zips)}"
        out.append((folder.name.replace("nhse_rtt_", ""), zips[0]))
    return out


def load_incomplete(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        with z.open(name) as f:
            raw = pd.read_csv(f, low_memory=False)
    return raw[raw["RTT Part Description"] == "Incomplete Pathways"].copy()


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


def silver_month(period: str, zip_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    inc = load_incomplete(zip_path)
    assert inc.Period.nunique() == 1, inc.Period.unique()
    w18, o52 = band_cols(list(inc.columns))
    assert len(w18) == 18 and len(o52) == 53, (len(w18), len(o52))

    # NHS England's published provider workbook excludes rows with no identified
    # commissioner; the CSV extract includes them. I drop them here so the Silver
    # totals are the published measure, and report what was dropped rather than
    # letting it vanish silently.
    all_bands = [c for c in inc.columns if c.startswith("Gt ")]
    unidentified = inc["Commissioner Org Code"].astype(str).str.startswith(RTT_UNIDENTIFIED_COMMISSIONER)
    dropped = inc.loc[unidentified & (inc["Treatment Function Code"] == "C_999"), all_bands].sum().sum()
    inc = inc[~unidentified].copy()
    print(f"{period}: dropped {dropped:,.0f} pathways with commissioner "
          f"{RTT_UNIDENTIFIED_COMMISSIONER} (not in NHS England's published provider totals)")
    inc["within_18"] = inc[w18].sum(axis=1)
    inc["over_52"] = inc[o52].sum(axis=1)
    # For incomplete pathways the 'Total' and 'unknown clock start' columns are
    # blank in the full extract; 'Total All' is populated and equals the band
    # sum exactly (asserted). Total is therefore rebuilt from the bands.
    inc["total_waiting"] = inc[all_bands].sum(axis=1)
    assert (inc["total_waiting"] - inc["Total All"]).abs().max() == 0, f"{period}: band sum != Total All"

    keys = {"Provider Org Code": "provider_code", "Provider Org Name": "provider_name",
            "Provider Parent Org Code": "provider_icb_ods", "Provider Parent Name": "provider_icb_name",
            "Treatment Function Code": "tfc_code", "Treatment Function Name": "tfc_name"}
    inc = inc.rename(columns=keys)

    # The file is provider x commissioner x TFC; roll commissioner out so grain is provider x TFC.
    tfc = (inc.groupby(["provider_code", "provider_name", "provider_icb_ods", "provider_icb_name", "tfc_code", "tfc_name"],
                       as_index=False)[["within_18", "over_52", "total_waiting"]].sum())
    tfc["pct_within_18"] = tfc.within_18 / tfc.total_waiting
    tfc["pct_over_52"] = tfc.over_52 / tfc.total_waiting
    assert not tfc.duplicated(["provider_code", "tfc_code"]).any(), f"{period}: grain violated: provider x tfc"

    prov = tfc[tfc.tfc_code == "C_999"].drop(columns=["tfc_code", "tfc_name"]).reset_index(drop=True)
    assert prov.provider_code.is_unique, f"{period}: grain violated: provider"
    # Cross-check: C_999 'Total' row equals the sum of the named TFCs for each provider.
    named = tfc[tfc.tfc_code != "C_999"].groupby("provider_code").total_waiting.sum()
    chk = prov.set_index("provider_code").total_waiting.sub(named, fill_value=0)
    assert (chk.abs() < 1).all(), f"{period}: C_999 total != sum of TFCs for {int((chk.abs() >= 1).sum())} providers"

    prov["provider_kind"] = prov.provider_code.str[0].map(
        {"R": "NHS trust", "N": "independent sector (N-code)"}).fillna("other (non-R/N ODS code)")
    prov.insert(0, "period", period)
    tfc.insert(0, "period", period)
    return prov, tfc


def main() -> None:
    provs, tfcs = [], []
    for period, zip_path in rtt_zips():
        prov, tfc = silver_month(period, zip_path)
        provs.append(prov)
        tfcs.append(tfc)
        eng_total = prov.total_waiting.sum()
        print(f"{period}: providers {len(prov)} | incomplete pathways {eng_total:,.0f} | within 18wk "
              f"{prov.within_18.sum() / eng_total:.1%} | >52wk {prov.over_52.sum():,.0f} | ICB parents {prov.provider_icb_ods.nunique()}")

    prov_all = pd.concat(provs, ignore_index=True)
    tfc_all = pd.concat(tfcs, ignore_index=True)
    assert not prov_all.duplicated(["period", "provider_code"]).any()
    prov_all.to_parquet(OUT / "rtt_provider.parquet", index=False)
    tfc_all.to_parquet(OUT / "rtt_provider_tfc.parquet", index=False)
    print("latest period:", prov_all.period.max(), "| kinds (latest):",
          prov_all[prov_all.period == prov_all.period.max()].provider_kind.value_counts().to_dict())


if __name__ == "__main__":
    main()
