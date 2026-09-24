from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


GRID_PATH = Path("data/processed/coverage_grid.geojson")
DISTRICT_ASSIGNMENTS_PATH = Path("data/processed/grid_district_assignments.csv")
POPULATION_PATH = Path("data/processed/baku_district_population_2026.csv")
ZONES_PATH = Path("data/processed/candidate_zones.csv")
SCREEN_CELLS_PATH = Path("data/processed/expansion_screen_cells.csv")

VALIDATION_FOLDS_PATH = Path("data/processed/model_validation_by_fold.csv")
COEFFICIENTS_PATH = Path("data/processed/context_model_coefficients.csv")
ZONE_PROFILES_PATH = Path("data/processed/candidate_zone_profiles.csv")
COEFFICIENT_CHART_PATH = Path("outputs/context_model_coefficients.png")
ZONE_PROFILES_MD_PATH = Path("outputs/candidate_zone_profiles.md")

MODEL_FEATURES = [
    "log_population_density",
    "log_competitor_count",
    "nearest_competitor_km_capped",
    "log_transit_count",
    "nearest_transit_km_capped",
]

FEATURE_LABELS = {
    "log_population_density": "Population density",
    "log_competitor_count": "Nearby food retail",
    "nearest_competitor_km_capped": "Distance to food retail",
    "log_transit_count": "Nearby public transport",
    "nearest_transit_km_capped": "Distance to public transport",
}


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


def prepare_grid() -> pd.DataFrame:
    grid = gpd.read_file(GRID_PATH)
    assignments = pd.read_csv(DISTRICT_ASSIGNMENTS_PATH)
    population = pd.read_csv(POPULATION_PATH)
    population = population.loc[population["district"] != "Baku"].copy()

    grid = grid.merge(
        assignments[["cell_id", "district"]],
        on="cell_id",
        how="left",
    )
    grid = grid.merge(
        population[["district", "density_per_sq_km"]],
        on="district",
        how="left",
    )

    grid["has_bravo_1km"] = (
        pd.to_numeric(grid["nearest_bravo_km"], errors="coerce") <= 1.0
    ).astype(int)

    grid["log_population_density"] = np.log1p(
        pd.to_numeric(grid["density_per_sq_km"], errors="coerce")
    )
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
    return grid


