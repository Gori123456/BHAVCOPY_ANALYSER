"""
exporter.py
-----------
Handles writing the AnalysisResult (or List[AnalysisResult]) out to an
Excel file using pandas + openpyxl. Kept separate from the processor
so additional export formats can be added later as sibling functions.
"""

import logging
from typing import List, Union

import pandas as pd

from core.models import AnalysisResult

logger = logging.getLogger("fno_analyzer")


class ExportError(Exception):
    """Raised when the result cannot be written to disk."""


def export_result_to_excel(result_input: Union[AnalysisResult, List[AnalysisResult]], filepath: str) -> None:
    """Write AnalysisResult or List[AnalysisResult] to an .xlsx file."""
    try:
        results: List[AnalysisResult] = result_input if isinstance(result_input, list) else [result_input]
        if not results:
            raise ExportError("No results provided to export.")

        rows = [r.to_flat_dict() for r in results]
        df = pd.DataFrame(rows)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="ATM Analysis")

            first_res = results[0]
            types_str = ", ".join(r.option_type for r in results)
            meta = pd.DataFrame(
                {
                    "Field": [
                        "Symbol",
                        "Expiry Date",
                        "Option Type(s)",
                        "ATM Strike Price",
                        "Ref Spot / Futures Price",
                        "History Days Used",
                    ],
                    "Value": [
                        first_res.symbol,
                        first_res.expiry_date,
                        types_str,
                        first_res.strike_price,
                        first_res.underlying_price,
                        first_res.days_used,
                    ],
                }
            )
            meta.to_excel(writer, index=False, sheet_name="Run Info")

        logger.info("Results successfully exported to '%s'", filepath)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to export results: %s", exc)
        raise ExportError(f"Failed to export results to Excel: {exc}") from exc
