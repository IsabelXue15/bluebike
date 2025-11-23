import requests

BASE = "https://api-v3.mbta.com"
API_KEY = "44bbc7e0590644728d692718a502f99d"   # set to None to try without key (low rate)

headers = {}
if API_KEY:
    headers['x-api-key'] = API_KEY

# Example: fetch Red Line stops
resp = requests.get(f"{BASE}/stops", params={"filter[route]":"Red"}, headers=headers)
resp.raise_for_status()
data = resp.json()
for s in data.get("data", [])[:10]:
    print(s["id"], s["attributes"]["name"])
