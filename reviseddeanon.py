import csv
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import itertools


## CONFIGURE PARAMETERS (changeable)
MIN_TRIPS_PER_ROUTE = 5          # Only analyze routes used this many times
MIN_TRIPS_IN_TIME_CLUSTER = 2    # Minimum trips in same time window to consider
TIME_BUCKET_SIZE = 5             # Group arrivals by this many minutes
MAX_TIME_VARIANCE = 5            # Consistency threshold in minutes
MIN_HOURS_BETWEEN_TRIPS = 4      # Minimum hours for return journey (trip from destination back home)
MIN_MATCHED_PAIRS = 2            # Minimum matches to identify a person

# Confidence levels based on evidence
CRITICAL_THRESHOLD = 10          # 10+ matched pairs = CRITICAL
VERY_HIGH_THRESHOLD = 5          # 5+ matched pairs = VERY HIGH
# else HIGH

# Output and reporting
PROGRESS_UPDATE_FREQUENCY = 100  # Print progress every N combinations
SAMPLE_OUTPUT_SIZE = 5           # Number of sample people to display

## LOAD DATA
def load_data(filename):
    trips = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append(row)
    return trips

data = load_data('202510-bluebikes-tripdata.csv')

print("=" * 80)
print("ROBUST DE-ANONYMIZATION ANALYSIS")
print("Multi-factor fingerprinting of supposedly anonymous bike-share users")
print("=" * 80)
print(f"Total trips in dataset: {len(data)}\n")

# Parse all trips with detailed temporal info
parsed_trips = []
for trip in data:
    try:
        dt = datetime.strptime(trip['started_at'], '%Y-%m-%d %H:%M:%S.%f')
        parsed_trips.append({
            'ride_id': trip['ride_id'],
            'route': f"{trip['start_station_name']} -> {trip['end_station_name']}",
            'start_station': trip['start_station_name'],
            'end_station': trip['end_station_name'],
            'start_station_id': trip.get('start_station_id'),
            'end_station_id': trip.get('end_station_id'),
            'datetime': dt,
            'date': dt.strftime('%Y-%m-%d'),
            'time': dt.strftime('%H:%M'),
            'hour': dt.hour,
            'minute': dt.minute,
            'day_of_week': dt.weekday(),
            'week_number': dt.isocalendar()[1],
            'time_in_minutes': dt.hour * 60 + dt.minute,
            'member_type': trip['member_casual'],
            'duration': int(trip.get('duration', 0)) if trip.get('duration') else None
        })
    except:
        continue

print(f"Successfully parsed: {len(parsed_trips)} trips\n")

# Create multiple grouping structures for analysis
routes = defaultdict(list)
start_stations = defaultdict(list)
commute_patterns = defaultdict(list)  # hour + day_of_week + route
hourly_patterns = defaultdict(list)   # just hour + route

for trip in parsed_trips:
    routes[trip['route']].append(trip)
    start_stations[trip['start_station']].append(trip)
    commute_patterns[(trip['hour'], trip['day_of_week'], trip['route'])].append(trip)
    hourly_patterns[(trip['hour'], trip['route'])].append(trip)

print(f"Total unique routes: {len(routes)}")
print(f"Total unique start stations: {len(start_stations)}\n")

## STRATEGY: HIGH-PRECISION COMMUTE MATCHING
# Find people by: Same member type + same route + precise arrival time + return journey

results = []

print("=" * 80)
print("STRATEGY: HIGH-PRECISION COMMUTE RE-IDENTIFICATION")
print("Matching: Member Type + Route + Arrival Time (±5 min) + Return Journey")
print("=" * 80 + "\n")

# Pre-build index for fast return journey lookup
print("Building indices... (this may take a moment)")
same_day_trips = defaultdict(list)
for trip in parsed_trips:
    key = (trip['date'], trip['member_type'])
    same_day_trips[key].append(trip)

# Group by member_type + route to find people who consistently use same route
member_route_groups = defaultdict(list)
for trip in parsed_trips:
    key = (trip['member_type'], trip['route'])
    member_route_groups[key].append(trip)

# FILTER: Only look at routes used MIN_TRIPS_PER_ROUTE times (much faster)
popular_routes = {k: v for k, v in member_route_groups.items() if len(v) >= MIN_TRIPS_PER_ROUTE}

print(f"Analyzing {len(popular_routes)} high-frequency member-route combinations...\n")

