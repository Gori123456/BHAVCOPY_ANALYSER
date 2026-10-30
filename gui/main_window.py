"""
main_window.py
--------------
Institutional-grade quantitative derivatives desktop terminal.
Inspired by Bloomberg Terminal, TradingView Pro, and Sensibull.

Key Features:
  - Institutional Financial Terminal Dark Theme
  - Live Ticker Tape & Market Spot Header
  - 5 Dynamic Executive KPI Metric Cards (ATM, CE, PE, Straddle, Quant Edge)
  - Universal File Resilience (works for ANY current & historical file)
  - In-Dashboard Contract Matrix (Symbol, Expiry, Strike, Option Side, Lookback)
  - Tabbed Results, Trade Playbook Insights, and Audit Terminal
"""

import logging
import os
from typing import Dict, List, Optional, Union

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QListWidget, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QSplitter,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from config.constants import APP_NAME, APP_VERSION, SUPPORTED_DATA_EXTENSIONS
from config.config_manager import AppConfig, ConfigError, load_config, save_config
from core.data_loader import extract_metadata_from_files
from core.exporter import export_result_to_excel, ExportError
from core.models import AnalysisResult, ProcessingWarning
from gui.styles import DARK_THEME_QSS
from gui.worker import AnalysisWorker

logger = logging.getLogger("fno_analyzer")

FILE_FILTER = "NSE Bhavcopy Data Files (*.csv *.xlsx *.xls);;All Files (*)"
POPULAR_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]


