from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests


GRID_PATH = Path("data/processed/coverage_grid.csv")
OUTPUT_PATH = Path("data/processed/grid_district_assignments.csv")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

HEADERS = {
    "User-Agent": (
        "BravoExpansionAnalysis/1.0 "
        "(https://github.com/lamanmamed/bravo-expansion-analysis)"
    )
}

DISTRICT_ALIASES = {
    "Binagadi": ["binəqədi", "binagadi"],
    "Khatai": ["xətai", "khatai"],
    "Khazar": ["xəzər", "khazar"],
    "Garadagh": ["qaradağ", "garadagh", "garadag"],
    "Narimanov": ["nərimanov", "narimanov"],
    "Nasimi": ["nəsimi", "nasimi"],
    "Nizami": ["nizami"],
    "Pirallahi": ["pirallahı", "pirallahi"],
    "Sabunchu": ["sabunçu", "sabunchu"],
    "Sabail": ["səbail", "sabail"],
    "Surakhani": ["suraxanı", "surakhani"],
    "Yasamal": ["yasamal"],
}


def normalise(value: object) -> str:
    return str(value or "").casefold().replace("ı", "i")


NORMALISED_ALIASES = {
    district: [normalise(alias) for alias in aliases]
    for district, aliases in DISTRICT_ALIASES.items()
}


def district_from_payload(payload: dict) -> str | None:
    address = payload.get("address") or {}
    pieces = [
        address.get("borough"),
        address.get("city_district"),
        address.get("district"),
        address.get("county"),
        address.get("suburb"),
        payload.get("display_name"),
    ]
    text = " | ".join(normalise(piece) for piece in pieces if piece)

    for district, aliases in NORMALISED_ALIASES.items():
        if any(alias in text for alias in aliases):
            return district

    return None


def reverse_lookup(
    session: requests.Session,
    latitude: float,
    longitude: float,
) -> tuple[str | None, str | None]:
    for zoom in (12, 10):
        response = session.get(
            NOMINATIM_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": zoom,
            },
            headers=HEADERS,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        district = district_from_payload(payload)
        if district:
            return district, payload.get("display_name")

        time.sleep(1.05)

    return None, payload.get("display_name")


def main() -> None:
    grid = pd.read_csv(GRID_PATH)

    required = {"cell_id", "centre_latitude", "centre_longitude"}
    missing = required - set(grid.columns)
    if missing:
        raise ValueError(f"Coverage grid is missing columns: {sorted(missing)}")

    session = requests.Session()
    rows = []

    for index, row in enumerate(grid.itertuples(index=False)):
        if index:
            time.sleep(1.05)

        district, display_name = reverse_lookup(
            session,
            float(row.centre_latitude),
            float(row.centre_longitude),
        )

        rows.append(
            {
                "cell_id": int(row.cell_id),
                "district": district,
                "reverse_geocode_name": display_name,
                "centre_latitude": float(row.centre_latitude),
                "centre_longitude": float(row.centre_longitude),
                "source": "OpenStreetMap via Nominatim reverse geocoding",
            }
        )

        print(
            f"{index + 1:03d}/{len(grid)} cell {row.cell_id}: "
            f"{district or 'UNMATCHED'}"
        )

    result = pd.DataFrame(rows)
    matched = int(result["district"].notna().sum())
    match_rate = matched / len(result)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print(f"Matched {matched}/{len(result)} cells ({match_rate:.1%}).")
    print(result["district"].value_counts(dropna=False).to_string())

    if match_rate < 0.75:
        raise RuntimeError(
            "Fewer than 75% of grid cells received a Baku district label."
        )


if __name__ == "__main__":
    main()
