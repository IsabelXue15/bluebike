import csv
from collections import defaultdict, Counter
from datetime import datetime

# Load data
def load_data(filename):
    trips = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append(row)
    return trips

data = load_data('202510-bluebikes-tripdata.csv') 

# Organize by rider
riders = defaultdict(list)
for trip in data:
    riders[trip['ride_id']].append(trip)

# Analysis 1: Find repeated routes
rider_count = 0
for ride_id, trips in riders.items():
    routes = [f"{t['start_station_name']} -> {t['end_station_name']}" for t in trips]
    route_counts = Counter(routes)
    
    # Only show riders with repeated routes
    if len(trips) > 1:
        for route, count in route_counts.most_common(3):
            print(f"  • {route}: {count} times ({count/len(trips)*100:.1f}%)")
        
        rider_count += 1
        if rider_count >= 10:  # Show first 10 riders with multiple trips
            break

# Analysis 2: Find commuter patterns
commuter_count = 0
for ride_id, trips in riders.items():
    morning_commutes = 0
    evening_commutes = 0
    commute_routes = []
    
    for trip in trips:
        try:
            dt = datetime.strptime(trip['started_at'], '%Y-%m-%d %H:%M:%S.%f')
            hour = dt.hour
            day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
            
            # Weekday morning commute
            if 6 <= hour <= 9 and day_of_week < 5:
                morning_commutes += 1
                commute_routes.append(f"{trip['start_station_name']} -> {trip['end_station_name']}")
            # Weekday evening commute
            elif 16 <= hour <= 19 and day_of_week < 5:
                evening_commutes += 1
                commute_routes.append(f"{trip['start_station_name']} -> {trip['end_station_name']}")
        except:
            continue
    
    total_commutes = morning_commutes + evening_commutes
    if total_commutes >= 3:  # At least 3 commute trips
        commute_ratio = total_commutes / len(trips)
        
        if commute_routes:
            most_common = Counter(commute_routes).most_common(1)[0]
        
        commuter_count += 1
        if commuter_count >= 10:
            break

# Analysis 3: Unique identifying patterns
# Count all routes
all_routes = []
route_to_riders = defaultdict(set)
for ride_id, trips in riders.items():
    for trip in trips:
        route = f"{trip['start_station_name']} -> {trip['end_station_name']}"
        all_routes.append(route)
        route_to_riders[route].add(ride_id)

route_frequency = Counter(all_routes)
rare_routes = {route: count for route, count in route_frequency.items() if count <= 3}

for route, count in sorted(rare_routes.items(), key=lambda x: x[1])[:15]:
    rider_ids = list(route_to_riders[route])

# Analysis 4: Cross-reference attack

# Example: Find someone who:
# 1. Takes morning trips from Park Plaza area
# 2. Is a member (not casual)

matches = []
for ride_id, trips in riders.items():
    if trips[0]['member_casual'] == 'member':
        for trip in trips:
            try:
                dt = datetime.strptime(trip['started_at'], '%Y-%m-%d %H:%M:%S.%f')
                if 6 <= dt.hour <= 9 and dt.weekday() < 5:
                    if 'Park Plaza' in trip['start_station_name']:
                        matches.append((ride_id, trip))
                        break
            except:
                continue

print(f"Found {len(matches)} potential matches:")
for ride_id, trip in matches[:5]:
    rider_trips = riders[ride_id]