"""
styles.py
---------
Institutional-grade, high-contrast dark theme stylesheet inspired by
modern financial trading terminals (TradingView Pro, Bloomberg, Sensibull).
"""

DARK_THEME_QSS = """
/* ========================================================================= */
/* Global Window & Font Defaults                                             */
/* ========================================================================= */
QMainWindow, QWidget {
    background-color: #080D18;
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* ========================================================================= */
/* Sleek Modern Scrollbars                                                   */
/* ========================================================================= */
QScrollBar:vertical {
    background-color: #080D18;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background-color: #1E293B;
    min-height: 24px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background-color: #38BDF8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #080D18;
    height: 6px;
    margin: 0px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background-color: #1E293B;
    min-width: 24px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #38BDF8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    width: 0px;
}

/* ========================================================================= */
/* Institutional Surface Cards / Group Boxes                                 */
/* ========================================================================= */
QGroupBox {
    background-color: #0D1527;
    border: 1px solid #1E293B;
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 18px;
    padding-left: 12px;
    padding-right: 12px;
    padding-bottom: 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 4px 12px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #0F172A);
    color: #38BDF8;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.8px;
}

/* ========================================================================= */
/* Inputs, ComboBoxes, and SpinBoxes                                         */
/* ========================================================================= */
QLineEdit, QComboBox, QSpinBox {
    background-color: #111C33;
    color: #F8FAFC;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    font-weight: 500;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {
    border: 1px solid #334155;
    background-color: #14223E;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #0EA5E9;
    background-color: #0F1A30;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #1E293B;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94A3B8;
    width: 0px;
    height: 0px;
}
QComboBox QAbstractItemView {
    background-color: #0D1527;
    color: #F8FAFC;
    border: 1px solid #0EA5E9;
    border-radius: 8px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    outline: none;
    padding: 6px;
}

/* ========================================================================= */
/* Interactive File Lists                                                    */
/* ========================================================================= */
QListWidget {
    background-color: #080D18;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 6px;
    color: #CBD5E1;
    font-size: 12px;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
    margin-bottom: 3px;
    border-left: 2px solid transparent;
}
QListWidget::item:hover {
    background-color: #111C33;
    color: #38BDF8;
    border-left: 2px solid #0EA5E9;
}
QListWidget::item:selected {
    background-color: #1E3A8A;
    color: #FFFFFF;
    border-left: 2px solid #38BDF8;
}

/* ========================================================================= */
/* Buttons                                                                   */
/* ========================================================================= */
QPushButton {
    background-color: #111C33;
    color: #F1F5F9;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #1A2B4C;
    border-color: #38BDF8;
    color: #FFFFFF;
}
QPushButton:pressed {
    background-color: #0B1120;
}
QPushButton:disabled {
    background-color: #0B101D;
    color: #475569;
    border-color: #161F30;
}

/* Primary Execution Button (Neon Sky Gradient) */
QPushButton#btn_process {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #2563EB);
    color: #FFFFFF;
    border: none;
    border-radius: 9px;
    padding: 11px 26px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
QPushButton#btn_process:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #1D4ED8);
}
QPushButton#btn_process:disabled {
    background: #111C33;
    color: #475569;
}

/* Institutional Export Button (Emerald Green) */
QPushButton#btn_export {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
    color: #FFFFFF;
    border: none;
    border-radius: 9px;
    padding: 11px 22px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.4px;
}
QPushButton#btn_export:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
}
QPushButton#btn_export:disabled {
    background: #111C33;
    color: #475569;
}

/* Reset Utility Button */
QPushButton#btn_clear {
    background-color: #1E293B;
    color: #CBD5E1;
    border: 1px solid #334155;
    border-radius: 9px;
    padding: 11px 18px;
    font-weight: 600;
}
QPushButton#btn_clear:hover {
    background-color: #334155;
    color: #FFFFFF;
}

/* Remove Item Button */
QPushButton#btn_remove {
    background-color: rgba(239, 68, 68, 0.10);
    border: 1px solid #7F1D1D;
    color: #FCA5A5;
    font-size: 11px;
    padding: 5px 12px;
    border-radius: 6px;
}
QPushButton#btn_remove:hover {
    background-color: rgba(239, 68, 68, 0.25);
    border-color: #DC2626;
    color: #FFFFFF;
}

/* ========================================================================= */
/* Modern Precision Progress Bar                                             */
/* ========================================================================= */
QProgressBar {
    background-color: #0D1527;
    border: 1px solid #1E293B;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 800;
    font-size: 11px;
    height: 14px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #6366F1);
    border-radius: 5px;
}

/* ========================================================================= */
/* Institutional Financial Grid (TradingView / Bloomberg Style)              */
/* ========================================================================= */
QTableWidget {
    background-color: #080D18;
    alternate-background-color: #0D1424;
    gridline-color: #162035;
    border: 1px solid #1E293B;
    border-radius: 10px;
    color: #F1F5F9;
    font-size: 13px;
    selection-background-color: #1E3A8A;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #10192C;
}
QTableWidget::item:selected {
    background-color: #1E3A8A;
    color: #FFFFFF;
}
QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 10px 8px;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    border: none;
    border-right: 1px solid #080D18;
    border-bottom: 2px solid #0EA5E9;
}

/* ========================================================================= */
/* Tab Widget (Terminal & Playbook)                                          */
/* ========================================================================= */
QTabWidget::pane {
    border: 1px solid #1E293B;
    border-radius: 8px;
    background-color: #050811;
    top: -1px;
}
QTabBar::tab {
    background: #0D1527;
    color: #94A3B8;
    border: 1px solid #1E293B;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 12px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #050811;
    color: #38BDF8;
    border: 1px solid #1E293B;
    border-bottom: 2px solid #0EA5E9;
    font-weight: 700;
}
QTabBar::tab:hover:!selected {
    background: #111C33;
    color: #E2E8F0;
}

/* ========================================================================= */
/* Terminal Console                                                          */
/* ========================================================================= */
QTextEdit#log_panel {
    background-color: #050811;
    color: #E2E8F0;
    border: none;
    border-radius: 8px;
    font-family: Consolas, "Cascadia Code", "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
    padding: 10px;
}

/* ========================================================================= */
/* Status Bar & Splitter                                                     */
/* ========================================================================= */
QStatusBar {
    background-color: #050811;
    color: #94A3B8;
    border-top: 1px solid #1E293B;
    font-size: 12px;
    padding: 4px;
}
QSplitter::handle {
    background-color: #1E293B;
    height: 4px;
}
"""
