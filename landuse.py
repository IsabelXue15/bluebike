import osmnx as ox
import geopandas as gpd

# Define area
place_name = "Cambridge, Massachusetts, USA"

# Get all amenities (cafes, offices, schools, etc.)
gdf = ox.features_from_place(place_name, tags={"amenity": True})
print(gdf.head())

landuse = ox.features_from_place(place_name, tags={"landuse": True})
landuse["landuse"].value_counts().head(10)

print(landuse)


df_export = gdf.copy()

df_export["geometry"] = df_export["geometry"].apply(lambda x: x.wkt)

df_export.to_csv("osm_amenities_boston.csv", index=False)
