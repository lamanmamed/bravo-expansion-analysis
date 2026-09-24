# Methodology

## Objective

The project ranks areas for further expansion research. It does not make a final store-opening decision.

A useful candidate area has to satisfy two separate questions:

1. **Coverage gap:** is Bravo currently underrepresented nearby?
2. **Location context:** does the area resemble places where Bravo already tends to operate, based on external demand and accessibility signals?

Keeping those questions separate prevents every area far from an existing store from being treated as attractive.

## Geographic unit

The analysis uses a 1 km square grid clipped to the central Baku study polygon returned by the OpenStreetMap/Nominatim place search used in the data pipeline.

Each cell receives features calculated from its centre. The grid is small enough to show local differences while remaining interpretable for a screening exercise.

This polygon is **not the full Baku administrative city**. Baku City Executive Power describes the full administrative territory as roughly 2,200 km² and 12 districts. The current project should therefore be read as a central-Baku pilot rather than a complete citywide expansion search.

## Coverage features

The first feature pipeline calculates:

| Feature | Interpretation |
| --- | --- |
| `nearest_bravo_km` | Distance to the nearest existing Bravo |
| `bravo_count_1_5km` | Existing Bravo concentration nearby |
| `nearest_competitor_km` | Distance to another food retailer |
| `competitor_count_1_5km` | Local supermarket/convenience-store concentration |
| `nearest_transit_km` | Distance to the nearest mapped public-transport feature |
| `transit_count_1km` | Public-transport availability nearby |

The initial coverage-gap baseline uses only Bravo coverage:

```text
0.7 * normalised distance to nearest Bravo
+ 0.3 * inverse normalised Bravo count within 1.5 km
```

This score describes network gaps. It is not an expansion recommendation.

## Population

The State Statistical Committee workbook provides population and density as of **01.01.2026** for Baku and its 12 districts.

Each 1 km grid-cell centre is assigned to a Baku district using rate-limited OpenStreetMap/Nominatim reverse geocoding. The district label is then joined to the official population table.

District density is deliberately treated as a coarse demand signal. It does not imply that population is evenly distributed inside the district.

## External context model

To test whether the public data contains a useful location signal, the project defines an existing-network label:

```text
1 if a grid-cell centre is within 1 km of a current Bravo
0 otherwise
```

The model is a class-balanced logistic regression using only external features:

- log population density
- nearby non-Bravo food-retail count
- distance to the nearest non-Bravo food retailer
- nearby public-transport count
- distance to the nearest public-transport feature

Bravo distance and Bravo store count are excluded from this model. Using them would leak the answer into the validation.

A population-density-only model is kept as the baseline.

## Validation

Validation uses **GroupKFold by district** rather than a random cell split.

That means whole districts are held out together. Nearby cells from the same district cannot appear on both sides of a fold, which makes the test harder and reduces local spatial leakage.

The main validation metric is ROC AUC. The goal is not to prove that public data explains store profitability. It tests a narrower question:

> Do demand, retail-context and accessibility signals help distinguish the kinds of areas where Bravo currently operates?

## Expansion screen

A cell becomes eligible for expansion screening only when it is at least **1.5 km** from the nearest current Bravo.

The external model produces a context-fit score for every matched cell. The main expansion screen is the geometric mean of:

- coverage-gap score
- external context-fit score

A geometric mean is used because it penalises a cell when either component is very weak. A remote cell with poor demand context should not rank highly simply because it is far from Bravo.

## Sensitivity

The coverage contribution is varied between 40%, 50% and 60%.

Cells that remain in the top 15 under at least two settings are treated as robust screening candidates. Adjacent robust cells are then grouped with DBSCAN into broader candidate zones so the output does not present several neighbouring 1 km squares as separate business opportunities.

## Decision output

The final shortlist reports:

- district
- approximate zone centre
- distance to existing Bravo coverage
- population density
- nearby non-Bravo food retail
- public-transport context
- score robustness

The shortlist is a first screening layer only. A real store decision would still require internal information such as rent, property availability, sales, basket size, margins, footfall, road visibility and cannibalisation between formats.