class MetricCard(QFrame):
    """Institutional KPI Card displaying quantitative options analytics."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0F1A30, stop:1 #0A1120);
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;")

        self.lbl_value = QLabel("---")
        self.lbl_value.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800; font-family: -apple-system, sans-serif;")

        self.lbl_subtitle = QLabel("Awaiting Data Engine")
        self.lbl_subtitle.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_subtitle)

    def update_data(self, value: str, subtitle: str, val_color: str = "#F8FAFC", sub_color: str = "#94A3B8"):
        self.lbl_value.setText(value)
        self.lbl_value.setStyleSheet(f"color: {val_color}; font-size: 20px; font-weight: 800;")
        self.lbl_subtitle.setText(subtitle)
        self.lbl_subtitle.setStyleSheet(f"color: {sub_color}; font-size: 11px; font-weight: 600;")

    def reset(self):
        self.lbl_value.setText("---")
        self.lbl_value.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800;")
        self.lbl_subtitle.setText("Awaiting Data Engine")
        self.lbl_subtitle.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Institutional Derivatives Terminal")
        self.resize(1280, 880)
        self.setStyleSheet(DARK_THEME_QSS)

        # Application State
        self.current_day_files: List[str] = []
        self.historical_files: List[str] = []
        self.symbol_expiries_map: Dict[str, List[str]] = {}
        self.last_results: Optional[List[AnalysisResult]] = None
        self.worker: Optional[AnalysisWorker] = None

        self._build_ui()
        self._wire_events()
        self._update_process_button_state()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # 1. Top Navigation & Market Ticker Header
        root_layout.addWidget(self._build_header_banner())

        # Main Splitter: Upper Controls & Lower Analytics
        splitter = QSplitter(Qt.Vertical)
        root_layout.addWidget(splitter)

        # 2. Control Desk (3 Columns: Current Bhavcopy, Historical Pool, Strategy Matrix)
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        top_layout.addWidget(self._build_current_day_group())
        top_layout.addWidget(self._build_historical_group())
        top_layout.addWidget(self._build_config_group())

        splitter.addWidget(top_widget)

        # 3. Bottom Analytical Workspace
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 6, 0, 0)
        bottom_layout.setSpacing(10)

        # Execution Action Bar + Progress Indicator
        bottom_layout.addLayout(self._build_action_row())
        bottom_layout.addWidget(self.progress_bar)

        # 5 Interactive KPI Metric Cards (Ribbon)
        bottom_layout.addLayout(self._build_kpi_cards_banner())

        # Tabbed Analytical Display
        bottom_layout.addWidget(self._build_tabbed_workspace(), stretch=1)

        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.statusBar().showMessage("Quantitative Engine Online • Ready for Analysis")

    def _build_header_banner(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B1325, stop:1 #070B14);
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 6px 12px;
            }
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 6, 8, 6)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)

        title = QLabel(f"⚡ {APP_NAME.upper()}")
        title.setStyleSheet("font-size: 16px; font-weight: 900; color: #F8FAFC; letter-spacing: 0.8px;")

        badge_version = QLabel(f"PRO v{APP_VERSION}")
        badge_version.setStyleSheet("""
            background-color: #0284C7;
            color: #FFFFFF;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: 800;
        """)
        brand_row.addWidget(title)
        brand_row.addWidget(badge_version)
        brand_row.addStretch(1)

        subtitle = QLabel("NSE Derivatives Mispricing Scanner • ATM Profiler & Expected Move Matrix")
        subtitle.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: 500;")

        title_box.addLayout(brand_row)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch(1)

        # Live Market Spot Ticker Badge
        self.badge_ticker = QLabel("NIFTY 50 • SPOT: AWAITING LOAD")
        self.badge_ticker.setStyleSheet("""
            background-color: #0D1527;
            color: #38BDF8;
            border: 1px solid #1E293B;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        """)
        layout.addWidget(self.badge_ticker)

        # Live Engine Status Badge
        self.badge_status = QLabel("🟢 ENGINE READY")
        self.badge_status.setStyleSheet("""
            background-color: #0D1527;
            color: #10B981;
            border: 1px solid #064E3B;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        """)
        layout.addWidget(self.badge_status)
        return header

    def _build_current_day_group(self) -> QGroupBox:
        group = QGroupBox("📁 1. CURRENT SESSION BHAVCOPY")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.btn_upload_current = QPushButton("＋ Select Current Day Bhavcopy")
        self.btn_upload_current.setToolTip("Upload today's Bhavcopy CSV/Excel file")

        self.lbl_current_count = QLabel("0 files loaded")
        self.lbl_current_count.setStyleSheet("color: #94A3B8; font-size: 11px;")

        self.list_current_files = QListWidget()
        self.list_current_files.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.btn_remove_current = QPushButton("Remove Selected")
        self.btn_remove_current.setObjectName("btn_remove")

        layout.addWidget(self.btn_upload_current)
        layout.addWidget(self.lbl_current_count)
        layout.addWidget(self.list_current_files)
        layout.addWidget(self.btn_remove_current)
        return group

    def _build_historical_group(self) -> QGroupBox:
        group = QGroupBox("📚 2. HISTORICAL DATA POOL")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.btn_upload_historical = QPushButton("＋ Add Historical File(s)")
        self.btn_upload_historical.setToolTip("Upload past Bhavcopy or quote files (additive: click again to add more)")

        self.lbl_historical_count = QLabel("0 files loaded")
        self.lbl_historical_count.setStyleSheet("color: #94A3B8; font-size: 11px;")

        self.list_historical_files = QListWidget()
        self.list_historical_files.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.btn_remove_historical = QPushButton("Remove Selected")
        self.btn_remove_historical.setObjectName("btn_remove")

        layout.addWidget(self.btn_upload_historical)
        layout.addWidget(self.lbl_historical_count)
        layout.addWidget(self.list_historical_files)
        layout.addWidget(self.btn_remove_historical)
        return group

    def _build_config_group(self) -> QGroupBox:
        group = QGroupBox("⚙️ 3. CONTRACT & QUANT MATRIX")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        # Symbol & Expiry Row
        row_top = QHBoxLayout()
        row_top.setSpacing(8)

        vbox_sym = QVBoxLayout()
        lbl_sym = QLabel("Symbol:")
        lbl_sym.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        self.combo_symbol = QComboBox()
        self.combo_symbol.setEditable(True)
        self.combo_symbol.addItems(POPULAR_SYMBOLS)
        self.combo_symbol.setCurrentText("NIFTY")
        vbox_sym.addWidget(lbl_sym)
        vbox_sym.addWidget(self.combo_symbol)

        vbox_exp = QVBoxLayout()
        lbl_exp = QLabel("Contract Expiry:")
        lbl_exp.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        self.combo_expiry = QComboBox()
        self.combo_expiry.setEditable(True)
        self.combo_expiry.addItem("27-Oct-2026")
        self.combo_expiry.setCurrentText("27-Oct-2026")
        vbox_exp.addWidget(lbl_exp)
        vbox_exp.addWidget(self.combo_expiry)

        row_top.addLayout(vbox_sym)
        row_top.addLayout(vbox_exp)

        # Strike Price, History Days & Option Side Row
        row_mid = QHBoxLayout()
        row_mid.setSpacing(6)

        vbox_strike = QVBoxLayout()
        lbl_strike = QLabel("Target Strike:")
        lbl_strike.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        self.combo_strike = QComboBox()
        self.combo_strike.setEditable(True)
        self.combo_strike.addItems(["Auto (ATM)"])
        vbox_strike.addWidget(lbl_strike)
        vbox_strike.addWidget(self.combo_strike)

        vbox_days = QVBoxLayout()
        lbl_days = QLabel("History:")
        lbl_days.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        self.spin_history_days = QSpinBox()
        self.spin_history_days.setRange(1, 90)
        self.spin_history_days.setValue(7)
        self.spin_history_days.setSuffix(" D")
        vbox_days.addWidget(lbl_days)
        vbox_days.addWidget(self.spin_history_days)

        vbox_opt = QVBoxLayout()
        lbl_opt = QLabel("Option Side:")
        lbl_opt.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        self.combo_option_type = QComboBox()
        self.combo_option_type.addItems(["BOTH (CE & PE)", "CE (Call)", "PE (Put)"])
        self.combo_option_type.setCurrentIndex(0)
        vbox_opt.addWidget(lbl_opt)
        vbox_opt.addWidget(self.combo_option_type)

        row_mid.addLayout(vbox_strike)
        row_mid.addLayout(vbox_days)
        row_mid.addLayout(vbox_opt)

        # Presets Buttons Row
        row_presets = QHBoxLayout()
        self.btn_load_preset = QPushButton("📂 Load Preset")
        self.btn_load_preset.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_save_preset = QPushButton("💾 Save Preset")
        self.btn_save_preset.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        row_presets.addWidget(self.btn_load_preset)
        row_presets.addWidget(self.btn_save_preset)

        layout.addLayout(row_top)
        layout.addLayout(row_mid)
        layout.addLayout(row_presets)
        layout.addStretch(1)

        return group

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.btn_process = QPushButton("▶ RUN QUANT ANALYSIS")
        self.btn_process.setObjectName("btn_process")
        self.btn_process.setCursor(Qt.PointingHandCursor)

        self.btn_export = QPushButton("📊 EXPORT EXCEL REPORT")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setEnabled(False)

        self.btn_clear = QPushButton("🔄 RESET ENGINE")
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.setCursor(Qt.PointingHandCursor)

        row.addWidget(self.btn_process)
        row.addWidget(self.btn_export)
        row.addWidget(self.btn_clear)
        row.addStretch(1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        return row

    def _build_kpi_cards_banner(self) -> QHBoxLayout:
        banner = QHBoxLayout()
        banner.setSpacing(8)

        self.card_atm = MetricCard("ATM Strike & Spot Ref")
        self.card_ce = MetricCard("ATM Call (CE) Close")
        self.card_pe = MetricCard("ATM Put (PE) Close")
        self.card_straddle = MetricCard("ATM Straddle Move")
        self.card_edge = MetricCard("Quant Edge & Bias")

        banner.addWidget(self.card_atm)
        banner.addWidget(self.card_ce)
        banner.addWidget(self.card_pe)
        banner.addWidget(self.card_straddle)
        banner.addWidget(self.card_edge)

        return banner

    def _build_tabbed_workspace(self) -> QTabWidget:
        self.tabs = QTabWidget()

        # Tab 1: Executive Results Grid
        tab_grid = QWidget()
        l_grid = QVBoxLayout(tab_grid)
        l_grid.setContentsMargins(6, 6, 6, 6)
        self.results_table = QTableWidget(0, 0)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        l_grid.addWidget(self.results_table)
        self.tabs.addTab(tab_grid, "📊 Executive Results Grid")

        # Tab 2: Quantitative Trade Playbook
        tab_playbook = QWidget()
        l_playbook = QVBoxLayout(tab_playbook)
        l_playbook.setContentsMargins(10, 10, 10, 10)
        self.txt_playbook = QTextEdit()
        self.txt_playbook.setReadOnly(True)
        self.txt_playbook.setStyleSheet("""
            QTextEdit {
                background-color: #050811;
                border: 1px solid #1E293B;
                border-radius: 8px;
                color: #F8FAFC;
                font-family: -apple-system, sans-serif;
                font-size: 13px;
                line-height: 1.6;
                padding: 12px;
            }
        """)
        self.txt_playbook.setText("Run quantitative analysis to generate real-time trade signals and strategy playbook recommendations.")
        l_playbook.addWidget(self.txt_playbook)
        self.tabs.addTab(tab_playbook, "💡 Quantitative Trade Playbook")

        # Tab 3: System Audit & Engine Logs
        tab_logs = QWidget()
        l_logs = QVBoxLayout(tab_logs)
        l_logs.setContentsMargins(6, 6, 6, 6)
        self.log_panel = QTextEdit()
        self.log_panel.setObjectName("log_panel")
        self.log_panel.setReadOnly(True)
        l_logs.addWidget(self.log_panel)
        self.tabs.addTab(tab_logs, "🖥️ Audit Console & Terminal Logs")

        return self.tabs

    # ------------------------------------------------------------------
    # Event Wiring
    # ------------------------------------------------------------------
    def _wire_events(self) -> None:
        self.btn_upload_current.clicked.connect(self._on_upload_current_day)
        self.btn_remove_current.clicked.connect(self._on_remove_current_selected)
        self.btn_upload_historical.clicked.connect(self._on_upload_historical)
        self.btn_remove_historical.clicked.connect(self._on_remove_historical_selected)

        self.btn_load_preset.clicked.connect(self._on_load_preset)
        self.btn_save_preset.clicked.connect(self._on_save_preset)

        self.btn_process.clicked.connect(self._on_process)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_clear.clicked.connect(self._on_clear)

        self.combo_symbol.currentTextChanged.connect(self._on_symbol_changed)
        self.combo_expiry.currentTextChanged.connect(self._update_process_button_state)

    # ------------------------------------------------------------------
    # Handlers & Actions
    # ------------------------------------------------------------------
    def _on_symbol_changed(self, symbol_text: str) -> None:
        """Dynamically update expiry dropdown with ONLY expiries that exist for this symbol."""
        sym = symbol_text.strip().upper()
        exps = self.symbol_expiries_map.get(sym, [])
        if exps:
            current_exp = self.combo_expiry.currentText().strip()
            self.combo_expiry.blockSignals(True)
            self.combo_expiry.clear()
            self.combo_expiry.addItems(exps)
            if current_exp in exps:
                self.combo_expiry.setCurrentText(current_exp)
            else:
                self.combo_expiry.setCurrentIndex(0)
            self.combo_expiry.blockSignals(False)
            self._log(f"Filtered {len(exps)} valid expiry dates for symbol '{sym}'.")
        self._update_process_button_state()

    def _on_upload_current_day(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Current Day Data File(s)", "", FILE_FILTER
        )
        if not paths:
            return
        paths = self._filter_valid_paths(paths)
        if not paths:
            return

        added = self._add_files(self.current_day_files, paths)
        self._refresh_file_list(self.list_current_files, self.current_day_files)
        self.lbl_current_count.setText(f"{len(self.current_day_files)} file(s) loaded")
        self._log(f"Added {added} current-day file(s) (total: {len(self.current_day_files)}).")

        # Auto-detect symbols and expiries
        self._auto_detect_metadata(paths)
        self._update_process_button_state()

    def _auto_detect_metadata(self, paths: List[str]) -> None:
        """Scan uploaded file for available symbols and expiries."""
        try:
            symbols, mapping = extract_metadata_from_files(paths)
            if mapping:
                self.symbol_expiries_map = mapping

            if symbols:
                current_text = self.combo_symbol.currentText().strip().upper()
                self.combo_symbol.blockSignals(True)
                self.combo_symbol.clear()
                self.combo_symbol.addItems(symbols)
                if current_text in symbols:
                    self.combo_symbol.setCurrentText(current_text)
                elif "NIFTY" in symbols:
                    self.combo_symbol.setCurrentText("NIFTY")
                self.combo_symbol.blockSignals(False)

                # Update expiry dropdown specifically for the chosen symbol
                self._on_symbol_changed(self.combo_symbol.currentText())
                self._log(f"Auto-detected {len(symbols)} symbol(s) in uploaded file.")
        except Exception as exc:
            logger.debug("Metadata auto-detection non-fatal warning: %s", exc)

    def _on_upload_historical(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Historical Bhavcopy File(s)", "", FILE_FILTER
        )
        if not paths:
            return
        paths = self._filter_valid_paths(paths)
        if not paths:
            return

        added = self._add_files(self.historical_files, paths)
        self._refresh_file_list(self.list_historical_files, self.historical_files)
        self.lbl_historical_count.setText(f"{len(self.historical_files)} file(s) loaded")
        self._log(f"Added {added} historical file(s) (total: {len(self.historical_files)}).")

        # Scan historical files for available strike prices to populate the Strike Price dropdown
        try:
            from core.data_loader import _read_single_file
            from config.constants import BhavcopyColumns as C
            for p in paths:
                df = _read_single_file(p)
                if C.STRIKE_PRICE in df.columns:
                    s_vals = pd.to_numeric(df[C.STRIKE_PRICE], errors="coerce").dropna().unique()
                    for s in sorted(s_vals):
                        s_str = str(int(s)) if s.is_integer() else f"{s:.2f}"
                        if self.combo_strike.findText(s_str) == -1:
                            self.combo_strike.addItem(s_str)
        except Exception:
            pass

        self._update_process_button_state()

    def _on_remove_current_selected(self) -> None:
        removed = self._remove_selected(self.list_current_files, self.current_day_files)
        if removed:
            self.lbl_current_count.setText(f"{len(self.current_day_files)} file(s) loaded")
            self._log(f"Removed {removed} current-day file(s).")
        self._update_process_button_state()

    def _on_remove_historical_selected(self) -> None:
        removed = self._remove_selected(self.list_historical_files, self.historical_files)
        if removed:
            self.lbl_historical_count.setText(f"{len(self.historical_files)} file(s) loaded")
            self._log(f"Removed {removed} historical file(s).")
        self._update_process_button_state()

    def _on_load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load JSON Preset", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            config = load_config(path)
            self.combo_symbol.setCurrentText(config.symbol)
            self.combo_expiry.setCurrentText(config.expiry_date)
            self.spin_history_days.setValue(config.history_days)
            self.combo_strike.setCurrentText(getattr(config, "strike_price", "Auto (ATM)"))

            opt_upper = config.option_type.upper()
            if "BOTH" in opt_upper or "ALL" in opt_upper:
                self.combo_option_type.setCurrentIndex(0)
            elif opt_upper.startswith("PE"):
                self.combo_option_type.setCurrentIndex(2)
            else:
                self.combo_option_type.setCurrentIndex(1)

            self._log(f"Loaded configuration preset from '{os.path.basename(path)}'.")
        except ConfigError as exc:
            self._show_error(str(exc))

    def _on_save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON Preset", "my_fno_config.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            config = self._get_current_config()
            save_config(config, path)
            self._log(f"Preset configuration saved to '{os.path.basename(path)}'.")
            QMessageBox.information(self, "Preset Saved", f"Configuration preset saved to:\n{path}")
        except Exception as exc:
            self._show_error(f"Failed to save preset: {exc}")

    def _get_current_config(self) -> AppConfig:
        opt_choice = self.combo_option_type.currentText()
        if "BOTH" in opt_choice:
            opt_code = "BOTH"
        elif "PE" in opt_choice:
            opt_code = "PE"
        else:
            opt_code = "CE"

        return AppConfig(
            symbol=self.combo_symbol.currentText().strip().upper(),
            expiry_date=self.combo_expiry.currentText().strip(),
            history_days=self.spin_history_days.value(),
            option_type=opt_code,
            strike_price=self.combo_strike.currentText().strip(),
        )

    def _on_process(self) -> None:
        if not self._validate_inputs():
            return

        config = self._get_current_config()

        self.btn_process.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)

        self.card_atm.reset()
        self.card_ce.reset()
        self.card_pe.reset()
        self.card_straddle.reset()
        self.card_edge.reset()

        self.badge_status.setText("⚡ ANALYZING...")
        self.badge_status.setStyleSheet("""
            background-color: #0D1527;
            color: #F59E0B;
            border: 1px solid #78350F;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
        """)
        self.statusBar().showMessage("Running quantitative derivatives engine...")

        self.worker = AnalysisWorker(
            current_day_paths=self.current_day_files,
            historical_paths=self.historical_files,
            symbol=config.symbol,
            expiry_date=config.expiry_date,
            history_days=config.history_days,
            option_type=config.option_type,
            target_strike=config.strike_price,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_processing_finished)
        self.worker.failed.connect(self._on_processing_failed)
        self.worker.start()

    def _on_progress(self, pct: int, message: str) -> None:
        self.progress_bar.setValue(pct)
        self.statusBar().showMessage(message)

    def _on_processing_finished(self, results: Union[AnalysisResult, List[AnalysisResult]], warnings: List[ProcessingWarning]) -> None:
        res_list: List[AnalysisResult] = results if isinstance(results, list) else [results]
        self.last_results = res_list

        self._populate_results_table(res_list)
        self._update_kpi_cards(res_list)
        self._generate_playbook_insights(res_list)

        for w in warnings:
            self._log(f"[{w.source}] {w.message}")

        first = res_list[0]
        self.statusBar().showMessage(
            f"Analysis Complete • Strike: {first.strike_price} • History Evaluated: {first.days_used} trading days."
        )

        self.badge_status.setText("✅ AUDIT COMPLETE")
        self.badge_status.setStyleSheet("""
            background-color: #0D1527;
            color: #10B981;
            border: 1px solid #064E3B;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
        """)

        # Update Top Ticker Badge
        if first.underlying_price > 0:
            self.badge_ticker.setText(f"{first.symbol} • SPOT: ₹{first.underlying_price:,.2f} • ATM: {int(first.strike_price)}")

        self.btn_process.setEnabled(True)
        self.btn_export.setEnabled(True)

    def _on_processing_failed(self, message: str) -> None:
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Execution failed.")
        self.badge_status.setText("❌ RUN ERROR")
        self.badge_status.setStyleSheet("""
            background-color: #0D1527;
            color: #EF4444;
            border: 1px solid #7F1D1D;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
        """)
        self.btn_process.setEnabled(True)
        self._show_error(message)
        self._log(f"[ERROR] {message}")

    def _update_kpi_cards(self, results: List[AnalysisResult]) -> None:
        """Update top 5 visual executive KPI cards."""
        if not results:
            return

        res = results[0]
        strike_val = int(res.strike_price) if res.strike_price.is_integer() else res.strike_price
        diff_pts = (res.underlying_price - res.strike_price) if res.underlying_price > 0 else 0
        ref_text = f"Spot: ₹{res.underlying_price:,.2f} (Δ {diff_pts:+.2f} pts)" if res.underlying_price > 0 else "Atm Strike Evaluated"
        self.card_atm.update_data(f"{strike_val:,}", ref_text, val_color="#38BDF8")

        ce_res = next((r for r in results if r.option_type == "CE"), None)
        pe_res = next((r for r in results if r.option_type == "PE"), None)

        ce_close = 0.0
        pe_close = 0.0

        if ce_res:
            c_stats = ce_res.field_stats.get("Close")
            if c_stats and pd.notna(c_stats.current):
                ce_close = c_stats.current
                if pd.notna(c_stats.average) and c_stats.average > 0:
                    pct = ((c_stats.current - c_stats.average) / c_stats.average) * 100
                    sub = f"{pct:+.1f}% vs {ce_res.days_used}D Avg (₹{c_stats.average:.2f})"
                    col = "#10B981" if pct >= 0 else "#EF4444"
                else:
                    sub = f"Avg: ₹{c_stats.average:.2f}" if pd.notna(c_stats.average) else ""
                    col = "#94A3B8"
                self.card_ce.update_data(f"₹{c_stats.current:.2f}", sub, val_color="#F8FAFC", sub_color=col)

        if pe_res:
            p_stats = pe_res.field_stats.get("Close")
            if p_stats and pd.notna(p_stats.current):
                pe_close = p_stats.current
                if pd.notna(p_stats.average) and p_stats.average > 0:
                    pct = ((p_stats.current - p_stats.average) / p_stats.average) * 100
                    sub = f"{pct:+.1f}% vs {pe_res.days_used}D Avg (₹{p_stats.average:.2f})"
                    col = "#10B981" if pct >= 0 else "#EF4444"
                else:
                    sub = f"Avg: ₹{p_stats.average:.2f}" if pd.notna(p_stats.average) else ""
                    col = "#94A3B8"
                self.card_pe.update_data(f"₹{p_stats.current:.2f}", sub, val_color="#F8FAFC", sub_color=col)

        # Combined Straddle Card
        if ce_close > 0 and pe_close > 0:
            tot_straddle = ce_close + pe_close
            self.card_straddle.update_data(f"₹{tot_straddle:.2f}", f"Exp Move: ±{tot_straddle:.1f} pts", val_color="#FBBF24", sub_color="#CBD5E1")
        elif ce_close > 0:
            self.card_straddle.update_data(f"₹{ce_close:.2f}", "Single Side Profiled", val_color="#FBBF24")
        elif pe_close > 0:
            self.card_straddle.update_data(f"₹{pe_close:.2f}", "Single Side Profiled", val_color="#FBBF24")

        # Quant Strategy Signal Card
        max_pct = 0.0
        for r in results:
            c = r.field_stats.get("Close")
            if c and pd.notna(c.current) and pd.notna(c.average) and c.average > 0:
                p = ((c.current - c.average) / c.average) * 100
                if abs(p) > abs(max_pct):
                    max_pct = p

        if max_pct >= 25.0:
            self.card_edge.update_data("🔴 SELL SPREADS", f"Premiums Inflated (+{max_pct:.1f}%)", val_color="#EF4444", sub_color="#FCA5A5")
        elif max_pct <= -20.0:
            self.card_edge.update_data("🟢 BUY OPTIONS", f"Vol Crushed ({max_pct:.1f}%)", val_color="#10B981", sub_color="#6EE7B7")
        else:
            self.card_edge.update_data("⚖️ RANGE CONDOR", "Normal Premium Mean", val_color="#38BDF8", sub_color="#93C5FD")

    def _generate_playbook_insights(self, results: List[AnalysisResult]) -> None:
        """Generate institutional trade playbook insights on Tab 2."""
        if not results:
            return

        first = results[0]
        ce_res = next((r for r in results if r.option_type == "CE"), None)
        pe_res = next((r for r in results if r.option_type == "PE"), None)

        insights = [
            f"=== 🎯 QUANTITATIVE DERIVATIVES PLAYBOOK: {first.symbol} ===",
            f"Target Strike: {int(first.strike_price)} | Contract Expiry: {first.expiry_date} | Spot Ref: ₹{first.underlying_price:,.2f}\n",
        ]

        # Call Option Analysis
        if ce_res:
            c = ce_res.field_stats.get("Close")
            if c and pd.notna(c.current) and pd.notna(c.average) and c.average > 0:
                c_pct = ((c.current - c.average) / c.average) * 100
                insights.append(f"• CALL (CE) ANALYSIS: Current Close ₹{c.current:.2f} vs {ce_res.days_used}-Day Avg ₹{c.average:.2f} ({c_pct:+.1f}%)")
                if c_pct >= 25.0:
                    insights.append("  ➜ STATUS: EXTREMELY OVERPRICED. Option buyers are overpaying due to panic/speculation.")
                    insights.append("  ➜ STRATEGY: Favorable for Option Sellers. Consider selling ATM Calls or Bear Call Credit Spreads to capture theta decay.")
                elif c_pct <= -20.0:
                    insights.append("  ➜ STATUS: EXTREMELY UNDERPRICED (Vol Compression).")
                    insights.append("  ➜ STRATEGY: Favorable for Option Buyers. Cheap asymmetric upside if underlying index rallies.")
                else:
                    insights.append("  ➜ STATUS: FAIR VALUE. Premiums trading within normal statistical bounds.")
                insights.append("")

        # Put Option Analysis
        if pe_res:
            p = pe_res.field_stats.get("Close")
            if p and pd.notna(p.current) and pd.notna(p.average) and p.average > 0:
                p_pct = ((p.current - p.average) / p.average) * 100
                insights.append(f"• PUT (PE) ANALYSIS: Current Close ₹{p.current:.2f} vs {pe_res.days_used}-Day Avg ₹{p.average:.2f} ({p_pct:+.1f}%)")
                if p_pct >= 25.0:
                    insights.append("  ➜ STATUS: EXTREMELY OVERPRICED. Downside hedging demand has inflated put premiums.")
                    insights.append("  ➜ STRATEGY: Consider Bull Put Credit Spreads to collect high premium with defined risk.")
                elif p_pct <= -20.0:
                    insights.append("  ➜ STATUS: DIRT CHEAP PUT OPTIONS. Market complacency is high.")
                    insights.append("  ➜ STRATEGY: Low-cost downside insurance or speculative put buying.")
                else:
                    insights.append("  ➜ STATUS: FAIR VALUE.")
                insights.append("")

        # Combined Expected Move & Tomorrow's Tactical Directive
        if ce_res and pe_res:
            c = ce_res.field_stats.get("Close")
            p = pe_res.field_stats.get("Close")
            if c and p and pd.notna(c.current) and pd.notna(p.current):
                tot = c.current + p.current
                ref_spot = first.underlying_price if first.underlying_price > 0 else first.strike_price
                lower_be = ref_spot - tot
                upper_be = ref_spot + tot
                target_50 = tot * 0.50
                sl_25 = tot * 1.25
                cushion = upper_be - lower_be

                insights.append(f"• EXPECTED MARKET MOVE (ATM STRADDLE): ₹{tot:.2f}")
                insights.append(f"  The market is pricing in a ±{tot:.1f} point swing on {first.symbol} before expiry.")
                insights.append(f"  Breakeven Lower Band: {lower_be:,.2f}")
                insights.append(f"  Breakeven Upper Band: {upper_be:,.2f}")
                insights.append(f"  Total Safe Cushion: {cushion:,.1f} points\n")

                insights.append("=== 🌅 TOMORROW'S ACTION PLAN (09:18 – 09:30 AM IST) ===")
                insights.append(f"1. PRIMARY SETUP: SELL ATM {int(first.strike_price)} CE & PE STRADDLE")
                insights.append(f"   • Wait 3 minutes after 09:15 AM to let the chaotic opening tick settle.")
                insights.append(f"   • Entry Window: 09:18 AM – 09:25 AM IST (Combined premium: ~₹{tot:.2f}).")
                insights.append(f"   • Take Profit Target: 50% premium decay @ ₹{target_50:.2f} (Lock in +₹{tot - target_50:.2f}/share profit).")
                insights.append(f"   • Strict Stop-Loss: +25% premium expansion @ ₹{sl_25:.2f} (Hard GTT exit).")
                insights.append(f"   • Safety Corridor: Safe as long as spot trades between {lower_be:,.1f} and {upper_be:,.1f}.\n")

                insights.append("2. THREE OPENING BELL CONTINGENCIES:")
                insights.append(f"   • Flat Open (±35 pts): Deploy full straddle at {int(first.strike_price)} strike.")
                insights.append(f"   • Big Gap-Up (> +80 pts): Shift ATM upward to next strike, or deploy Bear Call Spread (Sell ATM CE, Buy OTM CE).")
                insights.append(f"   • Big Gap-Down (> -80 pts): Wait for 9:30 AM support confirmation, then deploy Bull Put Spread.\n")

                insights.append("=== 🔭 FUTURE ANALYSIS ROADMAP (WHAT TO PERFORM NEXT) ===")
                insights.append("• STEP 1 (Daily at 6:30 PM IST): Download tomorrow's fresh Bhavcopy and run this analyzer.")
                insights.append("  ➜ Measure Decay Velocity: Confirm straddle decayed by expected ₹30–45 points.")
                insights.append(f"• STEP 2 (Strike Migration Check): If spot shifts by >100 pts from {int(first.strike_price)}, roll the winning leg closer to re-center delta.")
                insights.append("• STEP 3 (Open Interest Confirmation): Check Bhavcopy 'ChngInOpnIntrst' for institutional resistance ceilings and support floors.")
                insights.append("• STEP 4 (Expiry Day T-0 Protocol): Always square off short options before 2:30 PM on expiry day before final 30-minute gamma explosion.\n")

        insights.append("Tip: Refer to 'HOW_THIS_MAKES_MONEY_TRADING_STRATEGY.md' for institutional position sizing and Greek risk parameters.")
        self.txt_playbook.setText("\n".join(insights))

    def _populate_results_table(self, results: List[AnalysisResult]) -> None:
        """Fill grid with institutional formatting and color-coded figures."""
        if not results:
            return

        rows_data = [r.to_flat_dict() for r in results]
        columns = list(rows_data[0].keys())

        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        self.results_table.setRowCount(len(rows_data))

        font_mono = QFont("Consolas, Courier New, monospace", 10)
        font_mono.setStyleHint(QFont.Monospace)

        for row_idx, row_dict in enumerate(rows_data):
            for col_idx, key in enumerate(columns):
                val = row_dict[key]
                if isinstance(val, float):
                    text = f"{val:.2f}"
                else:
                    text = str(val)

                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(font_mono)

                # Institutional Color-Coding
                if "Valuation" in key:
                    try:
                        pct = float(val)
                        if pct > 0:
                            item.setForeground(QColor("#10B981"))  # Emerald Green
                            item.setText(f"+{pct:.2f}%")
                        elif pct < 0:
                            item.setForeground(QColor("#EF4444"))  # Red
                            item.setText(f"{pct:.2f}%")
                        else:
                            item.setForeground(QColor("#94A3B8"))
                    except Exception:
                        pass
                elif "Quant Edge" in key:
                    item.setFont(QFont("-apple-system, sans-serif", 10, QFont.Bold))
                    if "Overpriced" in text:
                        item.setForeground(QColor("#FCA5A5"))  # Red tint
                    elif "Underpriced" in text:
                        item.setForeground(QColor("#6EE7B7"))  # Green tint
                    else:
                        item.setForeground(QColor("#93C5FD"))  # Cyan tint
                elif "Current" in key:
                    item.setForeground(QColor("#38BDF8"))  # Neon Sky Blue
                    item.setFont(QFont("Consolas, monospace", 10, QFont.Bold))
                elif "Avg" in key:
                    item.setForeground(QColor("#FBBF24"))  # Amber Gold
                elif "Max" in key:
                    item.setForeground(QColor("#34D399"))  # Green
                elif "Min" in key:
                    item.setForeground(QColor("#F87171"))  # Red
                elif key == "Contract":
                    item.setFont(QFont("-apple-system, sans-serif", 10, QFont.Bold))
                    if "CE" in text:
                        item.setForeground(QColor("#38BDF8"))
                    else:
                        item.setForeground(QColor("#F43F5E"))

                self.results_table.setItem(row_idx, col_idx, item)

        self.results_table.resizeColumnsToContents()

    def _on_export(self) -> None:
        if not self.last_results:
            self._show_error("No results to export. Run Process first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "atm_analysis_results.xlsx", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            export_result_to_excel(self.last_results, path)
            self._log(f"Results successfully exported to '{path}'.")
            QMessageBox.information(self, "Export Complete", f"Results successfully exported to:\n{path}")
        except ExportError as exc:
            self._show_error(str(exc))

    def _on_clear(self) -> None:
        self.current_day_files = []
        self.historical_files = []
        self.last_results = None

        self.list_current_files.clear()
        self.list_historical_files.clear()
        self.lbl_current_count.setText("0 files loaded")
        self.lbl_historical_count.setText("0 files loaded")

        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)
        self.progress_bar.setValue(0)
        self.log_panel.clear()

        self.card_atm.reset()
        self.card_ce.reset()
        self.card_pe.reset()
        self.card_straddle.reset()
        self.card_edge.reset()

        self.badge_status.setText("🟢 ENGINE READY")
        self.badge_status.setStyleSheet("""
            background-color: #0D1527;
            color: #10B981;
            border: 1px solid #064E3B;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
        """)

        self.badge_ticker.setText("NIFTY 50 • SPOT: AWAITING LOAD")
        self.txt_playbook.setText("Run quantitative analysis to generate real-time trade signals and strategy playbook recommendations.")

        self.btn_export.setEnabled(False)
        self.statusBar().showMessage("Engine Reset Complete • Ready for Analysis")
        self._update_process_button_state()

    # ------------------------------------------------------------------
    # Validation & Utilities
    # ------------------------------------------------------------------
    def _validate_inputs(self) -> bool:
        if not self.current_day_files:
            self._show_error("Please upload at least one current-day data file.")
            return False
        if not self.historical_files:
            self._show_error("Please upload at least one historical Bhavcopy file.")
            return False
        if not self.combo_symbol.currentText().strip():
            self._show_error("Please enter or select a ticker Symbol.")
            return False
        if not self.combo_expiry.currentText().strip():
            self._show_error("Please enter or select an Expiry Date.")
            return False
        return True

    def _update_process_button_state(self) -> None:
        ready = (
            bool(self.current_day_files)
            and bool(self.historical_files)
            and bool(self.combo_symbol.currentText().strip())
            and bool(self.combo_expiry.currentText().strip())
        )
        self.btn_process.setEnabled(ready)

    def _filter_valid_paths(self, paths: List[str]) -> List[str]:
        invalid = [p for p in paths if os.path.splitext(p)[1].lower() not in SUPPORTED_DATA_EXTENSIONS]
        if invalid:
            self._show_error(
                "Unsupported file type(s) skipped:\n" + "\n".join(os.path.basename(p) for p in invalid)
            )
        return [p for p in paths if p not in invalid]

    @staticmethod
    def _add_files(target_list: List[str], new_paths: List[str]) -> int:
        existing = set(target_list)
        added = 0
        for p in new_paths:
            if p not in existing:
                target_list.append(p)
                existing.add(p)
                added += 1
        return added

    @staticmethod
    def _refresh_file_list(list_widget: QListWidget, paths: List[str]) -> None:
        list_widget.clear()
        list_widget.addItems([os.path.basename(p) for p in paths])

    def _remove_selected(self, list_widget: QListWidget, backing_list: List[str]) -> int:
        selected_rows = sorted({idx.row() for idx in list_widget.selectedIndexes()}, reverse=True)
        if not selected_rows:
            self._show_error("Select one or more files in the list first.")
            return 0
        for row in selected_rows:
            del backing_list[row]
        self._refresh_file_list(list_widget, backing_list)
        return len(selected_rows)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def _log(self, message: str) -> None:
        logger.info(message)
        self.log_panel.append(message)
