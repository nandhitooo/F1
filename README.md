# F1 Live Tracker & Analysis

A desktop app (PySide6/Qt) with two tabs:

- **Live** — polls the [OpenF1](https://openf1.org) API every 5 seconds for
  position, gap-to-leader, interval, and current tyre compound for whichever
  session is live or most recently finished. No API key needed.
- **Historical Analysis** — uses [FastF1](https://docs.fastf1.dev) to load
  any past session (year + Grand Prix name + session type) and shows the
  results table, the fastest lap's speed telemetry, and a lap-time
  comparison chart across all drivers.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Project layout

```
f1_tracker/
├── main.py                     # entry point — run this
├── core/                       # data & logic, no UI code here
│   ├── openf1_client.py         # OpenF1 REST API wrapper (live data)
│   └── historical.py             # FastF1 wrapper (historical sessions)
├── ui/                          # everything Qt-related
│   ├── main_window.py            # QMainWindow hosting the tabs
│   └── tabs/
│       ├── live_tab.py            # Live leaderboard tab
│       └── historical_tab.py      # Historical results/telemetry/lap-time tab
├── assets/                      # icons/images, empty for now
├── requirements.txt
├── .env                          # OpenF1 base URL (already set, no key required)
└── cache_folder/                 # FastF1 disk cache (auto-created, gitignored)
```

`core/` holds anything that talks to an API or crunches data; `ui/` holds
anything that draws a widget. Neither `ui/tabs/*` file imports from another
tab, and `core/*` never imports from `ui/` — data flows one way, UI → core.

## Notes

- **Live tab**: OpenF1 only has real-time data while a session is actually
  running (practice/quali/race weekend). Outside of that it shows the most
  recent completed session's final data. The polling runs in a background
  thread pool so the UI never freezes waiting on the network.
- **Historical tab**: the first time you load a given session, FastF1
  downloads and caches the timing/telemetry data — this can take from a few
  seconds up to ~1 minute depending on the session. Every load after that is
  near-instant, pulled from `cache_folder/`.
- Grand Prix names for the Historical tab are matched loosely, e.g. `"Brazil"`,
  `"Monza"`, `"Silverstone"`, `"Japan"` all work with FastF1's `get_session`.
- If you ever see network errors, double-check you have internet access to
  `api.openf1.org` (for Live) and FastF1's data source (for Historical) — no
  API keys are required for either.

## Possible next steps

- Add a track map overlay for the live tab using OpenF1's `/location` endpoint.
- Add driver-vs-driver telemetry comparison (speed/throttle/brake overlay) in
  the Historical tab.
- Push desktop notifications on race control messages (flags, safety car) via
  OpenF1's `/race_control` endpoint.
