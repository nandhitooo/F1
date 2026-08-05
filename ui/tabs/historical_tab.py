"""Historical Analysis tab: loads a past session via FastF1 (in a background
thread) and shows results, fastest-lap telemetry, lap times, and driver comparison."""

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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

    # Ubah parameter 'event' menjadi 'event_name' untuk menghindari konflik
    def __init__(self, year, event_name, session_type):
        super().__init__()
        self.year = year
        self.event_name = event_name
        self.session_type = session_type

    def run(self):
        try:
            # Gunakan self.event_name di sini
            hs = HistoricalSession(self.year, self.event_name, self.session_type)
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

        # Tab 1: Results
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Pos", "Driver", "Team", "Grid", "Status"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sub_tabs.addTab(self.results_table, "Results")

        # Tab 2: Fastest Lap Telemetry
        self.telemetry_figure = Figure(figsize=(6, 4))
        self.telemetry_canvas = FigureCanvasQTAgg(self.telemetry_figure)
        self.sub_tabs.addTab(self.telemetry_canvas, "Fastest Lap Telemetry")

        # Tab 3: Lap Times
        self.laptime_figure = Figure(figsize=(6, 4))
        self.laptime_canvas = FigureCanvasQTAgg(self.laptime_figure)
        self.sub_tabs.addTab(self.laptime_canvas, "Lap Times")

        # Tab 4: Driver vs Driver Telemetry Comparison
        compare_widget = QWidget()
        compare_layout = QVBoxLayout(compare_widget)
        
        selectors_layout = QHBoxLayout()
        self.driver1_combo = QComboBox()
        self.driver2_combo = QComboBox()
        self.compare_btn = QPushButton("Compare Telemetry")
        self.compare_btn.clicked.connect(self._plot_driver_comparison)
        
        selectors_layout.addWidget(QLabel("Driver 1:"))
        selectors_layout.addWidget(self.driver1_combo)
        selectors_layout.addWidget(QLabel("Driver 2:"))
        selectors_layout.addWidget(self.driver2_combo)
        selectors_layout.addWidget(self.compare_btn)
        
        compare_layout.addLayout(selectors_layout)

        self.compare_figure = Figure(figsize=(6, 5))
        self.compare_canvas = FigureCanvasQTAgg(self.compare_figure)
        compare_layout.addWidget(self.compare_canvas)
        
        self.sub_tabs.addTab(compare_widget, "Driver vs Driver")

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
        self._populate_drivers()
        self._plot_telemetry()
        self._plot_lap_times()
        self._plot_driver_comparison()

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

    def _populate_drivers(self):
        drivers = sorted(self.hs.session.laps["Driver"].dropna().unique().tolist())
        self.driver1_combo.clear()
        self.driver2_combo.clear()
        self.driver1_combo.addItems(drivers)
        self.driver2_combo.addItems(drivers)
        if len(drivers) >= 2:
            self.driver1_combo.setCurrentIndex(0)
            self.driver2_combo.setCurrentIndex(1)

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

    def _plot_driver_comparison(self):
        if not self.hs or not self.hs.session:
            return
        d1 = self.driver1_combo.currentText()
        d2 = self.driver2_combo.currentText()
        if not d1 or not d2:
            return

        try:
            _, tel1 = self.hs.driver_telemetry(d1)
            _, tel2 = self.hs.driver_telemetry(d2)
        except Exception as exc:
            QMessageBox.warning(self, "Telemetry Error", str(exc))
            return

        self.compare_figure.clear()
        axs = self.compare_figure.subplots(2, 1, sharex=True)

        # Plot Speed
        axs[0].plot(tel1["Distance"], tel1["Speed"], label=d1, color="tab:blue")
        axs[0].plot(tel2["Distance"], tel2["Speed"], label=d2, color="tab:orange")
        axs[0].set_ylabel("Speed (km/h)")
        axs[0].set_title(f"Telemetry Comparison: {d1} vs {d2} (Fastest Laps)")
        axs[0].legend(loc="lower right", fontsize=8)
        axs[0].grid(True, alpha=0.3)

        # Plot Throttle
        if "Throttle" in tel1.columns and "Throttle" in tel2.columns:
            axs[1].plot(tel1["Distance"], tel1["Throttle"], label=f"{d1} Throttle", color="tab:blue", alpha=0.8)
            axs[1].plot(tel2["Distance"], tel2["Throttle"], label=f"{d2} Throttle", color="tab:orange", alpha=0.8)
        axs[1].set_xlabel("Distance (m)")
        axs[1].set_ylabel("Throttle (%)")
        axs[1].legend(loc="lower right", fontsize=8)
        axs[1].grid(True, alpha=0.3)

        self.compare_figure.tight_layout()
        self.compare_canvas.draw()