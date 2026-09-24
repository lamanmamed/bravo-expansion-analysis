# Expansion screening summary

This is a public-data screening model, not a site-opening recommendation.

## Validation against the existing network

The context model uses only external features: district population density, nearby non-Bravo food retail and public transport. Bravo coverage variables are excluded from the validation model.

- Population-density-only grouped ROC AUC: **0.659** across 5 usable district-held-out folds
- Full external-context grouped ROC AUC: **0.899** across 5 usable district-held-out folds

The grouped split holds out entire districts, which is stricter than randomly splitting neighbouring cells.

## Screening rule

Only cells at least **1.5 km** from the nearest current Bravo are eligible.
The main score is the geometric mean of the Bravo coverage-gap score and the external context-fit score.
Sensitivity is checked by shifting the coverage weight between 40%, 50% and 60%.

- Grid cells with district population matched: **167 / 167**
- Eligible coverage-gap cells: **47**
- Robust candidate cells used for zone clustering: **15**
- Candidate zones after clustering adjacent cells: **4**

## Highest-ranked screening zones

| Rank | District | Cells | Centre | Mean nearest Bravo | Density | Competitors within 1.5 km | Transit features within 1 km |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Surakhani | 8 | 40.3592, 49.9798 | 1.82 km | 1,745/km² | 41.1 | 0.2 |
| 2 | Khatai | 4 | 40.3868, 49.9190 | 1.69 km | 9,260/km² | 13.5 | 0.2 |
| 3 | Sabail | 2 | 40.3383, 49.7991 | 1.92 km | 3,403/km² | 25.0 | 0.0 |
| 4 | Surakhani | 1 | 40.4076, 49.9806 | 2.05 km | 1,745/km² | 31.0 | 0.0 |

## Limits

The model cannot observe rent, store economics, footfall, road-side visibility, available properties, basket size or cannibalisation between formats.
District population density is also much coarser than the 1 km grid, so the shortlist should be treated as a first screening layer for more detailed research.
