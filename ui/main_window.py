from PySide6.QtWidgets import QMainWindow, QTabWidget
from ui.tabs.live_tab import LiveTab
from ui.tabs.historical_tab import HistoricalTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Live Tracker & Analysis")
        self.resize(1100, 720)

        tabs = QTabWidget()
        tabs.addTab(LiveTab(), "Live")
        tabs.addTab(HistoricalTab(), "Historical Analysis")
        self.setCentralWidget(tabs)