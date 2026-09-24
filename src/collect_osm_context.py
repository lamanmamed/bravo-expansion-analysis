from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import osmnx as ox


PLACE = "Baku, Azerbaijan"
RAW_DIR = Path("data/raw")


def keep_columns(gdf: gpd.GeoDataFrame, columns: list[str]) -> gpd.GeoDataFrame:
    available = [column for column in columns if column in gdf.columns]
    if "geometry" not in available:
        available.append("geometry")
    return gdf[available].copy()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    boundary = ox.geocode_to_gdf(PLACE)
    boundary.to_file(RAW_DIR / "baku_boundary.geojson", driver="GeoJSON")

    retail = ox.features_from_place(
        PLACE,
        tags={"shop": ["supermarket", "convenience"]},
    )
    retail = keep_columns(
        retail,
        [
            "name",
            "brand",
            "shop",
            "operator",
            "addr:street",
            "addr:housenumber",
            "geometry",
        ],
    )
    retail = retail.reset_index()
    retail.to_file(RAW_DIR / "osm_food_retail.geojson", driver="GeoJSON")

    transit = ox.features_from_place(
        PLACE,
        tags={
            "railway": ["station", "subway_entrance"],
            "station": "subway",
            "public_transport": ["station", "stop_position"],
        },
    )
    transit = keep_columns(
        transit,
        ["name", "railway", "station", "public_transport", "geometry"],
    )
    transit = transit.reset_index()
    transit.to_file(RAW_DIR / "osm_transit.geojson", driver="GeoJSON")

    print(f"Saved {len(retail)} food-retail features.")
    print(f"Saved {len(transit)} public-transport features.")
    print("Saved Baku boundary.")


if __name__ == "__main__":
    main()