def grouped_validation(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.dropna(
        subset=MODEL_FEATURES + ["district", "has_bravo_1km"]
    ).copy()

    groups = work["district"].astype(str)
    splitter = GroupKFold(n_splits=min(5, groups.nunique()))
    rows = []

    X = work[MODEL_FEATURES]
    y = work["has_bravo_1km"].astype(int)

    for fold, (train_index, test_index) in enumerate(
        splitter.split(X, y, groups),
        start=1,
    ):
        y_train = y.iloc[train_index]
        y_test = y.iloc[test_index]

        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue

        model = build_model()
        model.fit(X.iloc[train_index], y_train)
        probability = model.predict_proba(X.iloc[test_index])[:, 1]

        rows.append(
            {
                "fold": fold,
                "held_out_districts": ", ".join(
                    sorted(work.iloc[test_index]["district"].astype(str).unique())
                ),
                "roc_auc": roc_auc_score(y_test, probability),
                "test_cells": len(test_index),
                "positive_cells": int(y_test.sum()),
                "negative_cells": int((1 - y_test).sum()),
            }
        )

    return pd.DataFrame(rows)


def fit_coefficients(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.dropna(
        subset=MODEL_FEATURES + ["has_bravo_1km"]
    ).copy()

    model = build_model()
    model.fit(work[MODEL_FEATURES], work["has_bravo_1km"].astype(int))

    coefficients = model.named_steps["model"].coef_[0]
    return pd.DataFrame(
        {
            "feature": MODEL_FEATURES,
            "label": [FEATURE_LABELS[f] for f in MODEL_FEATURES],
            "standardised_coefficient": coefficients,
        }
    ).sort_values("standardised_coefficient", ascending=False)


def percentile(reference: pd.Series, value: float) -> float:
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    if ref.empty or pd.isna(value):
        return float("nan")

    # Mid-rank percentile: ties receive half weight. This matters for sparse
    # count features such as transit, where many eligible cells are exactly 0.
    below = (ref < value).sum()
    equal = np.isclose(ref.to_numpy(dtype=float), float(value)).sum()
    return float((below + 0.5 * equal) / len(ref) * 100)


def build_zone_profiles() -> pd.DataFrame:
    zones = pd.read_csv(ZONES_PATH)
    cells = pd.read_csv(SCREEN_CELLS_PATH)

    eligible = cells.loc[
        cells["eligible_gap"].astype(str).str.lower().eq("true")
    ].copy()

    rows = []
    for zone in zones.sort_values("screening_rank").itertuples(index=False):
        # Compare each zone's actual aggregated values with the eligible-cell
        # distribution. This keeps the profile consistent with candidate_zones.csv.
        gap = float(zone.mean_nearest_bravo_km)
        density = float(zone.population_density_per_sq_km)
        retail = float(zone.mean_competitor_count_1_5km)
        transit = float(zone.mean_transit_count_1km)

        rows.append(
            {
                "screening_rank": int(zone.screening_rank),
                "district": zone.district,
                "candidate_cells": int(zone.candidate_cells),
                "mean_nearest_bravo_km": gap,
                "population_density_per_sq_km": density,
                "mean_competitor_count_1_5km": retail,
                "mean_transit_count_1km": transit,
                "bravo_gap_percentile": percentile(
                    eligible["nearest_bravo_km"], gap
                ),
                "population_density_percentile": percentile(
                    eligible["density_per_sq_km"], density
                ),
                "food_retail_activity_percentile": percentile(
                    eligible["competitor_count_1_5km"], retail
                ),
                "transit_percentile": percentile(
                    eligible["transit_count_1km"], transit
                ),
            }
        )

    return pd.DataFrame(rows)


def write_zone_profiles(frame: pd.DataFrame) -> None:
    lines = [
        "# Candidate zone profiles",
        "",
        "Percentiles compare each shortlisted zone's actual aggregated values with cells that passed the 1.5 km Bravo coverage-gap threshold.",
        "They are relative public-data signals, not estimates of profitability. Absolute values still matter, especially for sparse OpenStreetMap transit data.",
        "",
        "| Rank | District | Bravo gap pct | Population density pct | Food-retail activity pct | Transit pct |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]

    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.screening_rank} | {row.district} | "
            f"{row.bravo_gap_percentile:.0f} | "
            f"{row.population_density_percentile:.0f} | "
            f"{row.food_retail_activity_percentile:.0f} | "
            f"{row.transit_percentile:.0f} |"
        )

    lines += [
        "",
        "A high food-retail percentile can mean a proven shopping destination, but it can also mean stronger competition.",
        "OpenStreetMap transit coverage is incomplete, so the transit percentile should be treated as a context signal rather than a complete accessibility measure.",
    ]

    ZONE_PROFILES_MD_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def plot_coefficients(frame: pd.DataFrame) -> None:
    plot_frame = frame.sort_values("standardised_coefficient")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.barh(
        plot_frame["label"],
        plot_frame["standardised_coefficient"],
    )
    ax.axvline(0, linewidth=0.8, color="black")
    ax.set_xlabel("Standardised logistic-regression coefficient")
    ax.set_title("External signals associated with existing Bravo coverage")
    plt.tight_layout()
    plt.savefig(COEFFICIENT_CHART_PATH, dpi=180)
    plt.close()


def main() -> None:
    grid = prepare_grid()

    folds = grouped_validation(grid)
    coefficients = fit_coefficients(grid)
    profiles = build_zone_profiles()

    VALIDATION_FOLDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COEFFICIENT_CHART_PATH.parent.mkdir(parents=True, exist_ok=True)

    folds.to_csv(VALIDATION_FOLDS_PATH, index=False)
    coefficients.to_csv(COEFFICIENTS_PATH, index=False)
    profiles.to_csv(ZONE_PROFILES_PATH, index=False)

    write_zone_profiles(profiles)
    plot_coefficients(coefficients)

    print("Validation folds:")
    print(folds.to_string(index=False))
    print("\nStandardised coefficients:")
    print(coefficients.to_string(index=False))
    print("\nCandidate zone profiles:")
    print(profiles.to_string(index=False))


if __name__ == "__main__":
    main()