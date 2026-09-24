from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup, NavigableString


SOURCE_URL = "https://www.bravosupermarket.az/en/branches/"
OUTPUT_PATH = Path("data/raw/bravo_stores.csv")

# Broad first-pass study extent. A proper Baku boundary will replace this
# when the geospatial context pipeline is joined to the store data.
BAKU_BBOX = {
    "min_lat": 40.25,
    "max_lat": 40.60,
    "min_lon": 49.60,
    "max_lon": 50.20,
}

STORE_FORMATS = {
    "hiper": "Hiper",
    "super": "Super",
    "market": "Market",
    "express": "Express",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_destination(href: str) -> tuple[float | None, float | None]:
    query = parse_qs(urlparse(href).query)
    destination = query.get("destination", [None])[0]
    if not destination or "," not in destination:
        return None, None

    try:
        lat, lon = destination.split(",", maxsplit=1)
        return float(lat), float(lon)
    except ValueError:
        return None, None


def text_between(heading, anchor) -> list[str]:
    values: list[str] = []

    for node in heading.next_elements:
        if node is anchor:
            break
        if isinstance(node, NavigableString):
            text = clean_text(str(node))
            if text and (not values or values[-1] != text):
                values.append(text)

    return values


def looks_like_hours(text: str) -> bool:
    value = text.lower()
    return (
        value == "24/7"
        or bool(re.search(r"\b\d{1,2}:\d{2}\b", value))
        or "only in summer" in value
    )


def parse_store(anchor) -> dict | None:
    heading = anchor.find_previous("h3")
    if heading is None:
        return None

    name = clean_text(heading.get_text(" ", strip=True))
    if not name.lower().startswith("bravo"):
        return None

    lat, lon = parse_destination(anchor.get("href", ""))
    values = text_between(heading, anchor)

    store_format = None
    format_index = None
    for index, value in enumerate(values):
        normalised = value.lower().strip()
        if normalised in STORE_FORMATS:
            store_format = STORE_FORMATS[normalised]
            format_index = index
            break

    hours = next((value for value in values if looks_like_hours(value)), None)

    ignored = {
        name.lower(),
        "show on map",
        "google maps ilə get",
        "waze ilə get",
        "all",
        "bravo hiper",
        "bravo super",
        "bravo market",
        "bravo express",
    }

    address = None
    start = (format_index + 1) if format_index is not None else 0
    for value in values[start:]:
        low = value.lower()
        if low in ignored:
            continue
        if value.startswith("+994"):
            continue
        if looks_like_hours(value):
            continue
        if "google" in low or "waze" in low:
            continue
        address = value
        break

    in_baku_bbox = False
    if lat is not None and lon is not None:
        in_baku_bbox = (
            BAKU_BBOX["min_lat"] <= lat <= BAKU_BBOX["max_lat"]
            and BAKU_BBOX["min_lon"] <= lon <= BAKU_BBOX["max_lon"]
        )

    return {
        "store_name": name,
        "store_format": store_format,
        "address": address,
        "opening_hours": hours,
        "latitude": lat,
        "longitude": lon,
        "in_baku_study_bbox": in_baku_bbox,
        "google_maps_url": anchor.get("href"),
        "source_url": SOURCE_URL,
    }


def main() -> None:
    response = requests.get(
        SOURCE_URL,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; BravoExpansionAnalysis/1.0; "
                "+https://github.com/lamanmamed/bravo-expansion-analysis)"
            )
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    map_links = soup.find_all(
        "a",
        href=lambda href: href
        and "google.com/maps/dir" in href
        and "destination=" in href,
    )

    rows = []
    for anchor in map_links:
        parsed = parse_store(anchor)
        if parsed:
            rows.append(parsed)

    if not rows:
        raise RuntimeError(
            "No Bravo stores were parsed. The official page structure may have changed."
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(
        subset=["store_name", "latitude", "longitude"], keep="first"
    ).reset_index(drop=True)

    collected_at = datetime.now(timezone.utc).isoformat()
    df["collected_at_utc"] = collected_at

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df)} Bravo stores to {OUTPUT_PATH}")
    print(f"Stores inside initial Baku bbox: {int(df['in_baku_study_bbox'].sum())}")
    print("Formats:")
    print(df["store_format"].fillna("Unknown").value_counts().to_string())

    missing_coordinates = int(df[["latitude", "longitude"]].isna().any(axis=1).sum())
    missing_addresses = int(df["address"].isna().sum())
    if missing_coordinates:
        print(f"Warning: {missing_coordinates} rows have missing coordinates.")
    if missing_addresses:
        print(f"Warning: {missing_addresses} rows have missing addresses.")


if __name__ == "__main__":
    main()
