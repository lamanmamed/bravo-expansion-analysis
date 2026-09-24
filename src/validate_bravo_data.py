from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/raw/bravo_stores.csv")
EXPECTED_FORMATS = {"Hiper", "Super", "Market", "Express"}


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} does not exist. Run src/collect_bravo_stores.py first."
        )

    df = pd.read_csv(INPUT_PATH)

    duplicate_rows = df.duplicated(
        subset=["store_name", "latitude", "longitude"], keep=False
    )
    missing_coordinates = df[["latitude", "longitude"]].isna().any(axis=1)
    unexpected_formats = set(df["store_format"].dropna()) - EXPECTED_FORMATS

    print(f"Rows: {len(df)}")
    print(f"Duplicate location rows: {int(duplicate_rows.sum())}")
    print(f"Rows missing coordinates: {int(missing_coordinates.sum())}")
    print(f"Rows missing address: {int(df['address'].isna().sum())}")
    print(
        "Stores in initial Baku bbox: "
        f"{int(df['in_baku_study_bbox'].astype(str).str.lower().eq('true').sum())}"
    )

    print("\nStore formats:")
    print(df["store_format"].fillna("Unknown").value_counts().to_string())

    if unexpected_formats:
        print(f"\nUnexpected formats: {sorted(unexpected_formats)}")

    if duplicate_rows.any():
        print("\nPossible duplicates:")
        print(
            df.loc[
                duplicate_rows,
                ["store_name", "store_format", "latitude", "longitude"],
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
