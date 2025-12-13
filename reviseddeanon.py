# build lookup structures
same_day = defaultdict(list)
for trip in parsed:
    key = (trip['date'], trip['member_type'])
    same_day[key].append(trip)

quasi_id_counts = defaultdict(int)
for trip in parsed:
    arrival_bucket = trip['time_in_minutes'] // TIME_BUCKET
    quasi_id = (trip['member_type'], trip['route'], arrival_bucket)
    quasi_id_counts[quasi_id] += 1

relaxed_thresholds = [5, 10, 15, 20]
relaxed_counts = {t: defaultdict(int) for t in relaxed_thresholds}

for trip in parsed:
    for threshold in relaxed_thresholds:
        arrival_bucket = trip['time_in_minutes'] // threshold
        quasi_id = (trip['member_type'], trip['route'], arrival_bucket)
        relaxed_counts[threshold][quasi_id] += 1

member_route_groups = defaultdict(list)
for trip in parsed:
    key = (trip['member_type'], trip['route'])
    member_route_groups[key].append(trip)

popular = {k: v for k, v in member_route_groups.items() if len(v) >= MIN_TRIPS}

print(f"\nAnalyzing {len(popular)} frequent routes...")
routes = defaultdict(list)
start_stations = defaultdict(list)
commute_patterns = defaultdict(list)
hourly_patterns = defaultdict(list)

for trip in parsed:
    routes[trip['route']].append(trip)
    start_stations[trip['start_station']].append(trip)
    commute_patterns[(trip['hour'], trip['day_of_week'], trip['route'])].append(trip)
    hourly_patterns[(trip['hour'], trip['route'])].append(trip)

import csv
from collections import defaultdict
from datetime import datetime

# Config
MIN_TRIPS = 5
MIN_CLUSTER = 2
TIME_BUCKET = 8
MAX_VARIANCE = 5
MIN_HOURS_GAP = 4
MIN_PAIRS = 2

CRITICAL = 10
VERY_HIGH = 5

PROGRESS_FREQ = 100
SAMPLE_SIZE = 5

def load_data(filename):
    trips = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append(row)
    return trips

data = load_data('202510-bluebikes-tripdata.csv')

print(f"Loaded {len(data)} trips from dataset")

parsed = []
for trip in data:
    try:
        dt = datetime.strptime(trip['started_at'], '%Y-%m-%d %H:%M:%S.%f')
        parsed.append({
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
            'duration': int(trip.get('duration', 0)) if trip.get('duration', '').strip() else 0
        })
    except:
        continue

print(f"Parsed {len(parsed)} trips, {len(routes)} unique routes")

results = []

print(f"\nAnalyzing {len(popular)} frequent routes...")

