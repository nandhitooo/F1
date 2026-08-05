"""Theme and design system for F1 Live Tracker & Analysis.
Provides QSS stylesheet, F1 brand palette, tyre/team badges, and Matplotlib dark theme.
"""

import matplotlib as mpl

# Palette Constants
COLOR_BG_DARK = "#0F1015"
COLOR_PANEL_BG = "#181920"
COLOR_HEADER_BG = "#20222C"
COLOR_BORDER = "#2B2E3C"
COLOR_PRIMARY_RED = "#E10600"
COLOR_PRIMARY_HOVER = "#FF1E19"
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_MUTED = "#8E94A5"
COLOR_ACCENT_CYAN = "#00E5FF"
COLOR_ACCENT_GREEN = "#00E676"
COLOR_ACCENT_YELLOW = "#FFC107"

# Tyre Compound Styling Map
TYRE_COLORS = {
    "SOFT": {"bg": "#3A0D0D", "fg": "#FF4D4D", "border": "#FF1801", "label": "SOFT"},
    "MEDIUM": {"bg": "#3A330D", "fg": "#FFE600", "border": "#FFF200", "label": "MED"},
    "HARD": {"bg": "#222530", "fg": "#FFFFFF", "border": "#E0E0E0", "label": "HARD"},
    "INTERMEDIATE": {"bg": "#0D3A18", "fg": "#00FF66", "border": "#39B54A", "label": "INTER"},
    "WET": {"bg": "#0D2B3A", "fg": "#00C3FF", "border": "#00AEEF", "label": "WET"},
}

# Team Colors (Key matching part of team name)
TEAM_COLORS = {
    "Red Bull": "#3671C6",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#0093CC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "AlphaTauri": "#6692FF",
    "Sauber": "#52E252",
    "Kick": "#52E252",
    "Haas": "#B6BABD",
}

def get_team_color(team_name: str) -> str:
    """Find team color hex string or default accent."""
    if not team_name:
        return COLOR_TEXT_MUTED
    for key, hex_val in TEAM_COLORS.items():
        if key.lower() in team_name.lower():
            return hex_val
    return "#888888"


