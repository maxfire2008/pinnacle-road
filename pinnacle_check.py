import time
import requests
import re
import json
import os
from homeassistant_api import (
    Client,
)  # You'll need to install the homeassistant-api package

# Configuration
HOME_ASSISTANT_URL = os.environ.get("HOME_ASSISTANT_URL")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
INTERVAL = os.environ.get("INTERVAL", 300)
URL = "https://hccapps.hobartcity.com.au/PinnacleRoad/"

# Gate lookup table (example data)
GATE_LOOKUP = {
    1: {"name": "Gate 1", "lat": "-42.8821", "lon": "147.3272"},
    2: {"name": "Gate 2", "lat": "-42.8721", "lon": "147.3372"},
    3: {"name": "Gate 3", "lat": "-42.8621", "lon": "147.3472"},
    4: {"name": "Gate 4", "lat": "-42.8521", "lon": "147.3572"},
    5: {"name": "Gate 5", "lat": "-42.8421", "lon": "147.3672"},
}


def fetch_data():
    response = requests.get(URL)
    response.raise_for_status()
    return response.text


def parse_data(html):
    data = {}

    # Gate closed
    gate_match = re.search(r"var closedGate = (\d+);", html)
    if gate_match:
        closed_gate_id = int(gate_match.group(1))
        if closed_gate_id == 1:
            data["road_status"] = "Road open"
        else:
            gate_info = GATE_LOOKUP.get(
                closed_gate_id, {"name": "Unknown", "lat": "0", "lon": "0"}
            )
            data["road_status"] = (
                f'Road is closed at gate {closed_gate_id} - {gate_info["name"]}'
            )
            data["gate_name"] = gate_info["name"]
            data["gate_lat"] = gate_info["lat"]
            data["gate_lon"] = gate_info["lon"]

    # HTML info
    data["html_info"] = {}
    for key in [
        "Next update",
        "Last update",
        "Reason for closure",
        "Walking distance to snow",
    ]:
        match = re.search(rf"<strong>{key}:</strong>\s*(.*?)<br\s*/?>", html)
        if match:
            data["html_info"][key] = match.group(1).strip()

    return data


def post_to_home_assistant(data):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    states = {
        "sensor.road_status": data.get("road_status", "Unknown"),
        "sensor.gate_name": data.get("gate_name", "Unknown"),
        "sensor.gate_lat": data.get("gate_lat", "0"),
        "sensor.gate_lon": data.get("gate_lon", "0"),
        "sensor.html_info": json.dumps(data.get("html_info", {})),
    }

    for entity, value in states.items():
        response = requests.post(
            f"{HOME_ASSISTANT_URL}/{entity}", headers=headers, json={"state": value}
        )
        response.raise_for_status()


def main():
    html = fetch_data()
    data = parse_data(html)
    post_to_home_assistant(data)


def event_loop():
    while True:
        main()
        time.sleep(-(time.time() % -INTERVAL))


if __name__ == "__main__":
    event_loop()
