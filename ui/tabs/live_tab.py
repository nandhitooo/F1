"""Live tab: polls OpenF1 in a background thread and renders a leaderboard
(position, gap, interval, current tyre) with high-tech F1 UI cards and compound badges.
"""

from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QColor, QFont
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
    QFrame,
    QGridLayout,
)

from core.openf1_client import OpenF1Client, latest_by_driver
from ui.theme import TYRE_COLORS, get_team_color, COLOR_PRIMARY_RED, COLOR_TEXT_MUTED, COLOR_ACCENT_GREEN, COLOR_ACCENT_CYAN, COLOR_PANEL_BG, COLOR_BORDER


class _FetchThread(QThread):
    """Runs OpenF1 API network calls on a background QThread to keep the UI perfectly responsive."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, client: OpenF1Client, parent=None):
        super().__init__(parent)
        self.client = client

    def run(self):
        try:
            session = self.client.get_latest_session()
            if not session:
                self.error.emit("No live or recent session found.")
                return
            session_key = session["session_key"]
            payload = {
                "session": session,
                "drivers": self.client.get_drivers(session_key),
                "positions": self.client.get_positions(session_key),
                "intervals": self.client.get_intervals(session_key),
                "stints": self.client.get_stints(session_key),
            }
            self.finished.emit(payload)
        except Exception as exc:
            self.error.emit(str(exc))


class LiveTab(QWidget):
    COLUMNS = ["POS", "DRIVER", "TEAM", "GAP TO LEADER", "INTERVAL", "TYRE", "STINT LAP"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = OpenF1Client()
        self._fetch_thread = None

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(0, 8, 0, 0)

        # KPI Header Cards Frame
        kpi_frame = QFrame()
        kpi_frame.setObjectName("cardPanel")
        kpi_layout = QGridLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 12, 16, 12)
        kpi_layout.setSpacing(16)

        # Card 1: Session
        session_box = QVBoxLayout()
        lbl1 = QLabel("ACTIVE SESSION")
        lbl1.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.val_session = QLabel("Connecting...")
        self.val_session.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold;")
        session_box.addWidget(lbl1)
        session_box.addWidget(self.val_session)
        kpi_layout.addLayout(session_box, 0, 0)

        # Card 2: Circuit
        circuit_box = QVBoxLayout()
        lbl2 = QLabel("CIRCUIT")
        lbl2.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.val_circuit = QLabel("-")
        self.val_circuit.setStyleSheet("color: #00E5FF; font-size: 15px; font-weight: bold;")
        circuit_box.addWidget(lbl2)
        circuit_box.addWidget(self.val_circuit)
        kpi_layout.addLayout(circuit_box, 0, 1)

        # Card 3: Live Status Indicator
        status_box = QVBoxLayout()
        lbl3 = QLabel("STATUS")
        lbl3.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.val_status = QLabel("● INITIALIZING")
        self.val_status.setStyleSheet("color: #FFC107; font-size: 13px; font-weight: bold;")
        status_box.addWidget(lbl3)
        status_box.addWidget(self.val_status)
        kpi_layout.addLayout(status_box, 0, 2)

        # Card 4: Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)
        self.auto_checkbox = QCheckBox("Auto-refresh (5s)")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.stateChanged.connect(self._toggle_auto_refresh)

        self.refresh_button = QPushButton("↻ Refresh Now")
        self.refresh_button.clicked.connect(self.refresh)

        ctrl_layout.addWidget(self.auto_checkbox)
        ctrl_layout.addWidget(self.refresh_button)
        kpi_layout.addLayout(ctrl_layout, 0, 3, Qt.AlignRight | Qt.AlignVCenter)

        main_layout.addWidget(kpi_frame)

        # Table Widget
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        main_layout.addWidget(self.table)

        # Bottom Info Banner
        note_frame = QFrame()
        note_frame.setObjectName("cardPanel")
        note_layout = QHBoxLayout(note_frame)
        note_layout.setContentsMargins(12, 8, 12, 8)
        
        info_icon = QLabel("ℹ")
        info_icon.setStyleSheet("color: #00E5FF; font-size: 14px; font-weight: bold;")
        note = QLabel(
            "OpenF1 streams telemetry data during live sessions. "
            "Outside of active session windows, data automatically defaults to the most recent official GP event."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8E94A5; font-size: 11px;")
        
        note_layout.addWidget(info_icon)
        note_layout.addWidget(note, 1)
        main_layout.addWidget(note_frame)

        # Timer setup (10s interval to prevent rate-limiting)
        self.timer = QTimer(self)
        self.timer.setInterval(10000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

        self.refresh()

    def _toggle_auto_refresh(self, state):
        if state:
            self.timer.start()
        else:
            self.timer.stop()

    def refresh(self):
        if self._fetch_thread is not None:
            try:
                if self._fetch_thread.isRunning():
                    return
            except RuntimeError:
                self._fetch_thread = None

        self.val_status.setText("● REFRESHING...")
        self.val_status.setStyleSheet("color: #FFC107; font-size: 13px; font-weight: bold;")
        self.refresh_button.setEnabled(False)

        thread = _FetchThread(self.client, parent=self)
        self._fetch_thread = thread

        def _clear_ref():
            if self._fetch_thread == thread:
                self._fetch_thread = None

        thread.finished.connect(self._on_data)
        thread.finished.connect(_clear_ref)
        thread.error.connect(self._on_error)
        thread.error.connect(_clear_ref)
        thread.start()



    def _on_error(self, message):
        self.val_status.setText("● ERROR")
        self.val_status.setStyleSheet(f"color: {COLOR_PRIMARY_RED}; font-size: 13px; font-weight: bold;")
        self.val_session.setText("Connection Failed")
        self.refresh_button.setEnabled(True)

    def _on_data(self, data):
        self.refresh_button.setEnabled(True)
        session = data["session"]
        drivers = {d["driver_number"]: d for d in data["drivers"]}
        positions = latest_by_driver(data["positions"])
        intervals = latest_by_driver(data["intervals"])

        stints = {}
        for rec in data["stints"]:
            num = rec.get("driver_number")
            if num is not None:
                stints[num] = rec

        rows = sorted(positions.values(), key=lambda r: r.get("position") or 999)

        self.table.setRowCount(len(rows))
        for i, pos_rec in enumerate(rows):
            pos_val = pos_rec.get("position", "-")
            num = pos_rec.get("driver_number")
            driver = drivers.get(num, {})
            interval = intervals.get(num, {})
            stint = stints.get(num, {})

            driver_name = driver.get("full_name") or driver.get("name_acronym") or str(num)
            if driver.get("name_acronym"):
                driver_display = f"{driver.get('name_acronym')}  #{num}"
            else:
                driver_display = f"{driver_name}  #{num}"

            team_name = driver.get("team_name", "-")

            gap = interval.get("gap_to_leader")
            if isinstance(gap, (int, float)):
                gap_str = "LEADER" if gap == 0 else f"+{gap:.3f}s"
            else:
                gap_str = "-"

            iv = interval.get("interval")
            iv_str = f"+{iv:.3f}s" if isinstance(iv, (int, float)) and iv != 0 else ("-" if gap_str == "LEADER" else "-")

            compound_raw = str(stint.get("compound", "-")).upper()
            stint_lap = str(stint.get("lap_start") or "-")

            # 1. Position Item
            pos_item = QTableWidgetItem(str(pos_val))
            pos_item.setTextAlignment(Qt.AlignCenter)
            font = QFont()
            font.setBold(True)
            pos_item.setFont(font)

            if pos_val == 1:
                pos_item.setForeground(QColor("#FFD700")) # Gold
            elif pos_val == 2:
                pos_item.setForeground(QColor("#C0C0C0")) # Silver
            elif pos_val == 3:
                pos_item.setForeground(QColor("#CD7F32")) # Bronze

            # 2. Driver Item
            drv_item = QTableWidgetItem(driver_display)
            drv_item.setFont(font)

            # 3. Team Item
            team_item = QTableWidgetItem(team_name)
            team_color = get_team_color(team_name)
            team_item.setForeground(QColor(team_color))

            # 4. Gap Item
            gap_item = QTableWidgetItem(gap_str)
            gap_item.setTextAlignment(Qt.AlignCenter)

            # 5. Interval Item
            iv_item = QTableWidgetItem(iv_str)
            iv_item.setTextAlignment(Qt.AlignCenter)

            # 6. Tyre Compound Item
            tyre_item = QTableWidgetItem(compound_raw)
            tyre_item.setTextAlignment(Qt.AlignCenter)
            tyre_item.setFont(font)
            
            if compound_raw in TYRE_COLORS:
                cfg = TYRE_COLORS[compound_raw]
                tyre_item.setBackground(QColor(cfg["bg"]))
                tyre_item.setForeground(QColor(cfg["fg"]))
                tyre_item.setText(cfg["label"])

            # 7. Stint Lap Item
            stint_item = QTableWidgetItem(stint_lap)
            stint_item.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(i, 0, pos_item)
            self.table.setItem(i, 1, drv_item)
            self.table.setItem(i, 2, team_item)
            self.table.setItem(i, 3, gap_item)
            self.table.setItem(i, 4, iv_item)
            self.table.setItem(i, 5, tyre_item)
            self.table.setItem(i, 6, stint_item)

        # Update KPI Header Labels
        name = session.get("session_name") or session.get("session_type", "Active Session")
        circuit = session.get("circuit_short_name", "Grand Prix Circuit")
        self.val_session.setText(name)
        self.val_circuit.setText(circuit.upper())
        self.val_status.setText("● LIVE DATA ACTIVE")
        self.val_status.setStyleSheet(f"color: {COLOR_ACCENT_GREEN}; font-size: 13px; font-weight: bold;")