# strava_polylines

Simple Python scripts that use the Strava API to download all of your activities, filter them to an area of interest, and export the tracks as **GeoJSON** for use in GIS software (QGIS, ArcGIS Pro, …).

The workflow is:

1. Authorise an app in Strava and obtain a **refresh token**.
2. Use that refresh token to get an **access token**.
3. Call the Strava API for all your activities.
4. For activities that start inside a chosen bounding box, request the GPS
   stream and write it out as GeoJSON LineStrings (or Points if no stream).

---

## Repository layout

```text
strava_polylines/
├── README.md          # This file
├── create_tokens.py   # One-off helper: exchange auth code → access + refresh token
└── strava_lines.py    # Main script: fetch activities + streams and export GeoJSON
```

---


### `create_tokens.py`

One-time helper script used during setup.

* Takes your **client ID**, **client secret** and a one-time **authorisation
  code** from Strava.
* Calls `https://www.strava.com/api/v3/oauth/token` with
  `grant_type=authorization_code`.
* Prints the JSON response so you can copy the **refresh_token** and keep it
  for the main script.

You normally run this once per app/user (or if you need to re-authorise).

### `strava_lines.py`

Main script that does the actual data download and export.

* Uses your **client ID**, **client secret** and **refresh token** to obtain a
  fresh access token (`grant_type=refresh_token`).
* Calls `/athlete/activities` to download all your activities (paginated).
* Filters activities whose **start point** falls inside a configurable
  bounding box (`MIN_LAT`, `MAX_LAT`, `MIN_LON`, `MAX_LON`).
* For each matching activity:

  * Requests the `latlng` stream from `/activities/{id}/streams`.
  * Builds a **LineString** GeoJSON feature from the coordinates, or a **Point** if no stream is available.
  * Attaches useful properties (name, sport type, distance, times, etc.).
  * Writes everything to a single **GeoJSON FeatureCollection** file, ready for GIS.

By default the output is:

```python
OUTPUT_GEOJSON = "strava_activities.geojson"
```

but you can rename that to anything you like.

> **Note:** The helper function is called `is_in_aoi`, and simply checks
> whether the start coordinate is inside the configured bounding box – you can
> set this to *any* area of interest.

---

## Requirements

* Python **3.x**
* [`requests`](https://pypi.org/project/requests/) library

Install `requests`:

```bash
python -m pip install requests
# or
pip install requests
```

---

## 1. Set up a Strava API application

1. Log in to Strava in your browser.
2. Go to **Settings → My API Application**.
3. Create an application if you don’t already have one.
4. Note down:

   * **Client ID**
   * **Client Secret**

These values are used in both scripts.

---

## 2. Get an authorisation code

You need to authorise your app to read your activities explicitly. If you don't do this step, the script will not function.

In your browser, open this URL (replace `YOUR_CLIENT_ID`):

```text
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=read,activity:read_all
```

Steps:

1. Log in (if asked) and click **Authorise**.

2. Strava will redirect your browser to something like:

   ```text
   http://localhost/exchange_token?state=&code=ABCDEF1234567890&scope=read,activity:read_all
   ```

3. Copy the value after `code=` (e.g. `ABCDEF1234567890`).
   That’s your **authorisation code** (one-time use).

---

## 3. Exchange the authorisation code for tokens

Open `create_tokens.py` and insert your values:

```python
import requests

CLIENT_ID = "PUT YOUR ID HERE"
CLIENT_SECRET = "PUT YOUR CLIENT SECRET HERE"
AUTH_CODE = "PUT YOUR AUTH CODE HERE"   # from the redirect URL

payload = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": AUTH_CODE,
    "grant_type": "authorization_code"
}

r = requests.post("https://www.strava.com/api/v3/oauth/token", data=payload)
print(r.status_code)
print(r.text)
```

Run it:

```bash
python create_tokens.py
```

You should see a JSON response similar to:

```json
{
  "token_type": "Bearer",
  "access_token": "NEW_ACCESS_TOKEN",
  "refresh_token": "NEW_REFRESH_TOKEN",
  "expires_at": 1764712345,
  "expires_in": 21600,
  "scope": "read,activity:read_all",
  "athlete": { ... }
}
```

Copy the value of `"refresh_token"` – you’ll use this in the main script.

> Make sure the `scope` includes **`activity:read_all`** (or at least
> `activity:read`). Without that, calls to `/athlete/activities` will fail with
> `401 Unauthorized`.

---

## 4. Configure and run `strava_lines.py`

Open `strava_lines.py` and set your credentials:

```python
CLIENT_ID = "PUT YOUR ID HERE"           # e.g. "12345"
CLIENT_SECRET = "PUT YOUR SECRET HERE"
REFRESH_TOKEN = "PUT YOUR REFRESH TOKEN HERE"
```

Set the output filename if you want:

```python
OUTPUT_GEOJSON = "strava_activities_aoi.geojson"
```

Set your **area of interest** using a bounding box in WGS84
(latitude/longitude):

```python
# Example: simple AOI, change to whatever you need
MIN_LAT = 50
MAX_LAT = 50
MIN_LON = 10
MAX_LON = 18
```

> Anything whose `start_latlng` falls within this box will be included.
> Outside = skipped.

Now run the script:

```bash
python strava_lines.py
```

You should see output along the lines of:

```text
Token refresh status: 200 {...}
Scopes: read,activity:read_all
New access token obtained, expires at 2025-12-02 21:38:29
Requesting activities page 1...
Requesting activities page 2...
...
Activities in Austria (features): 23
Saved to strava_activities_aoi.geojson
```

---

## 5. Using the output in GIS

The script writes a **GeoJSON** file in WGS84 (EPSG:4326) with a structure like:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[lon, lat], ...]
      },
      "properties": {
        "id": 1234567890,
        "name": "Morning Run",
        "sport_type": "Run",
        "start_date": "2025-11-30T08:15:23Z",
        "distance_m": 5234.2,
        "moving_time_s": 1543,
        "elapsed_time_s": 1600,
        "start_lat": 47.8001,
        "start_lon": 13.0423
      }
    }
  ]
}
```

### QGIS

* **Layer → Add Layer → Add Vector Layer**
* Source type: *File* → select the GeoJSON → *Open*.
* If you need metric analyses, reproject to a suitable projected CRS (e.g.
  **EPSG:3416** for Austria, **EPSG:5514** for Czechia, etc.).

### ArcGIS Pro

* `Map` tab → **Add Data** → select the GeoJSON.
* You can then project it to a File Geodatabase feature class if needed.

---

## 6. Security notes

* **Never commit real `CLIENT_SECRET`, `ACCESS_TOKEN`, or `REFRESH_TOKEN`
  values to a public repository.**
* The example scripts use placeholder strings – keep it that way in Git, and
  override them locally (for example via environment variables or a private
  config file that is `.gitignore`d).
* If you suspect a secret was exposed, regenerate it in the Strava API settings
  and update your local config.

---

## Troubleshooting

* **401 Unauthorized on `/athlete/activities`**

  * Check that your refresh token was obtained using a URL with
    `scope=read,activity:read_all`.
  * Re-run `create_tokens.py` with a **fresh authorisation code**.
  * Ensure `CLIENT_ID`, `CLIENT_SECRET` and `REFRESH_TOKEN` all belong to the
    same Strava app.

* **Empty or very few features**

  * Check your bounding box (`MIN_LAT`, `MAX_LAT`, `MIN_LON`, `MAX_LON`).
  * Remember the script only includes activities whose **start point** is
    inside that box.

---
