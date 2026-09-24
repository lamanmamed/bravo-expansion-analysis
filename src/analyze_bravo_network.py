from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_PATH = Path("data/raw/bravo_stores.csv")
BOUNDARY_PATH = Path("data/raw/baku_boundary.geojson")
METRICS_PATH = Path("data/processed/bravo_store_metrics.csv")
SUMMARY_PATH = Path("outputs/network_summary.md")
FORMAT_CHART = Path("outputs/store_format_mix.png")
DISTANCE_CHART = Path("outputs/nearest_bravo_distance.png")

EARTH_RADIUS_KM = 6371.0088


def haversine_matrix(latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    lat = np.radians(latitudes)
    lon = np.radians(longitudes)

    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat[:, None])
        * np.cos(lat[None, :])
        * np.sin(dlon / 2) ** 2
    )
    distances = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))
    np.fill_diagonal(distances, np.inf)
    return distances


def safe_format(value: object) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "Unknown"
    return str(value).strip()


def main() -> None:
    raw_stores = pd.read_csv(INPUT_PATH)
    total_official_locations = len(raw_stores)

    stores = raw_stores.dropna(subset=["latitude", "longitude"]).copy()
    usable_coordinate_locations = len(stores)
    stores["store_format"] = stores["store_format"].map(safe_format)

    boundary = gpd.read_file(BOUNDARY_PATH).to_crs("EPSG:4326")
    study_polygon = boundary.geometry.union_all()

    store_points = gpd.GeoDataFrame(
        stores.copy(),
        geometry=gpd.points_from_xy(stores.longitude, stores.latitude),
        crs="EPSG:4326",
    )
    baku = store_points.loc[
        store_points.geometry.apply(study_polygon.covers)
    ].copy()
    baku = pd.DataFrame(baku.drop(columns="geometry"))

    lat = baku["latitude"].to_numpy(dtype=float)
    lon = baku["longitude"].to_numpy(dtype=float)
    distances = haversine_matrix(lat, lon)

    nearest_index = distances.argmin(axis=1)
    baku["nearest_bravo_km"] = distances.min(axis=1)
    baku["nearest_bravo_name"] = baku.iloc[nearest_index]["store_name"].to_numpy()
    baku["bravo_count_within_1km"] = (distances <= 1.0).sum(axis=1)
    baku["bravo_count_within_2km"] = (distances <= 2.0).sum(axis=1)

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    baku.sort_values("nearest_bravo_km", ascending=False).to_csv(
        METRICS_PATH, index=False
    )

    format_counts = baku["store_format"].value_counts()
    format_share = (100 * format_counts / len(baku)).round(1)

    median_nearest = float(baku["nearest_bravo_km"].median())
    p75_nearest = float(baku["nearest_bravo_km"].quantile(0.75))
    share_under_1km = float((baku["nearest_bravo_km"] <= 1.0).mean() * 100)
    share_under_2km = float((baku["nearest_bravo_km"] <= 2.0).mean() * 100)

    isolated = baku.nlargest(8, "nearest_bravo_km")[
        ["store_name", "store_format", "nearest_bravo_km", "nearest_bravo_name"]
    ]
    dense = baku.nlargest(8, "bravo_count_within_1km")[
        ["store_name", "store_format", "bravo_count_within_1km"]
    ]

    summary = [
        "# Bravo network summary",
        "",
        "This is a first-pass analysis of locations from Bravo's official store page.",
        "The network statistics use the same central Baku study polygon as the expansion screen.",
        "",
        "## Network size",
        "",
        f"- Official locations collected: **{total_official_locations}**",
        f"- Locations with usable coordinates: **{usable_coordinate_locations}**",
        f"- Locations inside the central Baku study area: **{len(baku)}**",
        f"- Median distance to the nearest other Bravo: **{median_nearest:.2f} km**",
        f"- 75th percentile nearest-store distance: **{p75_nearest:.2f} km**",
        f"- Stores with another Bravo within 1 km: **{share_under_1km:.1f}%**",
        f"- Stores with another Bravo within 2 km: **{share_under_2km:.1f}%**",
        "",
        "## Format mix in the central Baku study area",
        "",
        "| Format | Stores | Share |",
        "| --- | ---: | ---: |",
    ]

    for store_format, count in format_counts.items():
        summary.append(
            f"| {store_format} | {int(count)} | {float(format_share[store_format]):.1f}% |"
        )

    summary += [
        "",
        "## Most geographically isolated current stores",
        "",
        "These stores have the greatest straight-line distance to the nearest other Bravo. This is a network-spacing observation, not a profitability measure.",
        "",
        "| Store | Format | Nearest Bravo distance | Nearest Bravo |",
        "| --- | --- | ---: | --- |",
    ]

    for row in isolated.itertuples(index=False):
        summary.append(
            f"| {row.store_name} | {row.store_format} | {row.nearest_bravo_km:.2f} km | {row.nearest_bravo_name} |"
        )

    summary += [
        "",
        "## Densest current clusters",
        "",
        "These locations have the largest number of other Bravo stores within 1 km.",
        "",
        "| Store | Format | Other Bravo stores within 1 km |",
        "| --- | --- | ---: |",
    ]

    for row in dense.itertuples(index=False):
        summary.append(
            f"| {row.store_name} | {row.store_format} | {int(row.bravo_count_within_1km)} |"
        )

    summary += [
        "",
        "## Interpretation",
        "",
        "Nearest-store distance helps describe how tightly the existing network is clustered, but it is not enough to recommend new locations.",
        "The expansion stage adds population, surrounding food retail and public transport so that a coverage gap is only treated as interesting when there is also evidence of demand or accessibility.",
    ]

    SUMMARY_PATH.write_text("\n".join(summary) + "\n", encoding="utf-8")

    format_counts.sort_values().plot(kind="barh")
    plt.xlabel("Number of Bravo stores")
    plt.ylabel("Store format")
    plt.title("Bravo store formats in the central Baku study area")
    plt.tight_layout()
    plt.savefig(FORMAT_CHART, dpi=180)
    plt.close()

    baku["nearest_bravo_km"].plot(kind="hist", bins=18)
    plt.xlabel("Distance to nearest other Bravo (km)")
    plt.ylabel("Number of stores")
    plt.title("Spacing of Bravo stores in the central Baku study area")
    plt.tight_layout()
    plt.savefig(DISTANCE_CHART, dpi=180)
    plt.close()

    print(f"Analysed {len(baku)} central-Baku-study-area stores.")
    print(f"Median nearest Bravo distance: {median_nearest:.2f} km")
    print(f"Saved {SUMMARY_PATH}")


if __name__ == "__main__":
    main()