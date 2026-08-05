"""Thin wrapper around the OpenF1 REST API (https://openf1.org).

OpenF1 gives us near-real-time data during a live session (car positions,
gaps/intervals, tyre stints, weather, etc). It does not require an API key.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = os.getenv("BASE_URL")


import time

class OpenF1Client:
    """Small helper for calling OpenF1 endpoints with caching and rate-limit guard."""

    def __init__(self, base_url: str | None = None, timeout: int = 10):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/") + "/"
        self.timeout = timeout
        self._driver_cache = {}
        self._session_cache = None
        self._session_cache_time = 0

    def _get(self, endpoint: str, **params):
        url = f"{self.base_url}{endpoint}"
        clean_params = {k: v for k, v in params.items() if v is not None}
        try:
            response = requests.get(url, params=clean_params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            if response.status_code == 429:
                raise RuntimeError("API rate limit reached (HTTP 429). Retrying shortly...") from exc
            raise

    # -- Sessions -----------------------------------------------------
    def get_latest_session(self):
        """Return the most recent session with 60s cache TTL to prevent rate limits."""
        now = time.time()
        if self._session_cache and (now - self._session_cache_time < 60):
            return self._session_cache

        sessions = self._get("sessions", session_key="latest")
        if sessions:
            self._session_cache = sessions[0]
            self._session_cache_time = now
            return self._session_cache
        return None

    def get_sessions(self, year=None, meeting_key=None, country_name=None):
        return self._get(
            "sessions", year=year, meeting_key=meeting_key, country_name=country_name
        )

    # -- Session-scoped data ------------------------------------------
    def get_drivers(self, session_key="latest"):
        """Cache drivers list by session_key to avoid redundant network calls."""
        if session_key in self._driver_cache:
            return self._driver_cache[session_key]
        drivers = self._get("drivers", session_key=session_key)
        if drivers:
            self._driver_cache[session_key] = drivers
        return drivers


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