def get_stylesheet() -> str:
    """Returns global QSS stylesheet for dark F1 theme."""
    return f"""
    /* Global Window Background */
    QMainWindow, QDialog, QWidget {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_PRIMARY};
        font-family: 'Segoe UI', 'SF Pro Text', -apple-system, sans-serif;
        font-size: 13px;
    }}

    /* Card Panels & Containers */
    QFrame#cardPanel, QWidget#cardWidget {{
        background-color: {COLOR_PANEL_BG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
    }}

    /* Header Bar */
    QFrame#headerBar {{
        background-color: {COLOR_HEADER_BG};
        border-bottom: 2px solid {COLOR_PRIMARY_RED};
        padding: 8px 16px;
    }}

    QLabel#headerTitle {{
        font-size: 18px;
        font-weight: bold;
        color: {COLOR_TEXT_PRIMARY};
        letter-spacing: 1px;
    }}

    QLabel#headerBadge {{
        background-color: {COLOR_PRIMARY_RED};
        color: #FFFFFF;
        font-weight: bold;
        font-size: 11px;
        padding: 3px 8px;
        border-radius: 4px;
    }}

    /* Tab Widget & Bar */
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER};
        background-color: {COLOR_PANEL_BG};
        border-radius: 8px;
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_MUTED};
        padding: 10px 22px;
        margin-right: 4px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 600;
        border: 1px solid transparent;
    }}

    QTabBar::tab:hover {{
        background-color: {COLOR_PANEL_BG};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QTabBar::tab:selected {{
        background-color: {COLOR_PANEL_BG};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER};
        border-bottom: 3px solid {COLOR_PRIMARY_RED};
    }}

    /* Buttons */
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_PRIMARY_RED}, stop:1 #B30500);
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 12px;
    }}

    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_PRIMARY_HOVER}, stop:1 #C80500);
    }}

    QPushButton:pressed {{
        background-color: #990400;
    }}

    QPushButton:disabled {{
        background-color: #3A3D4A;
        color: #6C7284;
    }}

    QPushButton#secondaryBtn {{
        background-color: #272A38;
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER};
    }}

    QPushButton#secondaryBtn:hover {{
        background-color: #323648;
        border-color: {COLOR_PRIMARY_RED};
    }}

    /* Input Fields & Combo Boxes */
    QLineEdit, QComboBox {{
        background-color: #12131A;
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 12px;
        selection-background-color: {COLOR_PRIMARY_RED};
    }}

    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {COLOR_PRIMARY_RED};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left-width: 0px;
    }}

    QComboBox QAbstractItemView {{
        background-color: #181920;
        color: {COLOR_TEXT_PRIMARY};
        selection-background-color: {COLOR_PRIMARY_RED};
        border: 1px solid {COLOR_BORDER};
    }}

    /* Checkbox */
    QCheckBox {{
        color: {COLOR_TEXT_PRIMARY};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {COLOR_BORDER};
        background-color: #12131A;
    }}

    QCheckBox::indicator:checked {{
        background-color: {COLOR_PRIMARY_RED};
        border-color: {COLOR_PRIMARY_RED};
    }}

    /* Tables */
    QTableWidget {{
        background-color: {COLOR_PANEL_BG};
        gridline-color: #222430;
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        color: {COLOR_TEXT_PRIMARY};
        selection-background-color: #351C24;
        selection-color: #FFFFFF;
    }}

    QHeaderView::section {{
        background-color: {COLOR_HEADER_BG};
        color: {COLOR_TEXT_MUTED};
        padding: 8px 10px;
        font-weight: bold;
        font-size: 11px;
        text-transform: uppercase;
        border: none;
        border-bottom: 2px solid {COLOR_BORDER};
    }}

    QTableWidget::item {{
        padding: 6px 8px;
        border-bottom: 1px solid #1E202C;
    }}

    QTableWidget::item:alternate {{
        background-color: #14151C;
    }}

    /* Scrollbars (Vertical & Horizontal) */
    QScrollBar:vertical {{
        background-color: #12131A;
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background-color: #2F3346;
        min-height: 24px;
        border-radius: 4px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_PRIMARY_RED};
    }}

    QScrollBar::handle:vertical:pressed {{
        background-color: #B30500;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        width: 0px;
        background: none;
        border: none;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background-color: #12131A;
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: #2F3346;
        min-width: 24px;
        border-radius: 4px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_PRIMARY_RED};
    }}

    QScrollBar::handle:horizontal:pressed {{
        background-color: #B30500;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        height: 0px;
        width: 0px;
        background: none;
        border: none;
    }}

    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}

    QTableCornerButton::section {{
        background-color: {COLOR_PANEL_BG};
        border: none;
    }}

    """


def apply_dark_matplotlib_theme(figure, axes_list=None):
    """Applies high-tech dark F1 styling to Matplotlib figure and axes."""
    figure.patch.set_facecolor(COLOR_PANEL_BG)

    if axes_list is None:
        axes_list = figure.get_axes()

    for ax in axes_list:
        ax.set_facecolor("#111218")

        # Spines
        for spine in ax.spines.values():
            spine.set_color(COLOR_BORDER)
            spine.set_linewidth(1.0)

        # Labels & Ticks
        ax.xaxis.label.set_color(COLOR_TEXT_MUTED)
        ax.yaxis.label.set_color(COLOR_TEXT_MUTED)
        ax.title.set_color(COLOR_TEXT_PRIMARY)
        ax.title.set_weight("bold")

        ax.tick_params(colors=COLOR_TEXT_MUTED, which="both", labelsize=9)

        # Grid
        ax.grid(True, linestyle="--", alpha=0.15, color="#FFFFFF")

        # Legend
        legend = ax.get_legend()
        if legend:
            frame = legend.get_frame()
            frame.set_facecolor("#1B1D26")
            frame.set_edgecolor(COLOR_BORDER)
            for text in legend.get_texts():
                text.set_color(COLOR_TEXT_PRIMARY)
