import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

# Load data
df = pd.read_csv("deanonymization_results.csv")
df2 = pd.read_csv("bluebike_with_landuseAmenity.csv")

df[["start_station", "end_station"]] = df["Outbound_Route"].str.split(" -> ", n=1, expand=True)

# Rename df2 columns so they will merge cleanly
df2 = df2.rename(columns={
    "Name": "start_station",
    "landuse": "start_landuse",
    "amenity": "start_amenity"
})

# Merge to add start station tags
df = df.merge(
    df2[["start_station", "start_landuse", "start_amenity"]],
    on="start_station",
    how="left"
)

# Prepare df2 again for end station merge
df2_end = df2.rename(columns={
    "start_station": "end_station",
    "start_landuse": "end_landuse",
    "start_amenity": "end_amenity"
})

# Merge to add end station tags
df = df.merge(
    df2_end[["end_station", "end_landuse", "end_amenity"]],
    on="end_station",
    how="left"
)

# Save if desired
df.to_csv("deanonymization_tagged.csv", index=False)
