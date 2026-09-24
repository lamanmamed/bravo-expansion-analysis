from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd


BOUNDARY_PATH = Path("data/raw/baku_boundary.geojson")
BRAVO_PATH = Path("data/raw/bravo_stores.csv")
CELLS_PATH = Path("data/processed/expansion_screen_cells.geojson")
ZONES_PATH = Path("data/processed/candidate_zones.csv")

NETWORK_OUTPUT = Path("outputs/readme_bravo_network.png")
SHORTLIST_OUTPUT = Path("outputs/readme_shortlist_map.png")


FORMAT_COLORS = {
    "Express": "#3f6b57",
    "Market": "#75917f",
    "Super": "#b57c4a",
    "Hiper": "#7a4848",
    "Premium": "#6f5b82",
    "Unknown": "#8a8a8a",
}


def load_store_points(boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    stores = pd.read_csv(BRAVO_PATH).dropna(
        subset=["latitude", "longitude"]
    ).copy()
    stores["store_format"] = stores["store_format"].fillna("Unknown")

    points = gpd.GeoDataFrame(
        stores,
        geometry=gpd.points_from_xy(stores.longitude, stores.latitude),
        crs="EPSG:4326",
    )

    polygon = boundary.geometry.union_all()
    return points.loc[points.geometry.apply(polygon.covers)].copy()


def set_map_extent(ax, boundary: gpd.GeoDataFrame) -> None:
    minx, miny, maxx, maxy = boundary.total_bounds
    xpad = (maxx - minx) * 0.04
    ypad = (maxy - miny) * 0.04
    ax.set_xlim(minx - xpad, maxx + xpad)
    ax.set_ylim(miny - ypad, maxy + ypad)
    ax.set_axis_off()


def build_network_map(
    boundary: gpd.GeoDataFrame,
    stores: gpd.GeoDataFrame,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 7.2))

    boundary.plot(
        ax=ax,
        facecolor="#f4f1ea",
        edgecolor="#b8b2a8",
        linewidth=1.1,
    )

    handles = []
    for store_format in ["Express", "Market", "Super", "Hiper", "Premium", "Unknown"]:
        subset = stores.loc[stores["store_format"] == store_format]
        if subset.empty:
            continue

        color = FORMAT_COLORS[store_format]
        subset.plot(
            ax=ax,
            color=color,
            markersize=30 if store_format in {"Hiper", "Super"} else 20,
            alpha=0.9,
            edgecolor="white",
            linewidth=0.45,
        )
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=color,
                markeredgecolor="white",
                markeredgewidth=0.5,
                markersize=8,
                label=f"{store_format} ({len(subset)})",
            )
        )

    ax.set_title(
        f"Bravo's current network in the mapped part of Baku\n"
        f"{len(stores)} stores with usable coordinates",
        loc="left",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )

    ax.legend(
        handles=handles,
        title="Store format",
        loc="lower left",
        frameon=True,
        framealpha=0.96,
    )

    set_map_extent(ax, boundary)
    plt.tight_layout()
    NETWORK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(NETWORK_OUTPUT, dpi=190, bbox_inches="tight")
    plt.close()


def build_shortlist_map(
    boundary: gpd.GeoDataFrame,
    stores: gpd.GeoDataFrame,
) -> None:
    cells = gpd.read_file(CELLS_PATH).to_crs("EPSG:4326")
    zones = pd.read_csv(ZONES_PATH).sort_values("screening_rank")

    robust = cells.loc[
        pd.to_numeric(cells["robust_top15_hits"], errors="coerce").fillna(0) >= 2
    ].copy()

    fig, ax = plt.subplots(figsize=(10, 7.2))

    boundary.plot(
        ax=ax,
        facecolor="#f7f4ee",
        edgecolor="#b8b2a8",
        linewidth=1.1,
    )

    if not robust.empty:
        robust.plot(
            ax=ax,
            facecolor="#e9c989",
            edgecolor="#c39952",
            linewidth=0.6,
            alpha=0.62,
        )

    stores.plot(
        ax=ax,
        color="#577363",
        markersize=13,
        alpha=0.62,
        edgecolor="white",
        linewidth=0.3,
    )

    offsets = {
        1: (10, 11),
        2: (10, -18),
        3: (-78, -18),
        4: (10, 11),
    }

    for row in zones.itertuples(index=False):
        rank = int(row.screening_rank)
        x = row.centre_longitude
        y = row.centre_latitude

        ax.scatter(
            x,
            y,
            s=260,
            facecolor="#ffffff",
            edgecolor="#222222",
            linewidth=1.5,
            zorder=6,
        )
        ax.text(
            x,
            y,
            str(rank),
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            zorder=7,
        )

        dx, dy = offsets.get(rank, (8, 8))
        ax.annotate(
            f"{rank}. {row.district}",
            (x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "edgecolor": "#d8d2c7",
                "alpha": 0.96,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": "#666666",
                "linewidth": 0.8,
            },
            zorder=8,
        )

    ax.set_title(
        "Four areas worth a closer look\n"
        "Shortlisted after combining gaps in Bravo coverage with local context",
        loc="left",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )

    legend_items = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#577363",
            markeredgecolor="white",
            markersize=7,
            label="Current Bravo store",
        ),
        Patch(
            facecolor="#e9c989",
            edgecolor="#c39952",
            label="Robust shortlisted grid cells",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="white",
            markeredgecolor="#222222",
            markersize=10,
            label="Candidate zone",
        ),
    ]
    ax.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.96,
    )

    set_map_extent(ax, boundary)
    plt.tight_layout()
    SHORTLIST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SHORTLIST_OUTPUT, dpi=190, bbox_inches="tight")
    plt.close()


def main() -> None:
    boundary = gpd.read_file(BOUNDARY_PATH).to_crs("EPSG:4326")
    stores = load_store_points(boundary)

    build_network_map(boundary, stores)
    build_shortlist_map(boundary, stores)

    print(f"Saved {NETWORK_OUTPUT}")
    print(f"Saved {SHORTLIST_OUTPUT}")


if __name__ == "__main__":
    main()
