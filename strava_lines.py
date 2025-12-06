import requests
import json
from datetime import datetime


#fill these from your Strava API application
CLIENT_ID = "PUT YOUR ID HERE"                 # e.g. "12345"
CLIENT_SECRET = "PUT YOUR SECRET HERE"
REFRESH_TOKEN = "PUT YOUR REFRESH TOKEN HERE"

#output file
OUTPUT_GEOJSON = "strava_activities.geojson" # rename this to what you would like. The file is currently saved to the same location as py file.

#approximate bounding box (WGS84), this can be changed to any AOI
MIN_LAT = 50
MAX_LAT = 50
MIN_LON = 10
MAX_LON = 18

#main script
def refresh_access_token():
    """Use the refresh token to get a fresh access token."""
    url = "https://www.strava.com/api/v3/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    resp = requests.post(url, data=payload)
    print("Token refresh status:", resp.status_code, resp.text)  # <--- add this line
    resp.raise_for_status()
    data = resp.json()
    access_token = data["access_token"]
    print("Scopes:", data.get("scope"))
    print(f"New access token obtained, expires at {datetime.fromtimestamp(data['expires_at'])}")
    return access_token


def is_in_austria(lat, lon):
    """Check if a point is inside the Austria bounding box."""
    if lat is None or lon is None:
        return False
    return (MIN_LAT <= lat <= MAX_LAT) and (MIN_LON <= lon <= MAX_LON)


def get_all_activities(access_token, per_page=100):
    """Download all activities for the athlete (paginated)."""
    activities = []
    page = 1
    headers = {"Authorization": f"Bearer {access_token}"}

    while True:
        print(f"Requesting activities page {page}...")
        url = "https://www.strava.com/api/v3/athlete/activities"
        params = {
            "page": page,
            "per_page": per_page
        }
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        page_data = resp.json()

        if not page_data:
            break

        activities.extend(page_data)
        page += 1

    print(f"Total activities fetched: {len(activities)}")
    return activities


def get_activity_stream(access_token, activity_id):
    """
    Get the latlng stream for an activity.
    Returns a list of [lat, lon] pairs or None if not available.
    """
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "keys": "latlng",
        "key_by_type": "true"
    }

    resp = requests.get(url, headers=headers, params=params)

    # If no stream, return None
    if resp.status_code == 404:
        return None

    resp.raise_for_status()
    data = resp.json()

    if "latlng" not in data or "data" not in data["latlng"]:
        return None

    return data["latlng"]["data"]  # list of [lat, lon]


def activities_to_geojson(access_token, activities):
    """
    Convert activities to a GeoJSON FeatureCollection of LineStrings.
    """
    features = []

    for act in activities:
        start_latlng = act.get("start_latlng", None)
        if not start_latlng or len(start_latlng) != 2:
            continue

        start_lat, start_lon = start_latlng[0], start_latlng[1]

        # Filter: only activities that *start* in Austria
        if not is_in_austria(start_lat, start_lon):
            continue

        activity_id = act["id"]
        name = act.get("name", "")
        sport_type = act.get("sport_type", act.get("type", ""))
        start_date = act.get("start_date")
        distance = act.get("distance", 0)
        moving_time = act.get("moving_time", 0)
        elapsed_time = act.get("elapsed_time", 0)

        print(f"Fetching stream for activity {activity_id} ({name})...")

        latlng_stream = get_activity_stream(access_token, activity_id)

        # If no detailed stream, fall back to a single point
        if not latlng_stream:
            print(f"  No latlng stream for activity {activity_id}, using start point only.")
            coords = [[start_lon, start_lat]]
            geom_type = "Point"
        else:
            # GeoJSON uses [lon, lat]
            coords = [[pt[1], pt[0]] for pt in latlng_stream]
            geom_type = "LineString"

        geometry = {
            "type": geom_type,
            "coordinates": coords if geom_type == "LineString" else coords[0]
        }

        properties = {
            "id": activity_id,
            "name": name,
            "sport_type": sport_type,
            "start_date": start_date,
            "distance_m": distance,
            "moving_time_s": moving_time,
            "elapsed_time_s": elapsed_time,
            "start_lat": start_lat,
            "start_lon": start_lon
        }

        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": properties
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson


def main():
    access_token = refresh_access_token()
    activities = get_all_activities(access_token)
    geojson = activities_to_geojson(access_token, activities)

    print(f"Activities in Austria (features): {len(geojson['features'])}")

    with open(OUTPUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_GEOJSON}")


if __name__ == "__main__":
    main()