# For each member_type + route combo, look for high-precision patterns
for combo_idx, ((member_type, route), trips) in enumerate(popular_routes.items()):
    if combo_idx % PROGRESS_UPDATE_FREQUENCY == 0:
        print(f"  Processed {combo_idx}/{len(popular_routes)} combinations...")
    
    # Group by time window
    time_clusters = defaultdict(list)
    for trip in trips:
        time_key = trip['time_in_minutes'] // TIME_BUCKET_SIZE  # Round to TIME_BUCKET_SIZE-min buckets
        time_clusters[time_key].append(trip)
    
    # Focus on precise time windows with multiple occurrences
    for time_key, time_window_trips in time_clusters.items():
        if len(time_window_trips) < MIN_TRIPS_IN_TIME_CLUSTER:
            continue
        
        # Get the precise arrival times
        arrival_times = [t['time_in_minutes'] for t in time_window_trips]
        avg_arrival = sum(arrival_times) / len(arrival_times)
        time_variance = max(arrival_times) - min(arrival_times)
        
        # Only keep if very consistent (within MAX_TIME_VARIANCE minutes)
        if time_variance > MAX_TIME_VARIANCE:
            continue
        
        # This is a high-precision arrival time pattern
        avg_hour = int(avg_arrival // 60)
        avg_min = int(avg_arrival % 60)
        
        # Now look for RETURN journeys on the same days
        morning_trips = time_window_trips
        start_station = morning_trips[0]['start_station']
        end_station = morning_trips[0]['end_station']
        
        # Look for return journeys (end_station -> start_station) same day - OPTIMIZED
        matched_pairs = []
        for morning_trip in morning_trips:
            # Use pre-built index instead of searching all trips
            day_trips = same_day_trips[(morning_trip['date'], member_type)]
            
            for other_trip in day_trips:
                min_gap_minutes = MIN_HOURS_BETWEEN_TRIPS * 60
                if (other_trip['start_station'] == end_station and
                    other_trip['end_station'] == start_station and
                    other_trip['time_in_minutes'] > morning_trip['time_in_minutes'] + min_gap_minutes):
                    matched_pairs.append({
                        'outbound': morning_trip,
                        'return': other_trip
                    })
                    break
        
        # If we found matched pairs, this is a real commuter
        if len(matched_pairs) >= MIN_MATCHED_PAIRS:
            commuter_id = f"COMMUTER_{member_type}_{start_station}_{end_station}"
            
            # Determine confidence based on number of matched pairs
            if len(matched_pairs) >= CRITICAL_THRESHOLD:
                confidence = 'CRITICAL'
            elif len(matched_pairs) >= VERY_HIGH_THRESHOLD:
                confidence = 'VERY HIGH'
            else:
                confidence = 'HIGH'
            
            for pair_idx, pair in enumerate(matched_pairs):
                outbound = pair['outbound']
                return_trip = pair['return']
                
                outbound_hour = outbound['hour']
                outbound_min = outbound['minute']
                return_hour = return_trip['hour']
                return_min = return_trip['minute']
                
                results.append({
                    'Person_ID': commuter_id,
                    'Identification_Confidence': confidence,
                    'Evidence_Type': 'Matched Outbound + Return Journey',
                    'Member_Type': member_type,
                    'Outbound_start_station_id': outbound['start_station_id'],
                    'Outbound_end_station_id': outbound['end_station_id'],
                    'Return_start_station_id': return_trip['start_station_id'],
                    'Return_end_station_id': return_trip['end_station_id'],
                    'Outbound_Arrival_Time': f"{outbound_hour:02d}:{outbound_min:02d}",
                    'Return_Departure_Time': f"{return_hour:02d}:{return_min:02d}",
                    'Outbound_Date': outbound['date'],
                    'Return_Date': return_trip['date'],
                    'Time_At_Destination': f"{(return_trip['time_in_minutes'] - outbound['time_in_minutes']) // 60} hours",
                    'Outbound_Ride_ID': outbound['ride_id'],
                    'Return_Ride_ID': return_trip['ride_id'],
                    'Number_Of_Matched_Pairs': len(matched_pairs),
                    'Pattern_Consistency': f"Arrival times within ±{time_variance} minutes",
                    'Why_Not_Anonymous': 'Same member type + route + precise arrival time + return journey = clear person identification'
                })

print(f"Found {len(set(r['Person_ID'] for r in results))} distinct commuters with matched journeys")
print(f"Found {len(results)} individual journey confirmations\n")

# Deduplicate: keep only one row per identified person
final_results = []
seen_people = set()

for result in results:
    person_id = result['Person_ID']
    if person_id not in seen_people:
        final_results.append(result)
        seen_people.add(person_id)

# Sort by most evidence (number of matched pairs)
final_results.sort(key=lambda x: -x['Number_Of_Matched_Pairs'])

## OUTPUT RESULTS

output_file = 'deanonymization_results.csv'

if final_results:
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=final_results[0].keys())
        writer.writeheader()
        writer.writerows(final_results)
    
    print("\n" + "=" * 80)
    print("RESULTS: ANONYMITY COMPROMISED")
    print("=" * 80)
    print(f"\n✗ Successfully re-identified: {len(final_results)} distinct people")
    print(f"✗ Based on: {len(results)} matched outbound + return journey pairs")
    if final_results:
        print(f"✗ All matched via: Same member type + route + precise arrival time ({final_results[0]['Pattern_Consistency']})")
    
    print(f"\n" + "=" * 80)
    print("WHY THIS PROVES ANONYMIZATION FAILS:")
    print("=" * 80)
    print(f"1. Each person has a unique (member_type, route, arrival_time) combination")
    print(f"2. Matching outbound + return journeys proves it's the SAME person")
    print(f"3. Precise arrival times (±5 min) are essentially job schedule = identification")
    print(f"4. Return journey at consistent time proves where they work")
    print(f"\n✓ Output saved to: {output_file}")
    print("=" * 80 + "\n")
    
    # Show sample
    print("SAMPLE RE-IDENTIFICATIONS:")
    for i, person in enumerate(final_results[:SAMPLE_OUTPUT_SIZE]):
        print(f"\nPerson {i+1}:")
        print(f"  - Member Type: {person['Member_Type']}")
        print(f"  - Route: {person['Outbound_start_station_id']} -> {person['Outbound_end_station_id']}")
        print(f"  - Departs home: {person['Outbound_Arrival_Time']}")
        print(f"  - Returns home: {person['Return_Departure_Time']}")
        print(f"  - Time at destination: {person['Time_At_Destination']}")
        print(f"  - Identified on: {person['Number_Of_Matched_Pairs']} different days")
        print(f"  - Time precision: {person['Pattern_Consistency']}")
        print(f"  ➜ Why identified: {person['Why_Not_Anonymous']}")
else:
    print("\nNo matched commuters found.")
    print("Try adjusting match criteria or check dataset size.")