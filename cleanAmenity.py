import pandas as pd

df = pd.read_csv("bluebike_with_landuseAmenity.csv")

dupes = df[df.duplicated(subset="Number", keep=False)]

# group by 'Number' and concatenate amenities for duplicates
dfCleaned = df.groupby('Number', as_index=False).agg({
    'amenity': lambda x: ', '.join(x.dropna().unique()),
    **{col: 'first' for col in df.columns if col not in ['Number', 'amenity']}
})

print(dfCleaned.head())

dupes = dfCleaned[dfCleaned.duplicated(subset="Number", keep=False)]

dfCleaned.to_csv("bluebike_with_landuseAmenityCleaned.csv", index=False)


