import time
import requests
import re
import json
import os

# Configuration
HOME_ASSISTANT_URL = os.environ.get("HOME_ASSISTANT_URL")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
INTERVAL = os.environ.get("INTERVAL", 300)
URL = "https://hccapps.hobartcity.com.au/PinnacleRoad/"

# Gate lookup table (example data)
GATE_LOOKUP = {
    1: {"name": "Bracken Lane (Gate 1)", "lat": -42.917, "lon": 147.261},
    2: {"name": "Below The Springs (Gate 2)", "lat": -42.912, "lon": 147.253},
    3: {"name": "The Springs (Gate 3)", "lat": -42.914, "lon": 147.246},
    4: {"name": "The Chalet (Gate 4)", "lat": -42.890, "lon": 147.236},
    5: {"name": "Big Bend (Gate 5)", "lat": -42.890, "lon": 147.221},
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
        closed_gate_id = int(gate_match.group(1)) - 2
        data["closed_gate"] = closed_gate_id
        if closed_gate_id == 0:
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
        "pinnacle_road.closed_gate": data.get("closed_gate", 0),
        "pinnacle_road.road_status": data.get("road_status", "Unknown"),
        "pinnacle_road.gate_name": data.get("gate_name", "Unknown"),
    }

    for entity, value in states.items():
        payload = {"state": value, "attributes": {}}
        response = requests.post(
            f"{HOME_ASSISTANT_URL}/{entity}", headers=headers, json=payload
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
