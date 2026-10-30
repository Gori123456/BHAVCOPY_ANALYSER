"""
models.py
---------
Lightweight data structures passed between the loader, processor, and
GUI layers. Using dataclasses instead of raw dicts/tuples keeps the
contract between layers explicit and IDE-friendly.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import pandas as pd


@dataclass
class LoadedFile:
    """A single file that was successfully loaded into a DataFrame."""
    filename: str
    filepath: str
    row_count: int


@dataclass
class FieldStats:
    """Current / Average / Max / Min statistics for one price field."""
    current: float
    average: float
    maximum: float
    minimum: float


@dataclass
class AnalysisResult:
    """Final quantitative analytical result for an option contract."""
    strike_price: float
    symbol: str
    expiry_date: str
    option_type: str
    days_used: int
    underlying_price: float = 0.0
    field_stats: Dict[str, FieldStats] = field(default_factory=dict)

    def to_flat_dict(self) -> Dict[str, object]:
        """Flatten into an institutional quantitative trading layout."""
        strike_val = int(self.strike_price) if self.strike_price.is_integer() else self.strike_price

        # Calculate Valuation % (Close vs Historical Avg)
        close_stats = self.field_stats.get("Close")
        if close_stats and pd.notna(close_stats.current) and pd.notna(close_stats.average) and close_stats.average > 0:
            diff_pct = ((close_stats.current - close_stats.average) / close_stats.average) * 100
            diff_pct = round(diff_pct, 2)
        else:
            diff_pct = 0.0

        # Actionable Quantitative Edge Signal
        if diff_pct >= 25.0:
            signal = "SELL EDGE - Overpriced"
        elif diff_pct <= -20.0:
            signal = "BUY EDGE - Underpriced"
        else:
            signal = "NEUTRAL - Fair Value"

        row: Dict[str, object] = {
            "Contract": f"{self.symbol} {self.option_type}",
            "Strike": strike_val,
            "Expiry": self.expiry_date,
            "Current Close": close_stats.current if close_stats else float("nan"),
            f"Hist Avg ({self.days_used}D)": close_stats.average if close_stats else float("nan"),
            "Valuation %": diff_pct,
            "Quant Edge": signal,
        }

        # Detailed OHLC fields
        for label in ("Open", "High", "Low"):
            stats = self.field_stats.get(label)
            if stats is None:
                continue
            row[f"Current {label}"] = stats.current
            row[f"Avg {label}"] = stats.average

        # Historical Boundaries (Range limits)
        if close_stats:
            row["Hist Max Close"] = close_stats.maximum
            row["Hist Min Close"] = close_stats.minimum

        return row


@dataclass
class ProcessingWarning:
    """Non-fatal issue encountered during processing (surfaced to the user)."""
    source: str
    message: str


@dataclass
class ProcessingOutcome:
    """Everything the GUI needs after a processing run completes."""
    results: List[AnalysisResult]
    warnings: List[ProcessingWarning] = field(default_factory=list)
