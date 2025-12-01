import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

# Load BlueBike stations
df = pd.read_csv("data/Blue_Bike_Stations.csv")


# Convert to GeoDataFrame (Longitude, Latitude → Points)
gdf_stations = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
    crs="EPSG:4326"
)

place_name = "Cambridge, Massachusetts, USA"

# Download OSM landuse polygons
landuse = ox.features_from_place(place_name, tags={"landuse": True})
# Keep only polygons and multipolygons
landuse = landuse[landuse.geometry.type.isin(["Polygon", "MultiPolygon"])]

print(landuse["landuse"].value_counts().head())

# Download amenities
amenity = ox.features_from_place(place_name, tags={"amenity": True})
# keep only relevant geoms
amenity = amenity[amenity.geometry.notna()]

print(amenity["amenity"].value_counts().head())


# Match CRS (needed before spatial join or measuring distances)
gdf_stations = gdf_stations.to_crs(landuse.crs)
# match amenities to stations
amenity = amenity.to_crs(landuse.crs)


# Join stations to landuse polygons
joined = gpd.sjoin(
    gdf_stations,
    landuse[["landuse", "geometry"]],
    how="left",
    predicate="intersects",
    lsuffix="station",
    rsuffix="landuse"
)
# join amenities
joined = gpd.sjoin(
    joined,
    amenity[["amenity", "geometry"]],
    how="left",
    predicate="intersects",
    lsuffix="station2",
    rsuffix="amenity"
)

# Identify stations not inside any polygon
missing = joined[joined["landuse"].isna()].copy()

MAX_DIST = 50  # max distance threshold

# Project both datasets into a metric CRS  
METRIC = "EPSG:26986"

# Project for distance calculation
stations_m = gdf_stations.to_crs(METRIC)
landuse_m = landuse.to_crs(METRIC)
amenity_m = amenity.to_crs(METRIC)
joined_m = joined.to_crs(METRIC)

# --- Missing landuse
missing_land = joined_m[joined_m["landuse"].isna()].copy()
missing_land = missing_land[missing_land.geometry.notna() & (~missing_land.geometry.is_empty)].copy()


print("missing labnd")
print(missing_land)
print("done")

if len(missing_land) > 0:
    missing_land["orig_index"] = missing_land.index
    missing_land = missing_land.drop_duplicates(subset="orig_index")
    orig_idx = missing_land.index

    nearest_idx = []
    dists = []

    print(missing_land.nunique())

    # Compute nearest landuse polygon and distance for each missing station
    for geom in missing_land.geometry:
        dist_series = landuse_m.distance(geom)          # distances to all polygons
        nearest_idx.append(dist_series.idxmin())        # nearest polygon index
        dists.append(dist_series.min())                 # nearest distance
    

    print(len(nearest_idx), len(dists), orig_idx.nunique())

    print("orig", orig_idx)


    # Assign landuse only if within MAX_DIST
    # joined.loc[orig_idx, "landuse"] = [
    #     landuse_m.loc[idx]["landuse"] if dist <= MAX_DIST else None
    #     for idx, dist in zip(nearest_idx, dists)
    # ]

    # Assign landuse only if within MAX_DIST, row by row
    for station_idx, (landuse_idx, dist) in zip(orig_idx, zip(nearest_idx, dists)):
        if landuse_idx is not None and dist <= MAX_DIST:
            joined.at[station_idx, "landuse"] = landuse_m.loc[landuse_idx, "landuse"]
        else:
            joined.at[station_idx, "landuse"] = None


# --- Missing amenity
missing_am = joined_m[joined_m["amenity"].isna()].copy()

if len(missing_am) > 0:
    missing_am["orig_index"] = missing_am.index
    missing_am = missing_am.drop_duplicates(subset="orig_index")
    orig_idx = missing_am.index

    amenity_m_valid = amenity_m[amenity_m.geometry.notna() & (~amenity_m.geometry.is_empty)].copy()
    

    nearest_idx = []
    dists = []

    # Compute nearest amenity polygon and distance for each missing station
    for geom in missing_am.geometry:
        dist_series = amenity_m_valid.distance(geom)
        nearest_idx.append(dist_series.idxmin())
        dists.append(dist_series.min())
        
    for station_idx, (amenity_idx, dist) in zip(orig_idx, zip(nearest_idx, dists)):
        if amenity_idx is not None and dist <= MAX_DIST:
            joined.at[station_idx, "amenity"] = amenity_m.loc[amenity_idx, "amenity"]
        else:
            joined.at[station_idx, "amenity"] = None

# Export
joined.to_csv("bluebike_with_landuseAmenity.csv", index=False)

ale_idx = joined[joined['Name'] == 'Ames St at Main St'].index
for idx in ale_idx:
    print(idx)
    print(joined.at[idx, 'landuse'])
    print(joined.at[idx, 'amenity'])


station_geom = joined_m.loc[joined_m['Name'] == 'Ames St at Main St'].geometry.iloc[0]

# distances to all landuse polygons
dists = landuse_m.distance(station_geom)

# show the closest 5 polygons
closest = dists.nsmallest(5)
print(closest)
print(landuse_m.loc[closest.index, 'landuse'])

# distances to all landuse polygons
dists = amenity_m.distance(station_geom)

# show the closest 5 polygons
closest = dists.nsmallest(5)
print(closest)
print(amenity_m.loc[closest.index, 'landuse'])