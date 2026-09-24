from __future__ import annotations

from collections import Counter
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


GRID_PATH = Path("data/processed/coverage_grid.geojson")
DISTRICT_ASSIGNMENTS_PATH = Path("data/processed/grid_district_assignments.csv")
POPULATION_PATH = Path("data/processed/baku_district_population_2026.csv")
BRAVO_PATH = Path("data/raw/bravo_stores.csv")

CELL_CSV = Path("data/processed/expansion_screen_cells.csv")
CELL_GEOJSON = Path("data/processed/expansion_screen_cells.geojson")
ZONE_CSV = Path("data/processed/candidate_zones.csv")
SUMMARY_PATH = Path("outputs/expansion_screen_summary.md")
MAP_PATH = Path("outputs/expansion_screen_map.html")
STATIC_MAP_PATH = Path("outputs/expansion_screen_map.png")
VALIDATION_CHART_PATH = Path("outputs/model_validation_auc.png")

CRS_METRIC = "EPSG:32639"
MIN_BRAVO_GAP_KM = 1.5
ZONE_CLUSTER_EPS_M = 1600

MODEL_FEATURES = [
    "log_population_density",
    "log_competitor_count",
    "nearest_competitor_km_capped",
    "log_transit_count",
    "nearest_transit_km_capped",
]
BASELINE_FEATURES = ["log_population_density"]


def safe_minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    minimum = values.min()
    maximum = values.max()

    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series(np.zeros(len(values)), index=values.index)

    return (values - minimum) / (maximum - minimum)


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=42,
                ),
            ),
        ]
    )


def grouped_auc(
    frame: pd.DataFrame,
    features: list[str],
) -> tuple[float, float, int]:
    work = frame.dropna(subset=features + ["district", "has_bravo_1km"]).copy()

    groups = work["district"].astype(str)
    n_groups = groups.nunique()

    if n_groups < 3:
        return float("nan"), float("nan"), 0

    splitter = GroupKFold(n_splits=min(5, n_groups))
    scores = []

    X = work[features]
    y = work["has_bravo_1km"].astype(int)

    for train_index, test_index in splitter.split(X, y, groups):
        X_train = X.iloc[train_index]
        X_test = X.iloc[test_index]
        y_train = y.iloc[train_index]
        y_test = y.iloc[test_index]

        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue

        model = build_model()
        model.fit(X_train, y_train)
        probability = model.predict_proba(X_test)[:, 1]
        scores.append(roc_auc_score(y_test, probability))

    if not scores:
        return float("nan"), float("nan"), 0

    return float(np.mean(scores)), float(np.std(scores)), len(scores)


def weighted_geometric_mean(
    coverage: pd.Series,
    context: pd.Series,
    coverage_weight: float,
) -> pd.Series:
    epsilon = 1e-6
    return (
        np.clip(coverage, epsilon, 1) ** coverage_weight
        * np.clip(context, epsilon, 1) ** (1 - coverage_weight)
    )


def district_mode(values: pd.Series) -> str:
    cleaned = [str(value) for value in values.dropna() if str(value)]
    if not cleaned:
        return "Unknown"
    return Counter(cleaned).most_common(1)[0][0]


