"""Track Map Tab: Menampilkan posisi mobil di sirkuit secara real-time menggunakan data OpenF1 location endpoint."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QCheckBox,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from core.openf1_client import OpenF1Client, latest_by_driver
from ui.theme import apply_dark_matplotlib_theme, get_team_color, COLOR_PANEL_BG, COLOR_BORDER

class TrackMapTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = OpenF1Client()
        self.car_positions = {}
        self.session_key = None
        self.timer = QTimer(self)
        self.timer.setInterval(3000)  # Update setiap 3 detik
        self.timer.timeout.connect(self.update_track)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(0, 8, 0, 0)
        
        # Control Panel
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("cardPanel")
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(16, 12, 16, 12)
        
        # Status info
        status_box = QVBoxLayout()
        lbl_status = QLabel("TRACK STATUS")
        lbl_status.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.status_label = QLabel("● WAITING FOR DATA")
        self.status_label.setStyleSheet("color: #FFC107; font-size: 13px; font-weight: bold;")
        status_box.addWidget(lbl_status)
        status_box.addWidget(self.status_label)
        ctrl_layout.addLayout(status_box)
        
        # Session info
        session_box = QVBoxLayout()
        lbl_session = QLabel("SESSION")
        lbl_session.setStyleSheet("color: #8E94A5; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.session_label = QLabel("-")
        self.session_label.setStyleSheet("color: #00E5FF; font-size: 13px; font-weight: bold;")
        session_box.addWidget(lbl_session)
        session_box.addWidget(self.session_label)
        ctrl_layout.addLayout(session_box)
        
        # Controls
        ctrl_layout.addStretch()
        
        self.auto_checkbox = QCheckBox("Auto-refresh (3s)")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.stateChanged.connect(self._toggle_auto_refresh)
        ctrl_layout.addWidget(self.auto_checkbox)
        
        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.clicked.connect(self.update_track)
        ctrl_layout.addWidget(self.refresh_btn)
        
        main_layout.addWidget(ctrl_frame)
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvasQTAgg(self.figure)
        apply_dark_matplotlib_theme(self.figure)
        main_layout.addWidget(self.canvas)
        
        # Legend / Info panel
        info_frame = QFrame()
        info_frame.setObjectName("cardPanel")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        self.info_label = QLabel("📍 Posisi mobil ditampilkan berdasarkan data OpenF1. Warna sesuai dengan tim masing-masing.")
        self.info_label.setStyleSheet("color: #8E94A5; font-size: 11px;")
        info_layout.addWidget(self.info_label)
        
        main_layout.addWidget(info_frame)
        
        # Start polling
        self.timer.start()
        self.update_track()
    
    def _toggle_auto_refresh(self, state):
        if state:
            self.timer.start()
        else:
            self.timer.stop()
    
    def update_track(self):
        """Fetch location data dan update track map."""
        try:
            session = self.client.get_latest_session()
            if not session:
                self.status_label.setText("● NO ACTIVE SESSION")
                self.status_label.setStyleSheet("color: #E10600; font-size: 13px; font-weight: bold;")
                return
            
            session_key = session["session_key"]
            self.session_key = session_key
            
            # Update session info
            session_name = session.get("session_name", "Unknown")
            circuit_name = session.get("circuit_short_name", "Unknown Circuit")
            self.session_label.setText(f"{session_name} - {circuit_name}")
            
            # Fetch location data
            locations = self.client._get("location", session_key=session_key)
            if not locations:
                self.status_label.setText("● NO LOCATION DATA")
                self.status_label.setStyleSheet("color: #FFC107; font-size: 13px; font-weight: bold;")
                return
            
            # Get latest position for each driver
            latest_positions = latest_by_driver(locations)
            
            # Fetch driver info for colors
            drivers = self.client.get_drivers(session_key)
            driver_map = {d["driver_number"]: d for d in drivers}
            
            # Update car positions
            self.car_positions = {}
            for num, pos in latest_positions.items():
                driver = driver_map.get(num, {})
                team = driver.get("team_name", "")
                color = get_team_color(team)
                self.car_positions[num] = {
                    "x": pos.get("x", 0),
                    "y": pos.get("y", 0),
                    "z": pos.get("z", 0),
                    "driver": driver.get("name_acronym", str(num)),
                    "team": team,
                    "color": color,
                }
            
            self._draw_track()
            self.status_label.setText("● TRACK ACTIVE")
            self.status_label.setStyleSheet("color: #00E676; font-size: 13px; font-weight: bold;")
            
        except Exception as e:
            self.status_label.setText(f"● ERROR: {str(e)[:30]}")
            self.status_label.setStyleSheet("color: #E10600; font-size: 13px; font-weight: bold;")
    
    def _draw_track(self):
        """Draw track map with car positions."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Track boundaries (approximate oval)
        track_width = 100
        track_length = 200
        
        # Draw track using bezier curve or oval
        theta = np.linspace(0, 2*np.pi, 100)
        rx, ry = track_length/2, track_width/2
        
        # Outer track
        ax.plot(rx*np.cos(theta), ry*np.sin(theta), color=COLOR_BORDER, linewidth=2, alpha=0.5)
        ax.plot(rx*1.05*np.cos(theta), ry*1.05*np.sin(theta), color=COLOR_BORDER, linewidth=1, alpha=0.3)
        
        # Grid lines (like F1 broadcast)
        for i in range(0, 360, 30):
            angle = np.radians(i)
            x = rx * 1.02 * np.cos(angle)
            y = ry * 1.02 * np.sin(angle)
            ax.plot([0, x], [0, y], color=COLOR_BORDER, linewidth=0.5, alpha=0.15)
        
        # Draw start/finish line
        ax.axhline(y=0, xmin=-0.02, xmax=0.02, color="#E10600", linewidth=3, alpha=0.8)
        
        # Draw cars
        for num, pos in self.car_positions.items():
            x = pos["x"] / 10  # Scale down for visualization
            y = pos["y"] / 10
            
            # Adjust scale
            x = np.clip(x, -rx*0.9, rx*0.9)
            y = np.clip(y, -ry*0.9, ry*0.9)
            
            # Car dot with glow
            ax.scatter(x, y, s=200, color=pos["color"], 
                      edgecolor='white', linewidth=1.5, 
                      alpha=0.9, zorder=5)
            
            # Glow effect
            ax.scatter(x, y, s=400, color=pos["color"], 
                      alpha=0.2, zorder=4)
            
            # Driver label
            ax.annotate(pos["driver"], (x, y), 
                       xytext=(0, 20), textcoords='offset points',
                       color='white', fontsize=9, fontweight='bold',
                       ha='center', va='bottom')
        
        # Set limits with padding
        pad = 20
        ax.set_xlim(-rx - pad, rx + pad)
        ax.set_ylim(-ry - pad, ry + pad)
        
        # Styling
        ax.set_facecolor("#111218")
        ax.set_aspect('equal')
        ax.set_title("🏎️ LIVE TRACK MAP", color='white', fontweight='bold', fontsize=14, pad=20)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Legend info - car count
        car_count = len(self.car_positions)
        ax.text(0.02, 0.02, f"🚗 {car_count} cars on track", 
               transform=ax.transAxes, color="#8E94A5", fontsize=10,
               bbox=dict(boxstyle="round,pad=0.3", facecolor="#181920", alpha=0.8))
        
        apply_dark_matplotlib_theme(self.figure, [ax])
        self.figure.tight_layout()
        self.canvas.draw()