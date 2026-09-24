from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests


SOURCE_URL = "https://www.stat.gov.az/source/demoqraphy/en/001_15en.xls"
RAW_XLS = Path("data/raw/stat_population_area_density.xls")
RAW_CSV = Path("data/raw/stat_population_area_density_raw.csv")


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
    RAW_XLS.write_bytes(response.content)

    workbook = pd.ExcelFile(RAW_XLS)
    frames = []

    for sheet_name in workbook.sheet_names:
        sheet = pd.read_excel(RAW_XLS, sheet_name=sheet_name, header=None)
        sheet.insert(0, "sheet_name", sheet_name)
        frames.append(sheet)

    raw = pd.concat(frames, ignore_index=True)
    raw.to_csv(RAW_CSV, index=False)

    print(f"Downloaded official population table from {SOURCE_URL}")
    print(f"Sheets: {workbook.sheet_names}")
    print(f"Saved raw table to {RAW_CSV} with {len(raw)} rows")


if __name__ == "__main__":
    main()
