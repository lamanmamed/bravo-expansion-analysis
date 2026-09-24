from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box


CRS_METRIC = "EPSG:32639"
GRID_SIZE_M = 1000
BRAVO_RADIUS_M = 1500
COMPETITOR_RADIUS_M = 1500
TRANSIT_RADIUS_M = 1000

BRAVO_PATH = Path("data/raw/bravo_stores.csv")
BOUNDARY_PATH = Path("data/raw/baku_boundary.geojson")
RETAIL_PATH = Path("data/raw/osm_food_retail.geojson")
TRANSIT_PATH = Path("data/raw/osm_transit.geojson")

OUTPUT_GEOJSON = Path("data/processed/coverage_grid.geojson")
OUTPUT_CSV = Path("data/processed/coverage_grid.csv")
OUTPUT_MAP = Path("outputs/coverage_gap_map.html")


def minmax(series: pd.Series) -> pd.Series:
    minimum = series.min()
    maximum = series.max()
    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - minimum) / (maximum - minimum)


def to_point_layer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    projected = gdf.to_crs(CRS_METRIC).copy()
    projected["geometry"] = projected.geometry.centroid
    return projected


def build_grid(boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    boundary_metric = boundary.to_crs(CRS_METRIC)
    study = boundary_metric.geometry.union_all()

    minx, miny, maxx, maxy = study.bounds
    cells = []
    cell_id = 0

    x = np.floor(minx / GRID_SIZE_M) * GRID_SIZE_M
    while x < maxx:
        y = np.floor(miny / GRID_SIZE_M) * GRID_SIZE_M
        while y < maxy:
            cell = box(x, y, x + GRID_SIZE_M, y + GRID_SIZE_M)
            centre = cell.centroid
            if study.contains(centre):
                cells.append({"cell_id": cell_id, "geometry": cell})
                cell_id += 1
            y += GRID_SIZE_M
        x += GRID_SIZE_M

    return gpd.GeoDataFrame(cells, crs=CRS_METRIC)


def distance_features(
    centres: gpd.GeoSeries,
    points: gpd.GeoDataFrame,
    radius_m: float,
    prefix: str,
) -> tuple[list[float], list[int]]:
    if points.empty:
        return [np.nan] * len(centres), [0] * len(centres)

    point_geometries = points.geometry
    nearest = []
    counts = []

    for centre in centres:
        distances = point_geometries.distance(centre)
        nearest.append(float(distances.min()))
        counts.append(int((distances <= radius_m).sum()))

    return nearest, counts


def main() -> None:
    required = [BRAVO_PATH, BOUNDARY_PATH, RETAIL_PATH, TRANSIT_PATH]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing inputs: " + ", ".join(missing)
            + ". Run the collection scripts first."
        )

    boundary = gpd.read_file(BOUNDARY_PATH)

    bravo = pd.read_csv(BRAVO_PATH)
    bravo = bravo.dropna(subset=["latitude", "longitude"]).copy()
    bravo_points = gpd.GeoDataFrame(
        bravo,
        geometry=gpd.points_from_xy(bravo.longitude, bravo.latitude),
        crs="EPSG:4326",
    ).to_crs(CRS_METRIC)

    retail = gpd.read_file(RETAIL_PATH)
    retail_text = (
        retail.get("name", pd.Series("", index=retail.index)).fillna("").astype(str)
        + " "
        + retail.get("brand", pd.Series("", index=retail.index)).fillna("").astype(str)
        + " "
        + retail.get("operator", pd.Series("", index=retail.index)).fillna("").astype(str)
    ).str.lower()
    competitors = retail.loc[~retail_text.str.contains("bravo", regex=False)].copy()
    competitors = to_point_layer(competitors)

    transit = to_point_layer(gpd.read_file(TRANSIT_PATH))

    grid = build_grid(boundary)
    centres = grid.geometry.centroid

    bravo_nearest, bravo_counts = distance_features(
        centres, bravo_points, BRAVO_RADIUS_M, "bravo"
    )
    competitor_nearest, competitor_counts = distance_features(
        centres, competitors, COMPETITOR_RADIUS_M, "competitor"
    )
    transit_nearest, transit_counts = distance_features(
        centres, transit, TRANSIT_RADIUS_M, "transit"
    )

    grid["nearest_bravo_km"] = np.array(bravo_nearest) / 1000
    grid["bravo_count_1_5km"] = bravo_counts
    grid["nearest_competitor_km"] = np.array(competitor_nearest) / 1000
    grid["competitor_count_1_5km"] = competitor_counts
    grid["nearest_transit_km"] = np.array(transit_nearest) / 1000
    grid["transit_count_1km"] = transit_counts

    # Coverage-gap baseline only. This is not the final expansion score.
    # A high value means a cell is relatively far from Bravo and has few
    # existing Bravo stores nearby.
    distance_signal = minmax(grid["nearest_bravo_km"].fillna(0))
    density_signal = 1 - minmax(grid["bravo_count_1_5km"])
    grid["coverage_gap_score"] = 0.7 * distance_signal + 0.3 * density_signal
    grid["coverage_gap_rank"] = grid["coverage_gap_score"].rank(
        method="min", ascending=False
    ).astype(int)

    centres_wgs84 = gpd.GeoSeries(centres, crs=CRS_METRIC).to_crs("EPSG:4326")
    grid["centre_latitude"] = centres_wgs84.y.values
    grid["centre_longitude"] = centres_wgs84.x.values

    OUTPUT_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MAP.parent.mkdir(parents=True, exist_ok=True)

    grid_wgs84 = grid.to_crs("EPSG:4326")
    grid_wgs84.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    grid.drop(columns="geometry").sort_values("coverage_gap_rank").to_csv(
        OUTPUT_CSV, index=False
    )

    map_centre = [
        float(grid["centre_latitude"].median()),
        float(grid["centre_longitude"].median()),
    ]
    m = folium.Map(location=map_centre, zoom_start=10, tiles="OpenStreetMap")

    top = grid.nsmallest(30, "coverage_gap_rank")
    for row in top.itertuples(index=False):
        folium.CircleMarker(
            location=[row.centre_latitude, row.centre_longitude],
            radius=7,
            color="#8b2f23",
            fill=True,
            fill_opacity=0.75,
            tooltip=(
                f"Rank {row.coverage_gap_rank} | "
                f"nearest Bravo {row.nearest_bravo_km:.2f} km | "
                f"Bravo within 1.5 km: {row.bravo_count_1_5km}"
            ),
        ).add_to(m)

    for row in bravo.itertuples(index=False):
        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=3,
            color="#2d5b3b",
            fill=True,
            fill_opacity=0.7,
            tooltip=row.store_name,
        ).add_to(m)

    m.save(OUTPUT_MAP)

    print(f"Created {len(grid)} 1 km candidate cells.")
    print(f"Saved {OUTPUT_CSV}")
    print(f"Saved {OUTPUT_GEOJSON}")
    print(f"Saved {OUTPUT_MAP}")


if __name__ == "__main__":
    main()