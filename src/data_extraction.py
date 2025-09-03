import requests
import csv


def get_earthquakes(min_latitude, max_latitude, min_longitude, max_longitude, 
                    start_time, end_time, min_magnitude):
    base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    
    params = {
        'format': 'geojson',
        'starttime': start_time,
        'endtime': end_time,
        'minlatitude': min_latitude,
        'maxlatitude': max_latitude,
        'minlongitude': min_longitude,
        'maxlongitude': max_longitude,
        'minmagnitude': min_magnitude
    }
    
    response = requests.get(base_url, params=params)
    
    
    data = response.json()
    
    if 'features' not in data or len(data['features']) == 0:
        print("No earthquakes found matching criteria")
        return []
    
    earthquakes = []
    for feature in data['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']
        print(feature['id'])
        earthquakes.append(feature['id'])

    return earthquakes

    
def write_earthquake_data(earthquake_id, output_file_name):
    # Step 1: Set the event ID
    event_id = earthquake_id
    geojson_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={event_id}&format=geojson"

    # Step 2: Get GeoJSON metadata
    print(event_id)
    geo_response = requests.get(geojson_url)
    if geo_response.status_code != 200:
        print("Failed to fetch GeoJSON for event.")
        return ""


    geo_data = geo_response.json()
    feature = geo_data  # It's a single Feature object

    # Earthquake-level metadata
    properties = feature["properties"]
    geometry = feature["geometry"]

    event_code = properties.get("code", "")
    magnitude = properties.get("mag", "")
    longitude = geometry["coordinates"][0]
    latitude = geometry["coordinates"][1]
    depth = geometry["coordinates"][2]

    # Step 3: Get stationlist URL from ShakeMap product
    try:
        shakemap = properties["products"]["shakemap"][0]
        stationlist_url = shakemap["contents"]["download/stationlist.json"]["url"]
    except KeyError:
        return ""

    # Step 4: Download and parse stationlist.json
    response = requests.get(stationlist_url)
    if response.status_code != 200:
        raise Exception("Failed to fetch stationlist.json")

    data = response.json()

    # Step 5: Prepare CSV
    output_file = output_file_name

    # Define priority of channels per orientation
    E_priority = ["HNE", "BHE", "ENE", "LNE"]
    N_priority = ["HNN", "BHN", "ENN", "LNN"]

    def extract_amplitudes(channel_data):
        return {amp["name"]: amp["value"] for amp in channel_data.get("amplitudes", [])}

    def get_best_channel(channels, preferred_list):
        for name in preferred_list:
            for ch in channels:
                if ch.get("name") == name:
                    return extract_amplitudes(ch)
        return {"pgv": "", "sa(1.0)": "", "sa(0.3)": "", "sa(3.0)": "", "pga": ""}

    # Step 6: Write CSV
    with open(output_file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)

        for feature in data["features"]:
            props = feature["properties"]
            code = props.get("code", "")
            distance = props.get("distance", "")
            vs30 = props.get("vs30", "")
            pga = props.get("pga", "")
            pgv = props.get("pgv", "")
            channels = props.get("channels", [])

            e_vals = get_best_channel(channels, E_priority)
            n_vals = get_best_channel(channels, N_priority)

            def safe_float(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            # Safely parse and compare
            sa03_e = safe_float(e_vals.get("sa(0.3)", ""))
            sa03_n = safe_float(n_vals.get("sa(0.3)", ""))
            max_sa03 = max([v for v in [sa03_e, sa03_n] if v is not None], default="")

            sa10_e = safe_float(e_vals.get("sa(1.0)", ""))
            sa10_n = safe_float(n_vals.get("sa(1.0)", ""))
            max_sa10 = max([v for v in [sa10_e, sa10_n] if v is not None], default="")

            sa30_e = safe_float(e_vals.get("sa(3.0)", ""))
            sa30_n = safe_float(n_vals.get("sa(3.0)", ""))
            max_sa30 = max([v for v in [sa30_e, sa30_n] if v is not None], default="")

            row = [
                event_code, magnitude, longitude, latitude, depth,
                code, distance, vs30, pga, pgv,
                max_sa03, max_sa10, max_sa30,
                e_vals.get("pgv", ""), e_vals.get("sa(0.3)", ""),  e_vals.get("sa(1.0)", ""),  e_vals.get("sa(3.0)", ""), e_vals.get("pga", ""),
                n_vals.get("pgv", ""), n_vals.get("sa(0.3)", ""), n_vals.get("sa(1.0)", ""), n_vals.get("sa(3.0)", ""), n_vals.get("pga", "")
            ]
            if any(val == "" for val in row):
                continue

            writer.writerow(row)

    print(f"CSV written to: {output_file}")

def main():
    # USER PARAMETERS
    min_latitude = 54
    max_latitude = 65
    min_longitude = -160
    max_longitude = -134
    start_time = "2020-01-01"
    end_time = "2024-12-30"
    min_magnitude = 3.4
    output_file_name = "StationsBeta5.csv"

    earthquakes = get_earthquakes(min_latitude, max_latitude, min_longitude, max_longitude,
                               start_time, end_time, min_magnitude)
    
    print(earthquakes)


    headers = [
        "event_id", "mag", "longitude", "latitude", "depth (km)",
        "code", "distance (km)", "vs30", "pga (%g)", "pgv (cm/s)",
        "max_sa(0.3)", "max_sa(1.0)", "max_sa(3.0)",
        "E-pgv (cm/s)","E-sa(0.3) (%g)", "E-sa(1.0) (%g)",  "E-sa(3.0) (%g)", "E-pga (%g)",
        "N-pgv (cm/s)","N-sa(0.3) (%g)", "N-sa(1.0) (%g)", "N-sa(3.0) (%g)", "N-pga (%g)"
    ]
    with open(output_file_name, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)


    for earthquake in earthquakes:
        write_earthquake_data(earthquake, output_file_name)

    print("Finished!")




main()
