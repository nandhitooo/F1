from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from ui.tabs.live_tab import LiveTab
from ui.tabs.historical_tab import HistoricalTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Live Tracker & Analysis")
        self.resize(1200, 800)

        # Central Container
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Header Bar
        header = QFrame()
        header.setObjectName("headerBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        badge = QLabel("F1")
        badge.setObjectName("headerBadge")
        
        title = QLabel("TELEMETRY & LIVE TRACKER")
        title.setObjectName("headerTitle")

        subtitle = QLabel("REAL-TIME TIMING & FASTF1 ANALYTICS")
        subtitle.setStyleSheet("color: #8E94A5; font-size: 11px; font-weight: bold; letter-spacing: 1px;")

        header_layout.addWidget(badge)
        header_layout.addWidget(title)
        header_layout.addSpacing(10)
        header_layout.addWidget(subtitle)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Tabs Widget
        tabs = QTabWidget()
        tabs.addTab(LiveTab(), "⚡ LIVE TIMING & LEADERBOARD")
        tabs.addTab(HistoricalTab(), "📊 HISTORICAL TELEMETRY & RACE ANALYSIS")
        main_layout.addWidget(tabs)

        self.setCentralWidget(main_container)