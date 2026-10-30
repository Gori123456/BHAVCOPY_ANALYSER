"""
data_loader.py
---------------
Responsible purely for I/O: reading CSV / Excel files into pandas
DataFrames. Contains no filtering / analysis logic, so it can be
reused (or swapped, e.g. for a database source) without touching the
processing layer.
"""

import logging
import os
import re
from typing import Dict, List, Tuple

import pandas as pd

from config.constants import BhavcopyColumns as C, COLUMN_ALIASES, SUPPORTED_DATA_EXTENSIONS

logger = logging.getLogger("fno_analyzer")


class DataLoadError(Exception):
    """Raised when a file cannot be read at all (bad path, corrupt file, etc.)."""


def _simplify(header: str) -> str:
    """Lowercase + strip everything except letters/digits, for fuzzy header matching."""
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


def normalize_columns(df: pd.DataFrame, source_name: str = "") -> pd.DataFrame:
    """
    Rename any recognized alias column (see COLUMN_ALIASES in constants.py)
    to its canonical Bhavcopy name, so downstream filtering/analysis code
    can rely on one consistent schema regardless of which NSE report
    format (or broker export) the file came from.

    Unrecognized columns are left untouched. If a file already uses the
    canonical UDIFF names, this is a no-op for those columns.
    """
    alias_lookup = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lookup[_simplify(alias)] = canonical

    rename_map = {}
    applied = []
    for col in df.columns:
        key = _simplify(col)
        canonical = alias_lookup.get(key)
        if canonical and canonical not in df.columns and col != canonical:
            rename_map[col] = canonical
            applied.append(f"'{col}' -> '{canonical}'")

    if rename_map:
        df = df.rename(columns=rename_map)
        logger.info(
            "Column mapping applied for '%s': %s",
            source_name or "file", ", ".join(applied),
        )

    return df


def _read_single_file(filepath: str) -> pd.DataFrame:
    """Read one CSV or Excel file into a DataFrame with normalized column headers."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext not in SUPPORTED_DATA_EXTENSIONS:
        raise DataLoadError(
            f"Unsupported file type '{ext}' for file: {os.path.basename(filepath)}"
        )

    try:
        if ext == ".csv":
            df = pd.read_csv(filepath, low_memory=False)
        else:  # .xlsx / .xls
            df = pd.read_excel(filepath, engine="openpyxl" if ext == ".xlsx" else None)
    except Exception as exc:  # noqa: BLE001
        raise DataLoadError(f"Failed to read '{os.path.basename(filepath)}': {exc}") from exc

    df.columns = [str(c).strip() for c in df.columns]
    df = normalize_columns(df, source_name=os.path.basename(filepath))
    return df


def load_current_day_files(filepaths: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """Load and concatenate one or more current day files."""
    frames = []
    errors: List[str] = []

    for path in filepaths:
        try:
            df = _read_single_file(path)
            df["__source_file__"] = os.path.basename(path)
            frames.append(df)
            logger.info("Loaded current-day file '%s' (%d rows)", os.path.basename(path), len(df))
        except DataLoadError as exc:
            logger.error(str(exc))
            errors.append(str(exc))

    if not frames:
        return pd.DataFrame(), errors

    combined = pd.concat(frames, ignore_index=True, sort=False)
    return combined, errors


def load_historical_files(filepaths: List[str]) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
    """Load each historical Bhavcopy file separately into a dict keyed by filename."""
    file_frames: Dict[str, pd.DataFrame] = {}
    errors: List[str] = []

    for path in filepaths:
        filename = os.path.basename(path)
        try:
            df = _read_single_file(path)
            file_frames[filename] = df
            logger.info("Loaded historical file '%s' (%d rows)", filename, len(df))
        except DataLoadError as exc:
            logger.error(str(exc))
            errors.append(str(exc))

    return file_frames, errors


def extract_metadata_from_files(filepaths: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Inspect files to extract:
      1. Sorted list of all unique symbols
      2. Mapping of {symbol: [available_expiries_for_that_symbol]}
    This allows the GUI to only display expiries that actually exist for the selected symbol!
    """
    all_symbols = set()
    symbol_expiries_map: Dict[str, set] = {}

    for path in filepaths:
        try:
            df = _read_single_file(path)
            if C.TICKER_SYMBOL in df.columns and C.EXPIRY_DATE in df.columns:
                sub = df[[C.TICKER_SYMBOL, C.EXPIRY_DATE]].dropna()
                for sym, grp in sub.groupby(C.TICKER_SYMBOL):
                    sym_clean = str(sym).strip().upper()
                    if not sym_clean or sym_clean == "NAN":
                        continue
                    all_symbols.add(sym_clean)
                    exp_vals = grp[C.EXPIRY_DATE].dropna().astype(str).str.strip().unique()
                    if sym_clean not in symbol_expiries_map:
                        symbol_expiries_map[sym_clean] = set()
                    symbol_expiries_map[sym_clean].update([e for e in exp_vals if e and e != "NAN"])
        except Exception:
            continue

    mapping = {s: sorted(exps) for s, exps in symbol_expiries_map.items()}
    return sorted(all_symbols), mapping
