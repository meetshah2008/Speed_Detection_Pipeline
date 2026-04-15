"""
Module 4: Action Handler (API)
------------------------------
Sends POST alerts to an external endpoint when speeding is detected.
"""

import requests


class APIHandler:
    def __init__(self, api_url="http://localhost:8000/speed", timeout=1.0):
        self.api_url = api_url
        self.timeout = timeout

    def send_alert(self, track_id, speed_kmh):
        payload = {
            "vehicle_id": int(track_id),
            "speed": float(speed_kmh),
        }
        try:
            requests.post(self.api_url, json=payload, timeout=self.timeout)
            return True
        except requests.RequestException:
            return False
