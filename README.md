# Bravo Expansion Analysis

A location analytics project that uses public data to study Bravo's current store network in Baku and identify areas that may deserve closer investigation for future expansion.

## Business question

**Where in Baku are there populated, accessible areas with relatively weak Bravo coverage and enough room to justify more detailed site research?**

This project is a decision-support analysis. It does not claim to know Bravo's internal sales, rents, margins, customer data or property pipeline.

## Planned analysis

1. Collect Bravo's current store locations, formats, addresses and opening hours from Bravo's official store page.
2. Map the existing network and separate Hiper, Super, Market and Express formats.
3. Add public context data for nearby supermarkets and public transport.
4. Add a demand signal using population or residential-density data.
5. Divide Baku into comparable geographic cells.
6. Calculate features such as:
   - distance to the nearest Bravo
   - number of Bravo stores within a local radius
   - competitor density
   - distance to public transport
   - population or residential intensity
7. Build a transparent expansion score and compare it with simpler baselines.
8. Hold out a subset of existing Bravo locations to test whether the scoring method ranks their areas highly.
9. Produce a map of candidate areas and a short business summary of the strongest signals and limitations.

## Current status

The first stage is the data pipeline. The repository now includes a collector for Bravo's official store list and a separate OpenStreetMap context collector.

The Bravo collector extracts the coordinates already used by the official store page's Google Maps links. This avoids guessing coordinates from free-text addresses.

## Repository structure

```text
.
├── data/
│   ├── raw/
│   └── processed/
├── outputs/
├── src/
│   ├── collect_bravo_stores.py
│   └── collect_osm_context.py
├── DATA_SOURCES.md
├── requirements.txt
└── README.md
```

## Run locally

Create an environment and install the dependencies:

```bash
pip install -r requirements.txt
```

Collect Bravo stores:

```bash
python src/collect_bravo_stores.py
```

Collect OpenStreetMap supermarket and transit context:

```bash
python src/collect_osm_context.py
```

The next stage will build the geographic analysis grid and store-coverage features.

## Output of the first collector

`data/raw/bravo_stores.csv` contains:

- store name
- store format
- address
- opening hours
- latitude and longitude
- whether the coordinates fall inside the initial Baku study bounding box
- source and Google Maps links
- collection timestamp

## Data quality

Public location data can be incomplete or inconsistent. Before scoring expansion areas, the project will:

- compare the scraped store count with Bravo's official page
- inspect duplicate or missing coordinates
- check outlier locations manually
- keep source URLs for traceability
- document any manual corrections

## Stack

**Python · pandas · GeoPandas · OSMnx · scikit-learn · DuckDB · Matplotlib · Folium**
