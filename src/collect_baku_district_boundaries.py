from __future__ import annotations

import json
import time
from pathlib import Path

import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OUTPUT_PATH = Path("data/raw/baku_district_boundaries.geojson")

DISTRICT_QUERIES = {
    "Binagadi": ["Binəqədi rayonu, Bakı, Azərbaycan", "Binagadi, Baku, Azerbaijan"],
    "Khatai": ["Xətai rayonu, Bakı, Azərbaycan", "Khatai, Baku, Azerbaijan"],
    "Khazar": ["Xəzər rayonu, Bakı, Azərbaycan", "Khazar, Baku, Azerbaijan"],
    "Garadagh": ["Qaradağ rayonu, Bakı, Azərbaycan", "Garadagh, Baku, Azerbaijan"],
    "Narimanov": ["Nərimanov rayonu, Bakı, Azərbaycan", "Narimanov, Baku, Azerbaijan"],
    "Nasimi": ["Nəsimi rayonu, Bakı, Azərbaycan", "Nasimi, Baku, Azerbaijan"],
    "Nizami": ["Nizami rayonu, Bakı, Azərbaycan", "Nizami district, Baku, Azerbaijan"],
    "Pirallahi": [
        "Pirallahı rayonu, Bakı, Azərbaycan",
        "Pirallahı rayonu, Azərbaycan",
        "Pirallahi district, Azerbaijan",
        "Pirallahi, Baku, Azerbaijan",
    ],
    "Sabunchu": ["Sabunçu rayonu, Bakı, Azərbaycan", "Sabunchu, Baku, Azerbaijan"],
    "Sabail": ["Səbail rayonu, Bakı, Azərbaycan", "Sabail, Baku, Azerbaijan"],
    "Surakhani": ["Suraxanı rayonu, Bakı, Azərbaycan", "Surakhani, Baku, Azerbaijan"],
    "Yasamal": ["Yasamal rayonu, Bakı, Azərbaycan", "Yasamal, Baku, Azerbaijan"],
}

HEADERS = {
    "User-Agent": (
        "BravoExpansionAnalysis/1.0 "
        "(https://github.com/lamanmamed/bravo-expansion-analysis)"
    )
}


def search_polygon(district: str, queries: list[str]) -> dict:
    for query in queries:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "geojson",
                "polygon_geojson": 1,
                "addressdetails": 1,
                "countrycodes": "az",
                "limit": 8,
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
            osm_type = str(properties.get("osm_type", "")).lower()
            category = str(properties.get("category", "")).lower()
            feature_type = str(properties.get("type", "")).lower()

            # Do not accept a building/POI polygon just because it happens to
            # contain the district name in its address.
            if osm_type != "relation":
                continue
            if category and category != "boundary" and feature_type != "administrative":
                continue

            # Baku's districts may be labelled in either English or Azerbaijani.
            if "baku" not in display_name and "bakı" not in display_name:
                if district != "Pirallahi":
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

    raise RuntimeError(
        f"No administrative relation found for {district}. Tried: {queries}"
    )


def main() -> None:
    features = []

    missing = []

    for index, (district, queries) in enumerate(DISTRICT_QUERIES.items()):
        if index:
            time.sleep(1.1)

        try:
            feature = search_polygon(district, queries)
        except RuntimeError as error:
            missing.append(district)
            print(f"WARNING: {error}")
            continue

        features.append(feature)
        print(
            f"Found {district}: "
            f"{feature['properties'].get('display_name', '')}"
        )

    if len(features) < 10:
        raise RuntimeError(
            f"Only {len(features)} of {len(DISTRICT_QUERIES)} district "
            f"boundaries were found. Missing: {missing}"
        )

    if missing:
        print(f"Missing district boundaries kept explicit: {missing}")

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