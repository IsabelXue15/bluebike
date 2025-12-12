import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

# load data
df = pd.read_csv("deanonymization_results.csv")
df2 = pd.read_csv("bluebike_with_landuseAmenity.csv")

df[["start_station", "end_station"]] = df["Outbound_Route"].str.split(" -> ", n=1, expand=True)

# rename columns so will merge
df2 = df2.rename(columns={
    "Name": "start_station",
    "landuse": "start_landuse",
    "amenity": "start_amenity"
})

# merge amd add start station tags
df = df.merge(
    df2[["start_station", "start_landuse", "start_amenity"]],
    on="start_station",
    how="left"
)

# prepare df2 for end station merge
df2_end = df2.rename(columns={
    "start_station": "end_station",
    "start_landuse": "end_landuse",
    "start_amenity": "end_amenity"
})

# merge to add end station tags
df = df.merge(
    df2_end[["end_station", "end_landuse", "end_amenity"]],
    on="end_station",
    how="left"
)

# export
df.to_csv("deanonymization_tagged.csv", index=False)
