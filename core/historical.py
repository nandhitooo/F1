"""Historical / post-session analysis powered by FastF1.

FastF1 pulls detailed timing + telemetry data for past sessions (practice,
qualifying, sprint, race) going back several years. Results are cached to
disk so repeat loads are fast.
"""

import os
import fastf1
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache_folder")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


class HistoricalSession:
    """Loads a single FastF1 session and exposes convenience views over it."""

    def __init__(self, year: int, event: str, session_type: str):
        self.year = year
        self.event = event
        self.session_type = session_type
        self.session = None

    def load(self):
        self.session = fastf1.get_session(self.year, self.event, self.session_type)
        self.session.load()
        return self.session

    def results_table(self) -> pd.DataFrame:
        """Position / grid / status table for the session."""
        if self.session is None:
            raise RuntimeError("Call load() first.")
        results = self.session.results
        wanted = ["Position", "Abbreviation", "TeamName", "GridPosition", "Status", "Points"]
        cols = [c for c in wanted if c in results.columns]
        return results[cols].copy()

    def fastest_lap_telemetry(self):
        """Returns (fastest_lap_row, telemetry_dataframe) for the outright
        fastest lap of the session."""
        if self.session is None:
            raise RuntimeError("Call load() first.")
        fastest = self.session.laps.pick_fastest()
        tel = fastest.get_telemetry()
        cols = [c for c in ["Distance", "Speed", "Throttle", "Brake", "nGear"] if c in tel.columns]
        return fastest, tel[cols].copy()

    def lap_times(self, driver_abbr: str | None = None) -> pd.DataFrame:
        """Lap-by-lap times, optionally filtered to a single driver
        (3-letter abbreviation, e.g. 'VER')."""
        if self.session is None:
            raise RuntimeError("Call load() first.")
        laps = self.session.laps
        if driver_abbr:
            laps = laps.pick_drivers(driver_abbr) if hasattr(laps, "pick_drivers") else laps.pick_driver(driver_abbr)
        cols = [c for c in ["Driver", "LapNumber", "LapTime", "Compound"] if c in laps.columns]
        return laps[cols].copy()

# Tambahkan method berikut di dalam kelas HistoricalSession (core/historical.py)

    def driver_telemetry(self, driver_abbr: str):
        """Returns (lap_row, telemetry_dataframe) for a driver's fastest lap."""
        if self.session is None:
            raise RuntimeError("Call load() first.")
        laps = self.session.laps
        drv_laps = laps.pick_drivers(driver_abbr) if hasattr(laps, "pick_drivers") else laps.pick_driver(driver_abbr)
        if drv_laps.empty:
            raise ValueError(f"No laps found for driver {driver_abbr}")
        fastest = drv_laps.pick_fastest()
        tel = fastest.get_telemetry()
        cols = [c for c in ["Distance", "Speed", "Throttle", "Brake", "nGear"] if c in tel.columns]
        return fastest, tel[cols].copy()