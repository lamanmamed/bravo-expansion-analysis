# Executive summary

## Question

Where in Baku does Bravo appear relatively under-covered while public demand and accessibility signals still look commercially interesting?

## What the existing network shows

Bravo is already densely distributed across much of the current Baku network.

- 144 official locations were collected
- 143 have usable coordinates
- 129 fall inside the broad first-pass Baku study extent
- 51.9% of those stores are Express format
- median distance to the nearest other Bravo is 0.53 km
- 83.7% have another Bravo within 1 km

This means distance from the nearest Bravo is not enough to identify an attractive expansion area.

## What improves the screen

A logistic model using only external context was tested against the existing Bravo network.

The model uses:

- official 2026 district population density
- non-Bravo food-retail concentration
- distance to other food retail
- public-transport availability
- distance to public transport

Validation holds out whole districts.

| Model | District-held-out ROC AUC |
| --- | ---: |
| Population density only | 0.659 |
| Full external context | 0.899 |

The improvement suggests that population alone misses useful information about the kinds of places where Bravo currently operates.

## Current screening zones

After requiring at least 1.5 km distance from an existing Bravo, testing score sensitivity and clustering neighbouring cells, four zones remain.

| Rank | District | Mean distance to Bravo | Population density | Nearby food retailers | Transit signal |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Surakhani | 1.82 km | 1,745/km² | 41.1 | Low |
| 2 | Khatai | 1.69 km | 9,260/km² | 13.5 | Low |
| 3 | Sabail | 1.92 km | 3,403/km² | 25.0 | Very low |
| 4 | Surakhani | 2.05 km | 1,745/km² | 31.0 | Very low |

## Business interpretation

The strongest Surakhani cluster combines a real Bravo coverage gap with substantial surrounding food-retail activity. That makes it worth investigating, but weak mapped transit means the result should not be treated as a ready-made store recommendation.

Khatai is different. It has much higher district population density and a smaller surrounding food-retail cluster, but the average Bravo gap is also smaller.

The useful output is therefore not "open in Surakhani". It is:

> Prioritise these four zones for a second-stage commercial review, then compare property availability, rent, footfall, road access and expected cannibalisation before choosing any site.

## Data needed for a real decision

The public-data screen would become much stronger with:

- store-level revenue and margins
- basket size and customer catchments
- rent and available properties
- pedestrian and vehicle footfall
- parking and road visibility
- planned store openings
- format-level cannibalisation
- delivery and logistics constraints

Those variables are intentionally not inferred from public proxies.