for combo_idx, ((member_type, route), trips) in enumerate(popular.items()):
    # group by time window
    time_clusters = defaultdict(list)
    for trip in trips:
        time_key = trip['time_in_minutes'] // TIME_BUCKET
        time_clusters[time_key].append(trip)
    
    for time_key, time_window_trips in time_clusters.items():
        if len(time_window_trips) < MIN_CLUSTER:
            continue
        
        arrival_times = [t['time_in_minutes'] for t in time_window_trips]
        avg_arrival = sum(arrival_times) / len(arrival_times)
        time_variance = max(arrival_times) - min(arrival_times)
        
        if time_variance > MAX_VARIANCE:
            continue
        
        avg_hour = int(avg_arrival // 60)
        avg_min = int(avg_arrival % 60)
        
        morning_trips = time_window_trips
        start_station = morning_trips[0]['start_station']
        end_station = morning_trips[0]['end_station']
        
        # look for return trips
        matched_pairs = []
        for morning_trip in morning_trips:
            day_trips = same_day[(morning_trip['date'], member_type)]
            
            for other_trip in day_trips:
                min_gap = MIN_HOURS_GAP * 60
                if (other_trip['start_station'] == end_station and
                    other_trip['end_station'] == start_station and
                    other_trip['time_in_minutes'] > morning_trip['time_in_minutes'] + min_gap):
                    matched_pairs.append({
                        'outbound': morning_trip,
                        'return': other_trip
                    })
                    break
        
        if len(matched_pairs) >= MIN_PAIRS:
            commuter_id = f"COMMUTER_{member_type}_{start_station}~{end_station}"
            
            if len(matched_pairs) >= CRITICAL:
                confidence = 'CRITICAL'
            elif len(matched_pairs) >= VERY_HIGH:
                confidence = 'VERY HIGH'
            else:
                confidence = 'HIGH'
            
            for pair_idx, pair in enumerate(matched_pairs):
                outbound = pair['outbound']
                return_trip = pair['return']
                
                out_hr = outbound['hour']
                out_min = outbound['minute']
                ret_hr = return_trip['hour']
                ret_min = return_trip['minute']
                
                # biking time calc
                out_bike_sec = outbound.get('duration') or 0
                out_bike_min = out_bike_sec / 60 if out_bike_sec > 0 else 0
                
                # redock time
                out_redock_min = outbound['time_in_minutes'] + out_bike_min
                out_redock_hr = int(out_redock_min // 60)
                out_redock_m = int(out_redock_min % 60)
                
                # time at destination
                time_at_dest_min = return_trip['time_in_minutes'] - out_redock_min
                hrs_at_dest = int(time_at_dest_min // 60)
                mins_at_dest = int(time_at_dest_min % 60)
                time_at_dest_str = f"{hrs_at_dest}h {mins_at_dest}m"
                
                results.append({
                    'Person_ID': commuter_id,
                    'Identification_Confidence': confidence,
                    'Evidence_Type': 'Matched Outbound + Return Journey',
                    'Member_Type': member_type,
                    'Outbound_start_station_id': outbound['start_station_id'],
                    'Outbound_end_station_id': outbound['end_station_id'],
                    'Return_start_station_id': return_trip['start_station_id'],
                    'Return_end_station_id': return_trip['end_station_id'],
                    'Outbound_Undock_Time': f"{out_hr:02d}:{out_min:02d}",
                    'Outbound_Redock_Time': f"{out_redock_hr:02d}:{out_redock_m:02d}",
                    'Return_Undock_Time': f"{ret_hr:02d}:{ret_min:02d}",
                    'Outbound_Date': outbound['date'],
                    'Return_Date': return_trip['date'],
                    'Outbound_Bike_Time_Minutes': round(out_bike_min, 1),
                    'Time_At_Destination': time_at_dest_str,
                    'Outbound_Ride_ID': outbound['ride_id'],
                    'Return_Ride_ID': return_trip['ride_id'],
                    'Number_Of_Matched_Pairs': len(matched_pairs),
                    'Pattern_Consistency': f"Arrival times within ±{time_variance} minutes",
                    'Quasi_Identifier': f"({member_type}, {route}, ~{outbound['time_in_minutes']//TIME_BUCKET * TIME_BUCKET})",
                    'Why_Not_Anonymous': 'Same member type + route + precise arrival time + return journey = clear person identification'
                })

print(f"Found {len(final_results)} identifiable commuters")
print(f"Writing to {output_file}...")

# dedup by person
final_results = []
seen = set()

for result in results:
    pid = result['Person_ID']
    if pid not in seen:
        final_results.append(result)
        seen.add(pid)

# calc privacy metrics
for result in final_results:
    member_type = result['Member_Type']
    route = result['Quasi_Identifier'].split(', ')[1]
    arrival_bucket = int(result['Quasi_Identifier'].split('~')[1].rstrip(')'))
    
    quasi_id = (member_type, route, arrival_bucket)
    anon_set = quasi_id_counts[quasi_id]
    
    uniqueness = (1.0 / anon_set * 100) if anon_set > 0 else 0
    k_violated = "YES - K-anonymity violated!" if anon_set < 5 else "NO - Acceptable"
    
    if anon_set <= 2:
        privacy_risk = "CRITICAL - Almost unique"
    elif anon_set <= 5:
        privacy_risk = "HIGH - Few matches"
    elif anon_set <= 10:
        privacy_risk = "MEDIUM - Moderate matches"
    else:
        privacy_risk = "LOW - Many matches"
    
    # relaxed threshold calc
    relaxed_risks = {}
    for threshold in relaxed_thresholds:
        relaxed_bucket = int(result['Outbound_Undock_Time'].split(':')[0]) * 60 + int(result['Outbound_Undock_Time'].split(':')[1])
        relaxed_bucket = relaxed_bucket // threshold
        relaxed_quasi = (member_type, route, relaxed_bucket)
        relaxed_anon = relaxed_counts[threshold].get(relaxed_quasi, 1)
        relaxed_risks[f"Anonymity_at_±{threshold}min"] = relaxed_anon
    
    result['Anonymity_Set_Size'] = anon_set
    result['Uniqueness_Score'] = round(uniqueness, 2)
    result['K_Anonymity_Violated'] = k_violated
    result['Privacy_Risk_Level'] = privacy_risk
    
    for threshold, count in relaxed_risks.items():
        result[threshold] = count

# sort by bike time
final_results.sort(key=lambda x: x.get('Outbound_Bike_Time_Minutes', float('inf')))

output_file = 'deanonymization_results_sensitivity2.csv'

if final_results:
    final_sorted = sorted(final_results, key=lambda x: -x['Number_Of_Matched_Pairs'])
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=final_sorted[0].keys())
        writer.writeheader()
        writer.writerows(final_sorted)
    
    print(f"\nResults written to {output_file}")
    print(f"\nIdentified {len(final_results)} people")
    
    k_violations = sum(1 for r in final_results if "YES" in r.get('K_Anonymity_Violated', ''))
    avg_anon = sum(r['Anonymity_Set_Size'] for r in final_results)/len(final_results)
    
    print(f"K-anonymity violations: {k_violations}/{len(final_results)} ({k_violations/len(final_results)*100:.1f}%)")
    print(f"Avg anonymity set size: {avg_anon:.1f}")
    
    print("\nTop 5 by shortest bike time:")
    for i, person in enumerate(final_results[:5]):
        print(f"\n{i+1}. {person['Outbound_Bike_Time_Minutes']} min | {person['Member_Type']}")
        print(f"   {person['Outbound_start_station_id']} -> {person['Outbound_end_station_id']}")
        print(f"   Matched {person['Number_Of_Matched_Pairs']} trips")
        print(f"   Anonymity set: {person['Anonymity_Set_Size']}, Risk: {person['Privacy_Risk_Level']}")
else:
    print("\nNo matches found")