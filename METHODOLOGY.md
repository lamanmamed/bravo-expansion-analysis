# Methodology

## Objective

The project ranks areas for further expansion research. It does not make a final store-opening decision.

A useful candidate area should satisfy two separate questions:

1. **Coverage gap:** is Bravo currently underrepresented nearby?
2. **Location attractiveness:** is there enough evidence of local demand and accessibility to justify deeper site research?

Keeping those questions separate avoids treating every area far from a Bravo store as an attractive expansion opportunity.

## Geographic unit

The first model uses a 1 km square grid clipped to the Baku boundary.

Each grid cell receives features calculated from its centre. The grid is small enough to show local differences but large enough to remain interpretable for a city-level screening exercise.

## Phase 1: coverage features

The first feature pipeline calculates:

| Feature | Interpretation |
| --- | --- |
| `nearest_bravo_km` | Distance to the nearest existing Bravo |
| `bravo_count_1_5km` | Existing Bravo concentration nearby |
| `nearest_competitor_km` | Distance to another food retailer |
| `competitor_count_1_5km` | Local supermarket/convenience-store concentration |
| `nearest_transit_km` | Distance to the nearest mapped public-transport feature |
| `transit_count_1km` | Public-transport availability nearby |

The initial `coverage_gap_score` intentionally uses only Bravo coverage:

```text
0.7 * normalised distance to nearest Bravo
+ 0.3 * inverse normalised Bravo count within 1.5 km
```

This is a baseline, not the final expansion score.

## Phase 2: demand and accessibility

The next stage adds:

- official population and density data from the State Statistical Committee
- residential-area intensity
- competitor concentration
- public-transport accessibility

Population is treated as a demand signal. Competitor density is not automatically assumed to be negative: a dense competitor cluster can indicate both stronger demand and stronger competition.

## Validation

The final model should be tested against existing Bravo locations.

The validation design will compare at least two approaches:

1. a simple baseline using population or residential intensity
2. a fuller model using demand, accessibility and retail-context features

Bravo-derived coverage features will not be used to prove that existing Bravo locations are attractive, because that would leak the answer into the validation.

The evaluation will report:
- how highly existing Bravo areas are ranked
- precision among the highest-ranked cells
- sensitivity to feature weights
- differences between central and peripheral Baku

## Decision output

The final result should identify a small shortlist of areas and show:

- the features driving each area's score
- nearby Bravo coverage
- nearby competitors
- accessibility
- population/demand signal
- limitations and what additional internal data would be needed before a real site decision

Useful internal data would include rent, sales, basket size, delivery catchments, margins, footfall and property availability.
