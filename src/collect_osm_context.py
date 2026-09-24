from __future__ import annotations

import json
from pathlib import Path

import requests


RAW_DIR = Path("data/raw")
OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Broad Baku study extent used only to collect candidate context.
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

    tags = element.get("tags", {})
    properties = {
        "osm_type": element.get("type"),
        "osm_id": element.get("id"),
        **tags,
    }

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(lon), float(lat)],
        },
        "properties": properties,
    }


def save_geojson(path: Path, features: list[dict]) -> None:
    payload = {
        "type": "FeatureCollection",
        "features": features,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def collect_boundary() -> None:
    params = {
        "q": "Baku, Azerbaijan",
        "format": "geojson",
        "polygon_geojson": 1,
        "limit": 1,
    }
    response = requests.get(
        NOMINATIM_URL,
        params=params,
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


def collect_context() -> tuple[int, int]:
    bbox = f"{SOUTH},{WEST},{NORTH},{EAST}"
    query = f"""
    [out:json][timeout:120];
    (
      node["shop"~"^(supermarket|convenience)$"]({bbox});
      way["shop"~"^(supermarket|convenience)$"]({bbox});
      relation["shop"~"^(supermarket|convenience)$"]({bbox});

      node["railway"~"^(station|subway_entrance)$"]({bbox});
      way["railway"="station"]({bbox});
      relation["railway"="station"]({bbox});

      node["station"="subway"]({bbox});
      way["station"="subway"]({bbox});
      relation["station"="subway"]({bbox});

      node["public_transport"~"^(station|stop_position)$"]({bbox});
    );
    out center tags;
    """

    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=180,
    )
    response.raise_for_status()

    retail: list[dict] = []
    transit: list[dict] = []

    for element in response.json().get("elements", []):
        feature = point_feature(element)
        if feature is None:
            continue

        tags = element.get("tags", {})
        if tags.get("shop") in {"supermarket", "convenience"}:
            retail.append(feature)

        if (
            tags.get("railway") in {"station", "subway_entrance"}
            or tags.get("station") == "subway"
            or tags.get("public_transport") in {"station", "stop_position"}
        ):
            transit.append(feature)

    save_geojson(RAW_DIR / "osm_food_retail.geojson", retail)
    save_geojson(RAW_DIR / "osm_transit.geojson", transit)

    return len(retail), len(transit)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    collect_boundary()
    retail_count, transit_count = collect_context()

    print(f"Saved {retail_count} supermarket/convenience features.")
    print(f"Saved {transit_count} public-transport features.")
    print("Saved Baku boundary.")


if __name__ == "__main__":
    main()
