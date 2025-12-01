import csv
from collections import defaultdict, Counter
from datetime import datetime

# Load your data - CHANGE THIS FILENAME
def load_data(filename):
    trips = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append(row)
    return trips

data = load_data('202510-bluebikes-tripdata.csv')  # CHANGE THIS!

# Organize by rider
riders = defaultdict(list)
for trip in data:
    riders[trip['ride_id']].append(trip)

print("=" * 80)
print("BIKE SHARE DE-ANONYMIZATION DEMO")
print("Showing how 'anonymous' ride data can reveal individual identities")
print("=" * 80)
print(f"\nTotal riders: {len(riders)}")
print(f"Total trips: {len(data)}")

# Analysis 1: Find repeated routes
print("\n1. REPEATED ROUTE ANALYSIS")
print("-" * 80)

rider_count = 0
for ride_id, trips in riders.items():
    routes = [f"{t['start_station_name']} -> {t['end_station_name']}" for t in trips]
    route_counts = Counter(routes)
    
    # Only show riders with repeated routes
    if len(trips) > 1:
        print(f"\nRider: {ride_id} (Member type: {trips[0]['member_casual']})")
        print(f"Total trips: {len(trips)}")
        print(f"Unique routes: {len(route_counts)}")
        print("Most frequent routes:")
        
        for route, count in route_counts.most_common(3):
            print(f"  • {route}: {count} times ({count/len(trips)*100:.1f}%)")
        
        rider_count += 1
        if rider_count >= 10:  # Show first 10 riders with multiple trips
            break

# Analysis 2: Find commuter patterns
print("\n\n2. COMMUTER PATTERN DETECTION")
print("-" * 80)
print("Identifying likely commuters (weekday morning/evening patterns)\n")

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
        
        print(f"Rider: {ride_id}")
        print(f"  Commute ratio: {commute_ratio*100:.1f}%")
        print(f"  Morning commutes: {morning_commutes}")
        print(f"  Evening commutes: {evening_commutes}")
        print(f"  Member type: {trips[0]['member_casual']}")
        
        if commute_routes:
            most_common = Counter(commute_routes).most_common(1)[0]
            print(f"  Typical route: {most_common[0]} ({most_common[1]} times)")
            print(f"  ⚠️  This person likely lives near '{most_common[0].split(' -> ')[0]}'")
            print(f"     and works near '{most_common[0].split(' -> ')[1]}'")
        print()
        
        commuter_count += 1
        if commuter_count >= 10:
            break

# Analysis 3: Unique identifying patterns
print("\n3. UNIQUENESS ANALYSIS")
print("-" * 80)
print("Routes that could uniquely identify riders:\n")

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

print(f"Total unique routes: {len(route_frequency)}")
print(f"Routes taken ≤3 times: {len(rare_routes)} ({len(rare_routes)/len(route_frequency)*100:.1f}%)")

print("\nExamples of highly identifying routes:")
for route, count in sorted(rare_routes.items(), key=lambda x: x[1])[:15]:
    rider_ids = list(route_to_riders[route])
    print(f"  • {route}")
    print(f"    Taken {count} time(s) by: {', '.join(rider_ids[:3])}")
    print(f"    ⚠️  HIGHLY IDENTIFYING - can link to specific person!\n")

# Analysis 4: Cross-reference attack
print("\n4. CROSS-REFERENCE ATTACK SIMULATION")
print("-" * 80)
print("If we know 2 facts about someone, we can find them:\n")

# Example: Find someone who:
# 1. Takes morning trips from Park Plaza area
# 2. Is a member (not casual)
print("Target profile: Member who commutes FROM 'Park Plaza' area in mornings\n")

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
    print(f"\n  Rider: {ride_id}")
    print(f"  Total trips: {len(rider_trips)}")
    print(f"  Example morning trip: {trip['start_station_name']} -> {trip['end_station_name']}")
    print(f"  ⚠️  With just 2 pieces of info, we narrowed down to {len(matches)} people!")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("- Repeated routes reveal home/work locations")
print("- Timing patterns identify commuters vs casual users")
print("- Rare routes are like fingerprints")
print("- Just 2-3 facts can uniquely identify 'anonymous' riders")
print("- Privacy in mobility data is largely an illusion!")
print("=" * 80)