"""
worker.py
---------
Runs the (potentially slow) file loading + analysis pipeline on a
background QThread so the UI stays responsive and the progress bar
can be updated in real time.
"""

import logging
from typing import Dict, List

from PySide6.QtCore import QThread, Signal

from core.data_loader import load_current_day_files, load_historical_files
from core.data_processor import run_analysis, ProcessingError
from core.models import AnalysisResult, ProcessingWarning

logger = logging.getLogger("fno_analyzer")


class AnalysisWorker(QThread):
    """
    Executes: load current-day files -> load historical files -> run_analysis()

    Signals:
        progress(int, str): percentage complete, status message
        finished_ok(AnalysisResult, list[ProcessingWarning]): success
        failed(str): a fatal error message (already formatted for display)
    """

    progress = Signal(int, str)
    finished_ok = Signal(object, object)  # AnalysisResult, List[ProcessingWarning]
    failed = Signal(str)

    def __init__(
        self,
        current_day_paths: List[str],
        historical_paths: List[str],
        symbol: str,
        expiry_date: str,
        history_days: int,
        option_type: str,
        target_strike: str = "Auto (ATM)",
        parent=None,
    ):
        super().__init__(parent)
        self.current_day_paths = current_day_paths
        self.historical_paths = historical_paths
        self.symbol = symbol
        self.expiry_date = expiry_date
        self.history_days = history_days
        self.option_type = option_type
        self.target_strike = target_strike

    def run(self) -> None:
        try:
            self.progress.emit(2, "Loading current-day files...")
            current_df, current_errors = load_current_day_files(self.current_day_paths)
            if current_df.empty:
                self.failed.emit(
                    "None of the current-day files could be loaded.\n"
                    + "\n".join(current_errors)
                )
                return

            self.progress.emit(10, "Loading historical files...")
            historical_frames, hist_errors = load_historical_files(self.historical_paths)
            if not historical_frames:
                self.failed.emit(
                    "None of the historical files could be loaded.\n" + "\n".join(hist_errors)
                )
                return

            result, warnings = run_analysis(
                current_day_df=current_df,
                historical_frames=historical_frames,
                symbol=self.symbol,
                expiry_date=self.expiry_date,
                history_days=self.history_days,
                option_type=self.option_type,
                target_strike=self.target_strike,
                progress_callback=lambda pct, msg: self.progress.emit(pct, msg),
            )

            # Surface file-load errors as warnings too, so nothing is silently dropped.
            for err in current_errors + hist_errors:
                warnings.append(ProcessingWarning(source="file loading", message=err))

            self.finished_ok.emit(result, warnings)

        except ProcessingError as exc:
            logger.error("Processing error: %s", exc)
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - last line of defense, never crash silently
            logger.exception("Unexpected error during processing")
            self.failed.emit(f"Unexpected error: {exc}")
