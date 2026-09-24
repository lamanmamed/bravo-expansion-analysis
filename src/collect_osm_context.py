from __future__ import annotations

import json
import time
from pathlib import Path

import requests


RAW_DIR = Path("data/raw")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Broad collection extent. The analysis itself is clipped to the Baku boundary.
SOUTH, WEST, NORTH, EAST = 40.25, 49.60, 40.60, 50.20

HEADERS = {
    "User-Agent": (
        "BravoExpansionAnalysis/1.0 "
        "(https://github.com/lamanmamed/bravo-expansion-analysis)"
    )
}


def point_feature(element: dict) -> dict | None:
    lat = element.get("lat")
    lon = element.get("lon")

    if lat is None or lon is None:
        centre = element.get("center") or {}
        lat = centre.get("lat")
        lon = centre.get("lon")

    if lat is None or lon is None:
        return None

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(lon), float(lat)],
        },
        "properties": {
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            **(element.get("tags") or {}),
        },
    }


def save_geojson(path: Path, features: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def collect_boundary() -> None:
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": "Baku, Azerbaijan",
            "format": "geojson",
            "polygon_geojson": 1,
            "limit": 1,
        },
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("features"):
        raise RuntimeError("Nominatim returned no Baku boundary.")

    save_geojson(
        RAW_DIR / "baku_boundary.geojson",
        [payload["features"][0]],
    )


def run_overpass(query: str) -> list[dict]:
    errors = []

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                data={"data": query},
                headers=HEADERS,
                timeout=150,
            )
            response.raise_for_status()
            return response.json().get("elements", [])
        except requests.RequestException as error:
            errors.append(f"{endpoint}: {error}")
            print(f"Overpass endpoint failed: {endpoint}: {error}")
            time.sleep(2)

    raise RuntimeError("All Overpass endpoints failed: " + " | ".join(errors))


def collect_retail() -> int:
    bbox = f"{SOUTH},{WEST},{NORTH},{EAST}"
    query = f"""
    [out:json][timeout:120];
    nwr["shop"~"^(supermarket|convenience)$"]({bbox});
    out center tags;
    """

    features = []
    for element in run_overpass(query):
        feature = point_feature(element)
        if feature is not None:
            features.append(feature)

    save_geojson(RAW_DIR / "osm_food_retail.geojson", features)
    return len(features)


def collect_transit() -> int:
    bbox = f"{SOUTH},{WEST},{NORTH},{EAST}"
    query = f"""
    [out:json][timeout:120];
    (
      nwr["railway"~"^(station|subway_entrance)$"]({bbox});
      nwr["station"="subway"]({bbox});
      nwr["public_transport"~"^(station|stop_position)$"]({bbox});
    );
    out center tags;
    """

    features = []
    for element in run_overpass(query):
        feature = point_feature(element)
        if feature is not None:
            features.append(feature)

    # The same OSM object can satisfy more than one transit tag.
    unique = {
        (feature["properties"]["osm_type"], feature["properties"]["osm_id"]): feature
        for feature in features
    }
    save_geojson(RAW_DIR / "osm_transit.geojson", list(unique.values()))
    return len(unique)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    collect_boundary()
    retail_count = collect_retail()
    transit_count = collect_transit()

    print(f"Saved {retail_count} supermarket/convenience features.")
    print(f"Saved {transit_count} public-transport features.")
    print("Saved Baku boundary.")


if __name__ == "__main__":
    main()
