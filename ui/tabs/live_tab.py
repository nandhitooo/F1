"""Live tab: polls OpenF1 in a background thread and renders a leaderboard
(position, gap, interval, current tyre) that refreshes on a timer."""

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QCheckBox,
    QHeaderView,
)

from core.openf1_client import OpenF1Client, latest_by_driver


class _FetchSignals(QObject):
    finished = Signal(dict)
    error = Signal(str)


class _FetchTask(QRunnable):
    """Runs the OpenF1 calls off the UI thread so the window never freezes
    while waiting on the network."""

    def __init__(self, client: OpenF1Client):
        super().__init__()
        self.client = client
        self.signals = _FetchSignals()

    def run(self):
        try:
            session = self.client.get_latest_session()
            if not session:
                self.signals.error.emit("No live or recent session found.")
                return
            session_key = session["session_key"]
            payload = {
                "session": session,
                "drivers": self.client.get_drivers(session_key),
                "positions": self.client.get_positions(session_key),
                "intervals": self.client.get_intervals(session_key),
                "stints": self.client.get_stints(session_key),
            }
            self.signals.finished.emit(payload)
        except Exception as exc:  # network hiccups shouldn't crash the app
            self.signals.error.emit(str(exc))


class LiveTab(QWidget):
    COLUMNS = ["Pos", "Driver", "Team", "Gap to leader", "Interval", "Tyre", "Stint lap"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = OpenF1Client()
        self.pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.status_label = QLabel("Connecting...")
        self.refresh_button = QPushButton("Refresh now")
        self.refresh_button.clicked.connect(self.refresh)
        self.auto_checkbox = QCheckBox("Auto-refresh every 5s")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.stateChanged.connect(self._toggle_auto_refresh)
        header.addWidget(self.status_label, 1)
        header.addWidget(self.auto_checkbox)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        note = QLabel(
            "Note: OpenF1 only streams live data while a session is actually "
            "running. Outside of sessions it falls back to the most recent one."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(note)

        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

        self.refresh()

    def _toggle_auto_refresh(self, state):
        # PySide6 emits 0 (unchecked) or 2 (checked) here - a simple
        # truthy check covers both.
        if state:
            self.timer.start()
        else:
            self.timer.stop()

    def refresh(self):
        self.status_label.setText("Refreshing...")
        task = _FetchTask(self.client)
        task.signals.finished.connect(self._on_data)
        task.signals.error.connect(self._on_error)
        self.pool.start(task)

    def _on_error(self, message):
        self.status_label.setText(f"Error: {message}")

    def _on_data(self, data):
        session = data["session"]
        drivers = {d["driver_number"]: d for d in data["drivers"]}
        positions = latest_by_driver(data["positions"])
        intervals = latest_by_driver(data["intervals"])

        # Stints are listed chronologically, so the last entry per driver is
        # the one currently on the car.
        stints = {}
        for rec in data["stints"]:
            num = rec.get("driver_number")
            if num is not None:
                stints[num] = rec

        rows = sorted(positions.values(), key=lambda r: r.get("position") or 999)

        self.table.setRowCount(len(rows))
        for i, pos_rec in enumerate(rows):
            num = pos_rec.get("driver_number")
            driver = drivers.get(num, {})
            interval = intervals.get(num, {})
            stint = stints.get(num, {})

            gap = interval.get("gap_to_leader")
            gap_str = f"{gap:.3f}s" if isinstance(gap, (int, float)) else "-"
            iv = interval.get("interval")
            iv_str = f"{iv:.3f}s" if isinstance(iv, (int, float)) else "-"

            values = [
                str(pos_rec.get("position", "-")),
                driver.get("full_name") or driver.get("name_acronym") or str(num),
                driver.get("team_name", "-"),
                gap_str,
                iv_str,
                stint.get("compound", "-"),
                str(stint.get("lap_end") or stint.get("lap_start") or "-"),
            ]
            for col, val in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(val))

        name = session.get("session_name") or session.get("session_type", "")
        circuit = session.get("circuit_short_name", "-")
        self.status_label.setText(f"Session: {name}  |  Circuit: {circuit}  |  Last updated ✓")