def main() -> None:
    required = [
        GRID_PATH,
        DISTRICT_ASSIGNMENTS_PATH,
        POPULATION_PATH,
        BRAVO_PATH,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required inputs: " + ", ".join(missing)
        )

    grid = gpd.read_file(GRID_PATH)
    district_assignments = pd.read_csv(DISTRICT_ASSIGNMENTS_PATH)
    population = pd.read_csv(POPULATION_PATH)
    population = population.loc[population["district"] != "Baku"].copy()

    grid = grid.merge(
        district_assignments[["cell_id", "district"]],
        on="cell_id",
        how="left",
    )
    grid = grid.merge(
        population[
            [
                "district",
                "population_2026",
                "density_per_sq_km",
            ]
        ],
        on="district",
        how="left",
    )

    matched = int(grid["density_per_sq_km"].notna().sum())
    if matched < 80:
        raise RuntimeError(
            f"Only {matched} grid cells matched a district population record."
        )

    grid["has_bravo_1km"] = (
        pd.to_numeric(grid["nearest_bravo_km"], errors="coerce") <= 1.0
    ).astype(int)

    grid["log_population_density"] = np.log1p(grid["density_per_sq_km"])
    grid["log_competitor_count"] = np.log1p(
        pd.to_numeric(grid["competitor_count_1_5km"], errors="coerce").fillna(0)
    )
    grid["nearest_competitor_km_capped"] = (
        pd.to_numeric(grid["nearest_competitor_km"], errors="coerce")
        .fillna(5)
        .clip(upper=5)
    )
    grid["log_transit_count"] = np.log1p(
        pd.to_numeric(grid["transit_count_1km"], errors="coerce").fillna(0)
    )
    grid["nearest_transit_km_capped"] = (
        pd.to_numeric(grid["nearest_transit_km"], errors="coerce")
        .fillna(5)
        .clip(upper=5)
    )

    baseline_auc, baseline_std, baseline_folds = grouped_auc(
        grid, BASELINE_FEATURES
    )
    full_auc, full_std, full_folds = grouped_auc(grid, MODEL_FEATURES)

    model_frame = grid.dropna(subset=MODEL_FEATURES + ["district"]).copy()
    context_model = build_model()
    context_model.fit(
        model_frame[MODEL_FEATURES],
        model_frame["has_bravo_1km"],
    )
    model_frame["context_fit_score"] = context_model.predict_proba(
        model_frame[MODEL_FEATURES]
    )[:, 1]

    grid = grid.merge(
        model_frame[["cell_id", "context_fit_score"]],
        on="cell_id",
        how="left",
    )

    grid["coverage_gap_score"] = pd.to_numeric(
        grid["coverage_gap_score"], errors="coerce"
    ).clip(0, 1)

    grid["eligible_gap"] = (
        pd.to_numeric(grid["nearest_bravo_km"], errors="coerce")
        >= MIN_BRAVO_GAP_KM
    ) & grid["context_fit_score"].notna()

    # Equal-weight geometric mean is the main screen. Unlike an arithmetic
    # average, it prevents a very strong value on one dimension from fully
    # compensating for a near-zero value on the other.
    grid["expansion_screen_score"] = np.where(
        grid["eligible_gap"],
        weighted_geometric_mean(
            grid["coverage_gap_score"],
            grid["context_fit_score"],
            0.5,
        ),
        np.nan,
    )

    eligible = grid.loc[grid["eligible_gap"]].copy()

    # Sensitivity check: vary the relative weight placed on coverage vs
    # external context rather than presenting one arbitrary weight as truth.
    rank_columns = []
    for coverage_weight in (0.4, 0.5, 0.6):
        suffix = int(coverage_weight * 100)
        score_col = f"screen_score_coverage_{suffix}"
        rank_col = f"rank_coverage_{suffix}"

        eligible[score_col] = weighted_geometric_mean(
            eligible["coverage_gap_score"],
            eligible["context_fit_score"],
            coverage_weight,
        )
        eligible[rank_col] = eligible[score_col].rank(
            method="min", ascending=False
        ).astype(int)
        rank_columns.append(rank_col)

    eligible["robust_top15_hits"] = (
        eligible[rank_columns].le(15).sum(axis=1)
    )
    eligible["average_sensitivity_rank"] = eligible[rank_columns].mean(axis=1)

    grid = grid.merge(
        eligible[
            ["cell_id", "robust_top15_hits", "average_sensitivity_rank"]
            + [col for col in eligible.columns if col.startswith("screen_score_coverage_")]
            + rank_columns
        ],
        on="cell_id",
        how="left",
    )

    candidates = eligible.loc[eligible["robust_top15_hits"] >= 2].copy()
    if candidates.empty:
        candidates = eligible.nsmallest(15, "average_sensitivity_rank").copy()

    candidate_metric = candidates.to_crs(CRS_METRIC)
    coords = np.column_stack(
        [
            candidate_metric.geometry.centroid.x,
            candidate_metric.geometry.centroid.y,
        ]
    )

    clusterer = DBSCAN(
        eps=ZONE_CLUSTER_EPS_M,
        min_samples=1,
        metric="euclidean",
    )
    candidates["zone_id"] = clusterer.fit_predict(coords) + 1

    centre_metric = candidates.to_crs(CRS_METRIC).copy()
    centre_metric["centre_x"] = centre_metric.geometry.centroid.x
    centre_metric["centre_y"] = centre_metric.geometry.centroid.y

    zone_rows = []
    for zone_id, group in centre_metric.groupby("zone_id"):
        centre = gpd.GeoSeries(
            gpd.points_from_xy(
                [group["centre_x"].mean()],
                [group["centre_y"].mean()],
            ),
            crs=CRS_METRIC,
        ).to_crs("EPSG:4326").iloc[0]

        zone_rows.append(
            {
                "zone_id": int(zone_id),
                "district": district_mode(group["district"]),
                "candidate_cells": int(len(group)),
                "centre_latitude": float(centre.y),
                "centre_longitude": float(centre.x),
                "max_screen_score": float(group["expansion_screen_score"].max()),
                "mean_screen_score": float(group["expansion_screen_score"].mean()),
                "mean_context_fit_score": float(group["context_fit_score"].mean()),
                "mean_coverage_gap_score": float(group["coverage_gap_score"].mean()),
                "mean_nearest_bravo_km": float(group["nearest_bravo_km"].mean()),
                "mean_competitor_count_1_5km": float(
                    group["competitor_count_1_5km"].mean()
                ),
                "mean_transit_count_1km": float(
                    group["transit_count_1km"].mean()
                ),
                "population_density_per_sq_km": float(
                    group["density_per_sq_km"].median()
                ),
                "robustness_hits": int(group["robust_top15_hits"].sum()),
            }
        )

    zones = pd.DataFrame(zone_rows)
    zones = zones.sort_values(
        ["robustness_hits", "max_screen_score"],
        ascending=[False, False],
    ).reset_index(drop=True)
    zones["screening_rank"] = np.arange(1, len(zones) + 1)

    CELL_CSV.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    grid.drop(columns="geometry").to_csv(CELL_CSV, index=False)
    grid.to_crs("EPSG:4326").to_file(CELL_GEOJSON, driver="GeoJSON")
    zones.to_csv(ZONE_CSV, index=False)

    summary = [
        "# Expansion screening summary",
        "",
        "This is a public-data screening model, not a site-opening recommendation.",
        "",
        "## Validation against the existing network",
        "",
        "The context model uses only external features: district population density, nearby non-Bravo food retail and public transport. Bravo coverage variables are excluded from the validation model.",
        "",
        f"- Population-density-only grouped ROC AUC: **{baseline_auc:.3f}** across {baseline_folds} usable district-held-out folds",
        f"- Full external-context grouped ROC AUC: **{full_auc:.3f}** across {full_folds} usable district-held-out folds",
        "",
        "The grouped split holds out entire districts, which is stricter than randomly splitting neighbouring cells.",
        "",
        "## Screening rule",
        "",
        f"Only cells at least **{MIN_BRAVO_GAP_KM:.1f} km** from the nearest current Bravo are eligible.",
        "The main score is the geometric mean of the Bravo coverage-gap score and the external context-fit score.",
        "Sensitivity is checked by shifting the coverage weight between 40%, 50% and 60%.",
        "",
        f"- Grid cells with district population matched: **{matched} / {len(grid)}**",
        f"- Eligible coverage-gap cells: **{int(grid['eligible_gap'].sum())}**",
        f"- Robust candidate cells used for zone clustering: **{len(candidates)}**",
        f"- Candidate zones after clustering adjacent cells: **{len(zones)}**",
        "",
        "## Highest-ranked screening zones",
        "",
        "| Rank | District | Cells | Centre | Mean nearest Bravo | Density | Other food retailers within 1.5 km | Transit features within 1 km |",
        "| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]

    for row in zones.head(8).itertuples(index=False):
        summary.append(
            "| "
            f"{row.screening_rank} | {row.district} | {row.candidate_cells} | "
            f"{row.centre_latitude:.4f}, {row.centre_longitude:.4f} | "
            f"{row.mean_nearest_bravo_km:.2f} km | "
            f"{row.population_density_per_sq_km:,.0f}/km² | "
            f"{row.mean_competitor_count_1_5km:.1f} | "
            f"{row.mean_transit_count_1km:.1f} |"
        )

    summary += [
        "",
        "## Limits",
        "",
        "The model cannot observe rent, store economics, footfall, road-side visibility, available properties, basket size or cannibalisation between formats.",
        "District population density is also much coarser than the 1 km grid, so the shortlist should be treated as a first screening layer for more detailed research.",
    ]

    SUMMARY_PATH.write_text("\n".join(summary) + "\n", encoding="utf-8")

    bravo = pd.read_csv(BRAVO_PATH).dropna(subset=["latitude", "longitude"])
    map_centre = [
        float(zones["centre_latitude"].median()) if not zones.empty else 40.40,
        float(zones["centre_longitude"].median()) if not zones.empty else 49.87,
    ]
    m = folium.Map(location=map_centre, zoom_start=10, tiles="OpenStreetMap")

    for row in bravo.itertuples(index=False):
        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=2.5,
            color="#355c3a",
            fill=True,
            fill_opacity=0.65,
            tooltip=row.store_name,
        ).add_to(m)

    for row in zones.head(8).itertuples(index=False):
        folium.CircleMarker(
            location=[row.centre_latitude, row.centre_longitude],
            radius=8,
            color="#8c3b2a",
            fill=True,
            fill_opacity=0.85,
            tooltip=(
                f"Screening zone {row.screening_rank}: {row.district} | "
                f"nearest Bravo {row.mean_nearest_bravo_km:.2f} km"
            ),
        ).add_to(m)

    m.save(MAP_PATH)

    # Static portfolio visual: eligible cells are shaded by the final screening
    # score, existing Bravo stores are points, and shortlisted zones are labelled.
    plot_grid = grid.to_crs("EPSG:4326")
    fig, ax = plt.subplots(figsize=(10, 8))
    plot_grid.boundary.plot(ax=ax, linewidth=0.25, alpha=0.25)

    eligible_plot = plot_grid.loc[
        plot_grid["eligible_gap"]
        & plot_grid["expansion_screen_score"].notna()
    ]
    if not eligible_plot.empty:
        eligible_plot.plot(
            ax=ax,
            column="expansion_screen_score",
            cmap="YlOrRd",
            legend=True,
            alpha=0.72,
            edgecolor="white",
            linewidth=0.35,
        )

    bravo_gdf = gpd.GeoDataFrame(
        bravo.copy(),
        geometry=gpd.points_from_xy(bravo.longitude, bravo.latitude),
        crs="EPSG:4326",
    )
    bravo_gdf.plot(ax=ax, markersize=7, color="#315b3c", alpha=0.75)

    for row in zones.head(8).itertuples(index=False):
        ax.scatter(
            row.centre_longitude,
            row.centre_latitude,
            s=85,
            facecolors="none",
            edgecolors="#1f1f1f",
            linewidths=1.4,
        )
        ax.annotate(
            str(row.screening_rank),
            (row.centre_longitude, row.centre_latitude),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_title("Bravo expansion screening: coverage gap + external context")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.tight_layout()
    plt.savefig(STATIC_MAP_PATH, dpi=180)
    plt.close()

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    labels = ["Population density\nonly", "Full external\ncontext"]
    values = [baseline_auc, full_auc]
    ax.bar(labels, values)
    ax.set_ylim(0, 1)
    ax.set_ylabel("District-held-out ROC AUC")
    ax.set_title("Does external context recover existing Bravo areas?")
    for index, value in enumerate(values):
        if not np.isnan(value):
            ax.text(index, value + 0.025, f"{value:.3f}", ha="center")
    plt.tight_layout()
    plt.savefig(VALIDATION_CHART_PATH, dpi=180)
    plt.close()

    print(f"Matched district population to {matched} of {len(grid)} cells.")
    print(
        f"Grouped AUC: density baseline={baseline_auc:.3f}, "
        f"full context={full_auc:.3f}"
    )
    print(f"Eligible gap cells: {int(grid['eligible_gap'].sum())}")
    print(f"Candidate zones: {len(zones)}")
    print(f"Saved {SUMMARY_PATH}")


if __name__ == "__main__":
    main()