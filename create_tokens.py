import requests

CLIENT_ID = "PUT YOUR ID HERE"         
CLIENT_SECRET = "PUT YOUR CLIENT SECRET HERE"
AUTH_CODE = "PUT YOUR AUTH CODE HERE"

payload = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": AUTH_CODE,
    "grant_type": "authorization_code"
}

r = requests.post("https://www.strava.com/api/v3/oauth/token", data=payload)
print(r.status_code)
print(r.text)
