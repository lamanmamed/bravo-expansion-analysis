from __future__ import annotations

from pathlib import Path

import folium
import pandas as pd


INPUT_PATH = Path("data/raw/bravo_stores.csv")
OUTPUT_PATH = Path("outputs/bravo_network_map.html")

FORMAT_COLORS = {
    "Hiper": "darkred",
    "Super": "red",
    "Market": "orange",
    "Express": "blue",
}


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} does not exist. Run src/collect_bravo_stores.py first."
        )

    stores = pd.read_csv(INPUT_PATH)
    stores = stores.dropna(subset=["latitude", "longitude"]).copy()

    baku = stores[stores["in_baku_study_bbox"].astype(str).str.lower().eq("true")].copy()
    if baku.empty:
        raise RuntimeError("No stores fall inside the initial Baku study extent.")

    centre = [baku["latitude"].median(), baku["longitude"].median()]
    network_map = folium.Map(location=centre, zoom_start=11, tiles="OpenStreetMap")

    for row in baku.itertuples(index=False):
        store_format = row.store_format if pd.notna(row.store_format) else "Unknown"
        colour = FORMAT_COLORS.get(store_format, "gray")

        popup = folium.Popup(
            (
                f"<strong>{row.store_name}</strong><br>"
                f"Format: {store_format}<br>"
                f"Address: {row.address if pd.notna(row.address) else 'Not parsed'}<br>"
                f"Hours: {row.opening_hours if pd.notna(row.opening_hours) else 'Not parsed'}"
            ),
            max_width=340,
        )

        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=5 if store_format == "Express" else 7,
            color=colour,
            fill=True,
            fill_opacity=0.8,
            weight=1,
            popup=popup,
            tooltip=f"{row.store_name} ({store_format})",
        ).add_to(network_map)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    network_map.save(OUTPUT_PATH)

    print(f"Mapped {len(baku)} Bravo stores.")
    print(f"Saved interactive map to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()