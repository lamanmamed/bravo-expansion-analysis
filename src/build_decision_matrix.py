from __future__ import annotations

from pathlib import Path

import pandas as pd


ZONES_PATH = Path("data/processed/candidate_zones.csv")
PROFILES_PATH = Path("data/processed/candidate_zone_profiles.csv")
OUTPUT_PATH = Path("outputs/decision_matrix.md")


def band(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 50:
        return "above median"
    if value >= 25:
        return "below median"
    return "low"


def strength_text(row) -> str:
    signals = []
    if row.bravo_gap_percentile >= 50:
        signals.append(f"{band(row.bravo_gap_percentile)} Bravo coverage gap")
    if row.population_density_percentile >= 50:
        signals.append(f"{band(row.population_density_percentile)} population density")
    if row.food_retail_activity_percentile >= 50:
        signals.append(f"{band(row.food_retail_activity_percentile)} surrounding food-retail activity")
    if row.mean_transit_count_1km >= 1:
        signals.append(
            f"{band(row.transit_percentile)} mapped transit context "
            f"({row.mean_transit_count_1km:.1f} features within 1 km)"
        )

    if not signals:
        return "No single public-data signal is above the eligible-cell median"
    return "; ".join(signals)


def caution_text(row) -> str:
    cautions = []
    if row.population_density_percentile < 25:
        cautions.append("low district-density signal")
    if row.mean_transit_count_1km < 1:
        cautions.append(
            f"sparse mapped transit ({row.mean_transit_count_1km:.1f} features within 1 km)"
        )
    if row.food_retail_activity_percentile >= 75:
        cautions.append("high food-retail activity may also mean stronger competition")
    if row.bravo_gap_percentile < 50:
        cautions.append("coverage gap is modest relative to other eligible cells")

    if not cautions:
        return "No obvious weakness in the current public-data screen"
    return "; ".join(cautions)


def next_check(row) -> str:
    if row.food_retail_activity_percentile >= 75:
        return "Property economics, competitor mix and footfall"
    if row.population_density_percentile >= 75:
        return "Property availability, road access and cannibalisation"
    if row.mean_transit_count_1km < 1:
        return "Road access, parking and actual pedestrian/vehicle footfall"
    return "Rent, property availability and local footfall"


def main() -> None:
    # The diagnostics workflow creates the zone-profile input used here.
    zones = pd.read_csv(ZONES_PATH)
    profiles = pd.read_csv(PROFILES_PATH)

    frame = zones.merge(
        profiles,
        on=["screening_rank", "district"],
        how="left",
        validate="one_to_one",
    ).sort_values("screening_rank")

    lines = [
        "# Candidate zone decision matrix",
        "",
        "This translates the model output into a business-review format. It does not convert the shortlist into site recommendations.",
        "",
        "| Rank | District | Evidence in favour | Main caution | What to check next |",
        "| ---: | --- | --- | --- | --- |",
    ]

    for row in frame.itertuples(index=False):
        lines.append(
            f"| {int(row.screening_rank)} | {row.district} | "
            f"{strength_text(row)} | {caution_text(row)} | {next_check(row)} |"
        )

    lines += [
        "",
        "## How to use this",
        "",
        "The model should narrow a large city search into a small set of areas worth commercial investigation.",
        "A second-stage review should add property-level information before any location is treated as a serious site candidate.",
        "",
        "The most important missing variables are rent, property availability, footfall, road visibility, parking, store economics and expected cannibalisation.",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()