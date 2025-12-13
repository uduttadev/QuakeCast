import sys
import sqlite3
import joblib
import pandas as pd
import json
import math
import numpy as np

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def main():
    try:
        # Load the model
        model = joblib.load("best_model.pkl")

        # Get arguments
        if len(sys.argv) < 5:
            print(json.dumps({'error': 'Not enough arguments'}))
            sys.exit(1)

        event_lon = float(sys.argv[1])
        event_lat = float(sys.argv[2])
        magnitude = float(sys.argv[3])
        depth = float(sys.argv[4])

        # Connect to database and fetch stations
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        cursor.execute("SELECT SiteName, Latitude, Longitude FROM Site")
        stations = cursor.fetchall()
        conn.close()

        if not stations:
            print(json.dumps({'error': 'No stations found in database'}))
            sys.exit(1)

        # Prepare data for prediction
        prediction_data = []
        station_info = []

        for site_name, st_lat, st_lon in stations:
            if st_lat is None or st_lon is None:
                continue
                
            dist = haversine_distance(event_lat, event_lon, st_lat, st_lon)
            
            # Features must match the model's expected input exactly
            # "mag", "longitude", "latitude", "depth (km)", "distance (km)", "vs30"
            # Note: longitude/latitude here refer to the EVENT location based on the user's snippet?
            # "For mag, longitude. latitude, depth it will pull from the users inputs."
            # So these are the EVENT coordinates.
            
            row = {
                "mag": magnitude,
                "longitude": event_lon,
                "latitude": event_lat,
                "depth (km)": depth,
                "distance (km)": dist,
                "vs30": 350.0  # Hardcoded as requested
            }
            prediction_data.append(row)
            station_info.append({
                'SiteName': site_name,
                'Latitude': st_lat,
                'Longitude': st_lon,
                'Distance': dist
            })

        if not prediction_data:
            print(json.dumps({'error': 'No valid station data for prediction'}))
            sys.exit(1)

        df = pd.DataFrame(prediction_data)

        # Predict
        # The model returns [PGA, PGV] for each row
        predictions = model.predict(df)

        results = []
        for i, (pga_pgv) in enumerate(predictions):
            # Handle case where prediction might be scalar or array
            # Based on snippet: pga_pgv = model.predict(df)[0] -> implies list of lists or 2D array
            # But here we predict on multiple rows.
            
            pga = float(pga_pgv[0])
            pgv = float(pga_pgv[1])
            
            results.append({
                'station': station_info[i]['SiteName'],
                'lat': station_info[i]['Latitude'],
                'lng': station_info[i]['Longitude'],
                'distance': station_info[i]['Distance'],
                'pga': pga,
                'pgv': pgv
            })

        # Output result
        print(json.dumps({'predictions': results}))

    except Exception as e:
        # print(f"Error: {str(e)}", file=sys.stderr) # Debugging
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
