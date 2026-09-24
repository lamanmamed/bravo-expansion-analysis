from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests


SOURCE_URL = "https://www.stat.gov.az/source/demoqraphy/en/001_15en.xls"
RAW_XLS = Path("data/raw/stat_population_area_density.xls")
RAW_CSV = Path("data/raw/stat_population_area_density_raw.csv")
BAKU_CSV = Path("data/processed/baku_district_population_2025.csv")

TARGETS = {
    "Baku": ["baku city", "baku"],
    "Binagadi": ["binagadi"],
    "Khatai": ["khatai"],
    "Khazar": ["khazar"],
    "Garadagh": ["garadagh"],
    "Narimanov": ["narimanov"],
    "Nasimi": ["nasimi"],
    "Nizami": ["nizami"],
    "Pirallahi": ["pirallahi"],
    "Sabunchu": ["sabunchu"],
    "Sabail": ["sabail"],
    "Surakhani": ["surakhani"],
    "Yasamal": ["yasamal"],
}


def normalise_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def numeric_values(row: pd.Series) -> list[float]:
    values: list[float] = []
    for value in row.tolist():
        if pd.isna(value):
            continue
        if isinstance(value, (int, float)):
            values.append(float(value))
            continue

        text = str(value).strip().replace(" ", "")
        if not text:
            continue

        try:
            values.append(float(text.replace(",", ".")))
        except ValueError:
            pass

    return values


def find_row(table: pd.DataFrame, aliases: list[str]) -> pd.Series:
    candidates = []

    for index, row in table.iterrows():
        joined = " | ".join(
            normalise_text(value)
            for value in row.tolist()
            if not pd.isna(value)
        )
        if any(alias in joined for alias in aliases):
            candidates.append((index, row, joined))

    if not candidates:
        raise ValueError(f"Could not find row matching {aliases}")

    # Prefer the row with the most numeric values. This avoids title/header rows
    # that may mention a district name without containing the actual data.
    candidates.sort(key=lambda item: len(numeric_values(item[1])), reverse=True)
    return candidates[0][1]


def extract_baku_table(table: pd.DataFrame) -> pd.DataFrame:
    records = []

    for district, aliases in TARGETS.items():
        row = find_row(table, aliases)
        numbers = numeric_values(row)

        # The official table supplies four values for each territorial unit:
        # area, 2019 census population, current population, and density.
        if len(numbers) < 4:
            raise ValueError(
                f"{district}: expected at least 4 numeric values, found {numbers}"
            )

        area_sq_km_thousand, census_2019_thousand, population_2025_thousand, density = numbers[-4:]

        records.append(
            {
                "district": district,
                "area_thousand_sq_km": area_sq_km_thousand,
                "area_sq_km": area_sq_km_thousand * 1000,
                "census_2019_thousand": census_2019_thousand,
                "population_2025_thousand": population_2025_thousand,
                "population_2025": population_2025_thousand * 1000,
                "density_per_sq_km": density,
                "source_url": SOURCE_URL,
            }
        )

    result = pd.DataFrame(records)

    # Simple source-consistency checks. These catch accidental header matches or
    # column shifts without replacing the official values with hard-coded data.
    baku = result.loc[result["district"] == "Baku"].iloc[0]
    districts = result.loc[result["district"] != "Baku"]

    if not 1_000_000 < baku["population_2025"] < 5_000_000:
        raise ValueError("Parsed Baku population is outside a plausible range.")

    if districts["population_2025"].sum() < 0.8 * baku["population_2025"]:
        raise ValueError("District totals are unexpectedly low relative to Baku total.")

    return result


def main() -> None:
    response = requests.get(
        SOURCE_URL,
        timeout=60,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; BravoExpansionAnalysis/1.0; "
                "+https://github.com/lamanmamed/bravo-expansion-analysis)"
            )
        },
    )
    response.raise_for_status()

    RAW_XLS.parent.mkdir(parents=True, exist_ok=True)
    BAKU_CSV.parent.mkdir(parents=True, exist_ok=True)
    RAW_XLS.write_bytes(response.content)

    workbook = pd.ExcelFile(RAW_XLS)
    frames = []

    for sheet_name in workbook.sheet_names:
        sheet = pd.read_excel(RAW_XLS, sheet_name=sheet_name, header=None)
        sheet.insert(0, "sheet_name", sheet_name)
        frames.append(sheet)

    raw = pd.concat(frames, ignore_index=True)
    raw.to_csv(RAW_CSV, index=False)

    baku = extract_baku_table(raw)
    baku.to_csv(BAKU_CSV, index=False)

    print(f"Downloaded official population table from {SOURCE_URL}")
    print(f"Sheets: {workbook.sheet_names}")
    print(f"Saved raw table to {RAW_CSV} with {len(raw)} rows")
    print(f"Saved Baku district table to {BAKU_CSV}")
    print()
    print(baku.to_string(index=False))


if __name__ == "__main__":
    main()
