"""Historical Analysis tab: loads a past session via FastF1 (in a background
thread, since the first load per session can take a while) and shows
results, fastest-lap telemetry, and a lap-time comparison chart."""

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QMessageBox,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.historical import HistoricalSession


class _LoadWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, year, event, session_type):
        super().__init__()
        self.year = year
        self.event = event
        self.session_type = session_type

    def run(self):
        try:
            hs = HistoricalSession(self.year, self.event, self.session_type)
            hs.load()
            self.finished.emit(hs)
        except Exception as exc:
            self.error.emit(str(exc))


class HistoricalTab(QWidget):
    SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "S", "R"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self.hs = None

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.year_input = QLineEdit("2024")
        self.event_input = QLineEdit("Brazil")
        self.event_input.setPlaceholderText("Grand Prix name, e.g. 'Brazil' or 'Monza'")
        self.session_combo = QComboBox()
        self.session_combo.addItems(self.SESSION_TYPES)
        self.session_combo.setCurrentText("R")
        self.load_button = QPushButton("Load session")
        self.load_button.clicked.connect(self.load_session)

        form.addRow("Year", self.year_input)
        form.addRow("Grand Prix", self.event_input)
        form.addRow("Session", self.session_combo)
        layout.addLayout(form)
        layout.addWidget(self.load_button)

        self.status_label = QLabel(
            "No session loaded yet. First load of a session downloads data "
            "and can take up to a minute; it's cached after that."
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.sub_tabs = QTabWidget()
        layout.addWidget(self.sub_tabs)

        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Pos", "Driver", "Team", "Grid", "Status"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sub_tabs.addTab(self.results_table, "Results")

        self.telemetry_figure = Figure(figsize=(6, 4))
        self.telemetry_canvas = FigureCanvasQTAgg(self.telemetry_figure)
        self.sub_tabs.addTab(self.telemetry_canvas, "Fastest Lap Telemetry")

        self.laptime_figure = Figure(figsize=(6, 4))
        self.laptime_canvas = FigureCanvasQTAgg(self.laptime_figure)
        self.sub_tabs.addTab(self.laptime_canvas, "Lap Times")

    def load_session(self):
        try:
            year = int(self.year_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid year", "Please enter a numeric year, e.g. 2024.")
            return
        event = self.event_input.text().strip()
        if not event:
            QMessageBox.warning(self, "Missing Grand Prix", "Please enter a Grand Prix name.")
            return
        session_type = self.session_combo.currentText()

        self.status_label.setText("Loading session (this can take a while the first time)...")
        self.load_button.setEnabled(False)

        self._thread = QThread()
        self._worker = _LoadWorker(year, event, session_type)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_error(self, message):
        self.status_label.setText(f"Error: {message}")
        self.load_button.setEnabled(True)

    def _on_loaded(self, hs: HistoricalSession):
        self.hs = hs
        self.load_button.setEnabled(True)
        event_name = hs.session.event.get("EventName", hs.event)
        self.status_label.setText(f"Loaded: {event_name} — {hs.session.name}")
        self._populate_results()
        self._plot_telemetry()
        self._plot_lap_times()

    def _populate_results(self):
        df = self.hs.results_table().reset_index(drop=True)
        self.results_table.setRowCount(len(df))
        for i, row in df.iterrows():
            values = [
                str(row.get("Position", "-")),
                str(row.get("Abbreviation", "-")),
                str(row.get("TeamName", "-")),
                str(row.get("GridPosition", "-")),
                str(row.get("Status", "-")),
            ]
            for col, val in enumerate(values):
                self.results_table.setItem(i, col, QTableWidgetItem(val))

    def _plot_telemetry(self):
        try:
            fastest, tel = self.hs.fastest_lap_telemetry()
        except Exception as exc:
            self.status_label.setText(f"Loaded, but telemetry failed: {exc}")
            return
        self.telemetry_figure.clear()
        ax = self.telemetry_figure.add_subplot(111)
        ax.plot(tel["Distance"], tel["Speed"])
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Speed (km/h)")
        ax.set_title(f"Fastest lap: {fastest['Driver']} ({fastest['LapTime']})")
        self.telemetry_figure.tight_layout()
        self.telemetry_canvas.draw()

    def _plot_lap_times(self):
        laps = self.hs.session.laps
        self.laptime_figure.clear()
        ax = self.laptime_figure.add_subplot(111)
        for drv in laps["Driver"].unique():
            drv_laps = laps.pick_drivers(drv) if hasattr(laps, "pick_drivers") else laps.pick_driver(drv)
            times = drv_laps["LapTime"].dt.total_seconds()
            ax.plot(drv_laps["LapNumber"], times, label=drv, alpha=0.6, linewidth=1)
        ax.set_xlabel("Lap")
        ax.set_ylabel("Lap time (s)")
        ax.set_title("Lap times by driver")
        ax.legend(fontsize=6, ncol=4, loc="upper right")
        self.laptime_figure.tight_layout()
        self.laptime_canvas.draw()