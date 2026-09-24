from __future__ import annotations

import json
import time
from pathlib import Path

import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OUTPUT_PATH = Path("data/raw/baku_district_boundaries.geojson")

DISTRICTS = [
    "Binagadi",
    "Khatai",
    "Khazar",
    "Garadagh",
    "Narimanov",
    "Nasimi",
    "Nizami",
    "Pirallahi",
    "Sabunchu",
    "Sabail",
    "Surakhani",
    "Yasamal",
]

HEADERS = {
    "User-Agent": (
        "BravoExpansionAnalysis/1.0 "
        "(https://github.com/lamanmamed/bravo-expansion-analysis)"
    )
}


def search_polygon(district: str) -> dict:
    queries = [
        f"{district} district, Baku, Azerbaijan",
        f"{district} rayon, Baku, Azerbaijan",
        f"{district}, Baku, Azerbaijan",
    ]

    for query in queries:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "geojson",
                "polygon_geojson": 1,
                "addressdetails": 1,
                "countrycodes": "az",
                "limit": 5,
            },
            headers=HEADERS,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        for feature in payload.get("features", []):
            geometry_type = (feature.get("geometry") or {}).get("type")
            if geometry_type not in {"Polygon", "MultiPolygon"}:
                continue

            properties = feature.get("properties") or {}
            display_name = str(properties.get("display_name", "")).lower()

            if "baku" not in display_name and "bakı" not in display_name:
                continue

            feature["properties"] = {
                "district": district,
                "display_name": properties.get("display_name"),
                "osm_type": properties.get("osm_type"),
                "osm_id": properties.get("osm_id"),
                "source": "OpenStreetMap via Nominatim",
            }
            return feature

        time.sleep(1.1)

    raise RuntimeError(f"No polygon boundary found for {district}")


def main() -> None:
    features = []

    for index, district in enumerate(DISTRICTS):
        if index:
            time.sleep(1.1)
        feature = search_polygon(district)
        features.append(feature)
        print(f"Found boundary for {district}")

    if len(features) != len(DISTRICTS):
        raise RuntimeError(
            f"Expected {len(DISTRICTS)} district boundaries, found {len(features)}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Saved {len(features)} Baku district boundaries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
