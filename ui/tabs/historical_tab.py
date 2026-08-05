"""Historical Analysis tab: loads a past session via FastF1 (in a background
thread) and shows results, fastest-lap telemetry, lap times, and driver comparison
using dark F1 motorsport themed widgets and Matplotlib plots."""

from PySide6.QtCore import QObject, Signal, QThread, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QMessageBox,
    QFrame,
    QGridLayout,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.historical import HistoricalSession
from ui.theme import apply_dark_matplotlib_theme, get_team_color, COLOR_PRIMARY_RED, COLOR_ACCENT_CYAN, COLOR_ACCENT_GREEN, COLOR_TEXT_MUTED


class _LoadWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, year, event_name, session_type):
        super().__init__()
        self.year = year
        self.event_name = event_name
        self.session_type = session_type

    def run(self):
        try:
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

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(0, 8, 0, 0)

        # Control Panel Box
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("cardPanel")
        ctrl_layout = QGridLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(16, 14, 16, 14)
        ctrl_layout.setSpacing(14)

        # Input 1: Year
        lbl_year = QLabel("SEASON YEAR")
        lbl_year.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.year_input = QLineEdit("2024")
        self.year_input.setMaximumWidth(100)
        
        # Input 2: Event Name
        lbl_event = QLabel("GRAND PRIX")
        lbl_event.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.event_input = QLineEdit("Brazil")
        self.event_input.setPlaceholderText("Grand Prix name (e.g. 'Brazil', 'Monza', 'Silverstone')")

        # Input 3: Session
        lbl_session = QLabel("SESSION")
        lbl_session.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.session_combo = QComboBox()
        self.session_combo.addItems(self.SESSION_TYPES)
        self.session_combo.setCurrentText("R")
        self.session_combo.setMaximumWidth(120)

        # Action Button
        self.load_button = QPushButton("🚀 Load Session Data")
        self.load_button.clicked.connect(self.load_session)

        # Add to Grid
        ctrl_layout.addWidget(lbl_year, 0, 0)
        ctrl_layout.addWidget(self.year_input, 1, 0)
        
        ctrl_layout.addWidget(lbl_event, 0, 1)
        ctrl_layout.addWidget(self.event_input, 1, 1)

        ctrl_layout.addWidget(lbl_session, 0, 2)
        ctrl_layout.addWidget(self.session_combo, 1, 2)

        ctrl_layout.addWidget(self.load_button, 1, 3)

        main_layout.addWidget(ctrl_frame)

        # Status Label
        self.status_banner = QFrame()
        self.status_banner.setObjectName("cardPanel")
        banner_layout = QHBoxLayout(self.status_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        
        self.status_icon = QLabel("ℹ")
        self.status_icon.setStyleSheet("color: #00E5FF; font-size: 14px; font-weight: bold;")
        self.status_label = QLabel(
            "Select season, Grand Prix event, and session type above, then click 'Load Session Data'."
        )
        self.status_label.setStyleSheet("color: #8E94A5; font-size: 12px;")
        banner_layout.addWidget(self.status_icon)
        banner_layout.addWidget(self.status_label, 1)
        main_layout.addWidget(self.status_banner)

        # Sub Tabs Widget
        self.sub_tabs = QTabWidget()
        main_layout.addWidget(self.sub_tabs)

        # Tab 1: Classification Results Table
        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(["POS", "DRIVER", "TEAM", "GRID", "STATUS", "POINTS"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setShowGrid(False)
        self.sub_tabs.addTab(self.results_table, "🏁 Race Classification")

        # Tab 2: Fastest Lap Telemetry
        self.telemetry_figure = Figure(figsize=(6, 4))
        self.telemetry_canvas = FigureCanvasQTAgg(self.telemetry_figure)
        apply_dark_matplotlib_theme(self.telemetry_figure)
        self.sub_tabs.addTab(self.telemetry_canvas, "⚡ Fastest Lap Telemetry")

        # Tab 3: Lap Times Distribution
        self.laptime_figure = Figure(figsize=(6, 4))
        self.laptime_canvas = FigureCanvasQTAgg(self.laptime_figure)
        apply_dark_matplotlib_theme(self.laptime_figure)
        self.sub_tabs.addTab(self.laptime_canvas, "⏱ Lap Times Analysis")

        # Tab 4: Driver vs Driver Telemetry Comparison
        compare_widget = QWidget()
        compare_layout = QVBoxLayout(compare_widget)
        compare_layout.setContentsMargins(12, 12, 12, 12)
        compare_layout.setSpacing(10)
        
        selectors_frame = QFrame()
        selectors_frame.setObjectName("cardPanel")
        selectors_layout = QHBoxLayout(selectors_frame)
        selectors_layout.setContentsMargins(12, 8, 12, 8)
        
        lbl_d1 = QLabel("Driver 1:")
        lbl_d1.setStyleSheet("color: #00E5FF; font-weight: bold;")
        self.driver1_combo = QComboBox()
        
        lbl_d2 = QLabel("Driver 2:")
        lbl_d2.setStyleSheet("color: #FF8000; font-weight: bold;")
        self.driver2_combo = QComboBox()
        
        self.compare_btn = QPushButton("⚔ Compare Telemetry")
        self.compare_btn.setObjectName("secondaryBtn")
        self.compare_btn.clicked.connect(self._plot_driver_comparison)
        
        selectors_layout.addWidget(lbl_d1)
        selectors_layout.addWidget(self.driver1_combo, 1)
        selectors_layout.addSpacing(16)
        selectors_layout.addWidget(lbl_d2)
        selectors_layout.addWidget(self.driver2_combo, 1)
        selectors_layout.addSpacing(16)
        selectors_layout.addWidget(self.compare_btn)
        
        compare_layout.addWidget(selectors_frame)

        self.compare_figure = Figure(figsize=(6, 5))
        self.compare_canvas = FigureCanvasQTAgg(self.compare_figure)
        apply_dark_matplotlib_theme(self.compare_figure)
        compare_layout.addWidget(self.compare_canvas)
        
        self.sub_tabs.addTab(compare_widget, "⚔ Driver vs Driver Comparison")

    def load_session(self):
        try:
            year = int(self.year_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Year", "Please enter a valid numeric year (e.g. 2024).")
            return
        event = self.event_input.text().strip()
        if not event:
            QMessageBox.warning(self, "Missing Grand Prix", "Please enter a Grand Prix event name.")
            return
        session_type = self.session_combo.currentText()

        self.status_label.setText("Loading session from FastF1 cache/server... Please wait.")
        self.status_icon.setText("⏳")
        self.status_icon.setStyleSheet("color: #FFC107; font-size: 14px; font-weight: bold;")
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
        self.status_label.setText(f"Error loading session: {message}")
        self.status_icon.setText("❌")
        self.status_icon.setStyleSheet(f"color: {COLOR_PRIMARY_RED}; font-size: 14px; font-weight: bold;")
        self.load_button.setEnabled(True)

    def _on_loaded(self, hs: HistoricalSession):
        self.hs = hs
        self.load_button.setEnabled(True)
        event_name = hs.session.event.get("EventName", hs.event)
        self.status_label.setText(f"Loaded: {event_name} ({hs.year}) — {hs.session.name}")
        self.status_icon.setText("✔")
        self.status_icon.setStyleSheet(f"color: {COLOR_ACCENT_GREEN}; font-size: 14px; font-weight: bold;")

        self._populate_results()
        self._populate_drivers()
        self._plot_telemetry()
        self._plot_lap_times()
        self._plot_driver_comparison()

    def _populate_results(self):
        df = self.hs.results_table().reset_index(drop=True)
        self.results_table.setRowCount(len(df))
        for i, row in df.iterrows():
            pos_val = str(row.get("Position", "-"))
            try:
                pos_int = int(float(pos_val))
            except ValueError:
                pos_int = 999

            driver_abbr = str(row.get("Abbreviation", "-"))
            team_name = str(row.get("TeamName", "-"))
            grid_pos = str(row.get("GridPosition", "-"))
            status = str(row.get("Status", "-"))
            points = str(row.get("Points", "0.0"))

            font = QFont()
            font.setBold(True)

            pos_item = QTableWidgetItem(pos_val)
            pos_item.setTextAlignment(Qt.AlignCenter)
            pos_item.setFont(font)
            if pos_int == 1:
                pos_item.setForeground(QColor("#FFD700"))
            elif pos_int == 2:
                pos_item.setForeground(QColor("#C0C0C0"))
            elif pos_int == 3:
                pos_item.setForeground(QColor("#CD7F32"))

            drv_item = QTableWidgetItem(driver_abbr)
            drv_item.setFont(font)

            team_item = QTableWidgetItem(team_name)
            team_item.setForeground(QColor(get_team_color(team_name)))

            grid_item = QTableWidgetItem(grid_pos)
            grid_item.setTextAlignment(Qt.AlignCenter)

            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)

            pts_item = QTableWidgetItem(points)
            pts_item.setTextAlignment(Qt.AlignCenter)
            pts_item.setFont(font)

            self.results_table.setItem(i, 0, pos_item)
            self.results_table.setItem(i, 1, drv_item)
            self.results_table.setItem(i, 2, team_item)
            self.results_table.setItem(i, 3, grid_item)
            self.results_table.setItem(i, 4, status_item)
            self.results_table.setItem(i, 5, pts_item)

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
            self.status_label.setText(f"Loaded session, but telemetry processing failed: {exc}")
            return
        
        self.telemetry_figure.clear()
        ax = self.telemetry_figure.add_subplot(111)
        
        # Plot Speed
        ax.plot(tel["Distance"], tel["Speed"], color="#00E5FF", linewidth=1.8, label="Speed (km/h)")
        ax.fill_between(tel["Distance"], tel["Speed"], color="#00E5FF", alpha=0.08)
        
        ax.set_xlabel("Distance (meters)")
        ax.set_ylabel("Speed (km/h)")
        ax.set_title(f"Outright Fastest Lap: {fastest['Driver']} ({fastest['LapTime']})")
        
        apply_dark_matplotlib_theme(self.telemetry_figure, [ax])
        self.telemetry_figure.tight_layout()
        self.telemetry_canvas.draw()

    def _plot_lap_times(self):
        laps = self.hs.session.laps
        self.laptime_figure.clear()
        ax = self.laptime_figure.add_subplot(111)
        
        for drv in laps["Driver"].unique():
            drv_laps = laps.pick_drivers(drv) if hasattr(laps, "pick_drivers") else laps.pick_driver(drv)
            times = drv_laps["LapTime"].dt.total_seconds()
            ax.plot(drv_laps["LapNumber"], times, label=drv, alpha=0.7, linewidth=1.2)

        ax.set_xlabel("Lap Number")
        ax.set_ylabel("Lap Time (seconds)")
        ax.set_title("Driver Lap Time Distribution & Degradation")
        ax.legend(fontsize=7, ncol=5, loc="upper right")
        
        apply_dark_matplotlib_theme(self.laptime_figure, [ax])
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

        # Plot Speed comparison
        axs[0].plot(tel1["Distance"], tel1["Speed"], label=f"{d1} Speed", color="#00E5FF", linewidth=1.8)
        axs[0].plot(tel2["Distance"], tel2["Speed"], label=f"{d2} Speed", color="#FF8000", linewidth=1.8)
        axs[0].set_ylabel("Speed (km/h)")
        axs[0].set_title(f"Telemetry Overlay: {d1} vs {d2} (Fastest Laps)")
        axs[0].legend(loc="lower right", fontsize=8)

        # Plot Throttle comparison
        if "Throttle" in tel1.columns and "Throttle" in tel2.columns:
            axs[1].plot(tel1["Distance"], tel1["Throttle"], label=f"{d1} Throttle", color="#00E5FF", alpha=0.85, linewidth=1.5)
            axs[1].plot(tel2["Distance"], tel2["Throttle"], label=f"{d2} Throttle", color="#FF8000", alpha=0.85, linewidth=1.5)
        axs[1].set_xlabel("Distance (meters)")
        axs[1].set_ylabel("Throttle (%)")
        axs[1].legend(loc="lower right", fontsize=8)

        apply_dark_matplotlib_theme(self.compare_figure, list(axs))
        self.compare_figure.tight_layout()
        self.compare_canvas.draw()