"""Thin wrapper around the OpenF1 REST API (https://openf1.org).

OpenF1 gives us near-real-time data during a live session (car positions,
gaps/intervals, tyre stints, weather, etc). It does not require an API key.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = os.getenv("BASE_URL")


class OpenF1Client:
    """Small helper for calling OpenF1 endpoints and returning parsed JSON."""

    def __init__(self, base_url: str | None = None, timeout: int = 10):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/") + "/"
        self.timeout = timeout

    def _get(self, endpoint: str, **params):
        url = f"{self.base_url}{endpoint}"
        clean_params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(url, params=clean_params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # -- Sessions -----------------------------------------------------
    def get_latest_session(self):
        """Return the most recent session (live if one is running, else the
        last completed one)."""
        sessions = self._get("sessions", session_key="latest")
        return sessions[0] if sessions else None

    def get_sessions(self, year=None, meeting_key=None, country_name=None):
        return self._get(
            "sessions", year=year, meeting_key=meeting_key, country_name=country_name
        )

    # -- Session-scoped data ------------------------------------------
    def get_drivers(self, session_key="latest"):
        return self._get("drivers", session_key=session_key)

    def get_positions(self, session_key="latest"):
        return self._get("position", session_key=session_key)

    def get_intervals(self, session_key="latest"):
        return self._get("intervals", session_key=session_key)

    def get_stints(self, session_key="latest"):
        return self._get("stints", session_key=session_key)

    def get_laps(self, session_key="latest", driver_number=None):
        return self._get("laps", session_key=session_key, driver_number=driver_number)

    def get_weather(self, session_key="latest"):
        return self._get("weather", session_key=session_key)

    def get_race_control(self, session_key="latest"):
        return self._get("race_control", session_key=session_key)


def latest_by_driver(records: list[dict], key: str = "date") -> dict:
    """Given a list of time-stamped records that each contain a
    'driver_number', return a dict mapping driver_number -> most recent
    record. OpenF1 endpoints return the full history for a session, so the
    UI needs to reduce that down to "what's true right now"."""
    latest: dict[int, dict] = {}
    for rec in records:
        num = rec.get("driver_number")
        if num is None:
            continue
        current = latest.get(num)
        if current is None or rec.get(key, "") > current.get(key, ""):
            latest[num] = rec
    return latest