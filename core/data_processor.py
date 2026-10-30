"""
data_processor.py
------------------
All business logic for the analysis:

    1. Filter current-day data by symbol + expiry (with auto-fallback to nearest active expiry)
    2. Determine the ATM strike (with auto-snap to nearest available strike in historical files)
    3. Filter each historical file by symbol + expiry + strike (+ option type) with 3-tier flexible matching
    4. Compute Current / N-Day Avg / Max / Min statistics with data integrity checks
"""

import logging
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from config.constants import (
    BhavcopyColumns as C,
    FUTURES_INSTRUMENT_PREFIXES,
    PRICE_STAT_FIELDS,
)
from core.models import AnalysisResult, FieldStats, ProcessingWarning

logger = logging.getLogger("fno_analyzer")


class ProcessingError(Exception):
    """Raised for unrecoverable data problems."""


# --------------------------------------------------------------------------
# Step 1: Filter current day data (with smart active expiry fallback)
# --------------------------------------------------------------------------
def filter_current_day(
    df: pd.DataFrame, symbol: str, expiry_date: str
) -> Tuple[pd.DataFrame, str, Optional[str]]:
    """
    Filter current-day DataFrame by TckrSymb and XpryDt.
    If requested expiry_date is expired or not present, automatically snaps to the
    nearest active contract expiry on or after current trade date.

    Returns:
        (filtered_df, effective_expiry_date, optional_warning_msg)
    """
    _require_columns(df, [C.TICKER_SYMBOL, C.EXPIRY_DATE, C.STRIKE_PRICE], "current-day data")

    sym_mask = df[C.TICKER_SYMBOL].astype(str).str.strip().str.upper() == symbol.upper()
    sym_rows = df.loc[sym_mask].copy()

    if sym_rows.empty:
        avail_syms = df[C.TICKER_SYMBOL].dropna().astype(str).str.strip().unique()[:6]
        raise ProcessingError(
            f"Symbol '{symbol}' was not found in the current-day file.\n"
            f"Available symbols include: {', '.join(avail_syms)}..."
        )

    normalized_expiry = _normalize_date_series(sym_rows[C.EXPIRY_DATE])
    target_expiry = _normalize_date_string(expiry_date)

    match_mask = normalized_expiry == target_expiry
    filtered = sym_rows.loc[match_mask].copy()

    effective_expiry = target_expiry
    warning_msg = None

    if filtered.empty:
        # Expiry not found in current day file (e.g. user selected an expired date or different week)
        # Find the earliest active expiry on or after the trade date
        curr_trade_dt = None
        if C.TRADE_DATE in sym_rows.columns:
            t_dates = sym_rows[C.TRADE_DATE].dropna()
            if not t_dates.empty:
                curr_trade_dt = pd.to_datetime(t_dates.iloc[0], errors="coerce", format="mixed")

        exp_parsed = pd.to_datetime(sym_rows[C.EXPIRY_DATE], errors="coerce", format="mixed")
        if curr_trade_dt is not None:
            active_exps = exp_parsed[exp_parsed >= curr_trade_dt]
            if not active_exps.empty:
                best_dt = active_exps.min()
            else:
                best_dt = exp_parsed.min()
        else:
            best_dt = exp_parsed.min()

        best_exp_str = best_dt.strftime("%Y-%m-%d")
        filtered = sym_rows.loc[normalized_expiry == best_exp_str].copy()
        effective_expiry = best_exp_str

        warning_msg = (
            f"Requested expiry '{expiry_date}' was not found/expired in current-day file. "
            f"Automatically selected nearest active contract expiry '{best_exp_str}'."
        )
        logger.warning(warning_msg)

    if filtered.empty:
        raise ProcessingError(f"No usable contract rows found for symbol='{symbol}' in current-day file.")

    logger.info("Current-day data filtered to %d rows for %s / %s", len(filtered), symbol, effective_expiry)
    return filtered, effective_expiry, warning_msg


# --------------------------------------------------------------------------
# Step 2: Determine ATM strike (Accuracy Enhanced)
# --------------------------------------------------------------------------
def determine_atm_strike(df: pd.DataFrame) -> Tuple[float, float, str]:
    """
    Determine the At-The-Money strike: the strike price closest to the
    current underlying / futures market price.
    """
    strikes = pd.to_numeric(df[C.STRIKE_PRICE], errors="coerce").dropna().unique()
    if len(strikes) == 0:
        raise ProcessingError("No valid strike prices found in the current-day data.")

    reference_price, source_desc = _resolve_underlying_price(df)

    if reference_price is None or reference_price <= 0:
        reference_price = float(pd.Series(strikes).median())
        source_desc = "Median of Available Strikes (Fallback)"
        logger.warning(
            "Underlying price not found or zero; falling back to median strike (%.2f) "
            "as ATM reference. Results may be approximate.",
            reference_price,
        )

    atm_strike = min(strikes, key=lambda s: abs(s - reference_price))
    logger.info("Reference price=%.2f (%s) -> ATM strike determined as %.2f", reference_price, source_desc, atm_strike)
    return float(atm_strike), float(reference_price), source_desc


def _resolve_underlying_price(df: pd.DataFrame) -> Tuple[Optional[float], str]:
    """Resolves reference spot price, filtering out zero/negative unpopulated rows."""
    if C.UNDERLYING_PRICE in df.columns:
        values = pd.to_numeric(df[C.UNDERLYING_PRICE], errors="coerce").dropna()
        positive_values = values[values > 0]
        if not positive_values.empty:
            return float(positive_values.median()), "Underlying Spot Price (UndrlygPric)"

    if C.INSTRUMENT_TYPE in df.columns and C.CLOSE_PRICE in df.columns:
        instrument = df[C.INSTRUMENT_TYPE].astype(str).str.upper()
        futures_mask = instrument.str.startswith(FUTURES_INSTRUMENT_PREFIXES)
        futures_rows = df.loc[futures_mask].copy()

        if not futures_rows.empty:
            futures_rows[C.CLOSE_PRICE] = pd.to_numeric(futures_rows[C.CLOSE_PRICE], errors="coerce")
            valid_fut = futures_rows.dropna(subset=[C.CLOSE_PRICE])
            valid_fut = valid_fut[valid_fut[C.CLOSE_PRICE] > 0]

            if not valid_fut.empty:
                if C.EXPIRY_DATE in valid_fut.columns:
                    exp_dates = pd.to_datetime(valid_fut[C.EXPIRY_DATE], errors="coerce", format="mixed")
                    if exp_dates.notna().any():
                        near_month_rows = valid_fut.loc[exp_dates == exp_dates.min()]
                        if not near_month_rows.empty:
                            return float(near_month_rows[C.CLOSE_PRICE].mean()), "Near-Month Futures Close Price"

                return float(valid_fut[C.CLOSE_PRICE].mean()), "Futures Close Price"

    return None, "Not Found"


# --------------------------------------------------------------------------
# Step 3: Progressive 3-Tier Filter for Historical Files
# --------------------------------------------------------------------------
def filter_historical_file_flexible(
    df: pd.DataFrame,
    symbol: str,
    expiry_date: str,
    strike_price: float,
    option_type: str,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Progressively filter historical file down to the target contract data:
      Tier 1: Exact Symbol + Exact Expiry + Exact Strike + Option Type
      Tier 2: Exact Symbol + Exact Expiry + Nearest Strike + Option Type
      Tier 3: Exact Symbol + Available Historical Expiry + Nearest Strike + Option Type (Cross-Contract Baseline)

    Returns:
        (filtered_df, match_type_note_or_None)
    """
    _require_columns(df, [C.TICKER_SYMBOL, C.STRIKE_PRICE], "historical data")

    sym_mask = df[C.TICKER_SYMBOL].astype(str).str.strip().str.upper() == symbol.upper()
    df_sym = df.loc[sym_mask].copy()

    if df_sym.empty:
        return pd.DataFrame(), None

    # Filter by Option Type (if present)
    if C.OPTION_TYPE in df_sym.columns:
        opt_mask = df_sym[C.OPTION_TYPE].astype(str).str.strip().str.upper() == option_type.upper()
        df_opt = df_sym.loc[opt_mask].copy()
        if not df_opt.empty:
            df_sym = df_opt

    target_exp_norm = _normalize_date_string(expiry_date)
    has_expiry = C.EXPIRY_DATE in df_sym.columns

    # --- Tier 1 & 2: Same Expiry ---
    if has_expiry:
        exp_norm_series = _normalize_date_series(df_sym[C.EXPIRY_DATE])
        df_exp = df_sym.loc[exp_norm_series == target_exp_norm].copy()

        if not df_exp.empty:
            s_num = pd.to_numeric(df_exp[C.STRIKE_PRICE], errors="coerce")
            # Tier 1: Exact Strike
            exact_mask = s_num.round(2) == round(strike_price, 2)
            df_exact = df_exp.loc[exact_mask]
            if not df_exact.empty:
                return df_exact, "Exact Contract Match"

            # Tier 2: Nearest Strike in same expiry
            valid_s = s_num.dropna().unique()
            if len(valid_s) > 0:
                closest_s = min(valid_s, key=lambda s: abs(s - strike_price))
                df_closest = df_exp.loc[s_num.round(2) == round(closest_s, 2)]
                return df_closest, f"Same Expiry, Nearest Strike ({closest_s})"

    # --- Tier 3: Cross-Contract Baseline (Different Expiry in Historical File) ---
    # This ensures that ANY historical file uploaded with ANY current day file works!
    if has_expiry:
        avail_exps = df_sym[C.EXPIRY_DATE].dropna().unique()
        if len(avail_exps) > 0:
            hist_exp_choice = avail_exps[0]
            df_exp = df_sym.loc[df_sym[C.EXPIRY_DATE] == hist_exp_choice].copy()
        else:
            df_exp = df_sym
            hist_exp_choice = "undated"
    else:
        df_exp = df_sym
        hist_exp_choice = "undated"

    s_num = pd.to_numeric(df_exp[C.STRIKE_PRICE], errors="coerce")
    valid_s = s_num.dropna().unique()

    if len(valid_s) > 0:
        closest_s = min(valid_s, key=lambda s: abs(s - strike_price))
        df_res = df_exp.loc[s_num.round(2) == round(closest_s, 2)]
        return df_res, f"Cross-Contract Baseline (Expiry: {hist_exp_choice}, Strike: {closest_s})"
    else:
        return df_exp, "Historical Fallback"


# --------------------------------------------------------------------------
# Step 4: Statistics
# --------------------------------------------------------------------------
def compute_field_stats(current_value: float, historical_values: List[float]) -> FieldStats:
    """Compute Current / Average / Max / Min for one price field."""
    series = pd.Series(historical_values, dtype="float64").dropna()
    return FieldStats(
        current=round(float(current_value), 2) if pd.notna(current_value) else float("nan"),
        average=round(float(series.mean()), 2) if not series.empty else float("nan"),
        maximum=round(float(series.max()), 2) if not series.empty else float("nan"),
        minimum=round(float(series.min()), 2) if not series.empty else float("nan"),
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def run_analysis(
    current_day_df: pd.DataFrame,
    historical_frames: Dict[str, pd.DataFrame],
    symbol: str,
    expiry_date: str,
    history_days: int,
    option_type: str,
    target_strike: Optional[Union[float, str]] = None,
    progress_callback=None,
) -> Tuple[List[AnalysisResult], List[ProcessingWarning]]:
    """Run the analysis pipeline end-to-end with universal file resilience."""
    warnings: List[ProcessingWarning] = []

    def _report(pct: int, msg: str):
        logger.debug(msg)
        if progress_callback:
            progress_callback(pct, msg)

    _report(5, "Filtering current-day data...")
    current_filtered, effective_expiry, exp_warn = filter_current_day(current_day_df, symbol, expiry_date)
    if exp_warn:
        warnings.append(ProcessingWarning(source="Expiry Adaptation", message=exp_warn))

    _report(20, "Determining ATM strike...")
    calculated_atm_strike, reference_price, ref_source = determine_atm_strike(current_filtered)

    # Resolve manual or auto strike
    manual_strike_val = None
    if target_strike is not None and str(target_strike).strip().upper() not in ("", "AUTO", "ATM", "NONE", "AUTO (ATM)"):
        try:
            manual_strike_val = float(str(target_strike).strip())
        except (ValueError, TypeError):
            pass

    atm_strike = manual_strike_val if manual_strike_val is not None else calculated_atm_strike

    cleaned_opt = option_type.strip().upper()
    if "BOTH" in cleaned_opt or "ALL" in cleaned_opt or ("CE" in cleaned_opt and "PE" in cleaned_opt):
        target_types = ["CE", "PE"]
    elif "PE" in cleaned_opt:
        target_types = ["PE"]
    else:
        target_types = ["CE"]

    current_trade_date_str = None
    if C.TRADE_DATE in current_filtered.columns:
        c_dates = current_filtered[C.TRADE_DATE].dropna()
        if not c_dates.empty:
            parsed_c_date = pd.to_datetime(c_dates.iloc[0], errors="coerce", format="mixed")
            if pd.notna(parsed_c_date):
                current_trade_date_str = parsed_c_date.strftime("%Y-%m-%d")

    results: List[AnalysisResult] = []

    for opt_idx, opt_type in enumerate(target_types):
        _report(
            30 + opt_idx * 30,
            f"Analyzing Strike {atm_strike} ({opt_type}) [Ref Spot: {reference_price:.2f}]...",
        )

        # Match current day row for this strike and option type
        s_num_curr = pd.to_numeric(current_filtered[C.STRIKE_PRICE], errors="coerce")
        opt_mask_curr = current_filtered[C.OPTION_TYPE].astype(str).str.strip().str.upper() == opt_type.upper()
        current_atm_rows = current_filtered.loc[(s_num_curr.round(2) == round(atm_strike, 2)) & opt_mask_curr]

        if current_atm_rows.empty:
            # Snap to closest available strike in current day if needed
            valid_curr_strikes = s_num_curr[opt_mask_curr].dropna().unique()
            if len(valid_curr_strikes) > 0:
                alt_strike = min(valid_curr_strikes, key=lambda s: abs(s - atm_strike))
                current_atm_rows = current_filtered.loc[(s_num_curr.round(2) == round(alt_strike, 2)) & opt_mask_curr]
                warnings.append(
                    ProcessingWarning(
                        source=f"Current Day Strike Adjustment ({opt_type})",
                        message=f"Strike {atm_strike} was not populated in today's data. Snapped to nearest strike {alt_strike}.",
                    )
                )

        if current_atm_rows.empty:
            warnings.append(
                ProcessingWarning(
                    source="Current Day Data",
                    message=f"Strike {atm_strike} found, but no matching row for option_type='{opt_type}'.",
                )
            )
            continue

        current_row = current_atm_rows.iloc[0]

        # Liquidity Check
        if C.TOTAL_TRADED_VOLUME in current_atm_rows.columns:
            vol = pd.to_numeric(current_atm_rows[C.TOTAL_TRADED_VOLUME], errors="coerce").fillna(0).sum()
            if vol == 0:
                warnings.append(
                    ProcessingWarning(
                        source=f"Liquidity Check ({opt_type})",
                        message=f"Strike {atm_strike} ({opt_type}) had 0 volume traded today. "
                                "Prices may represent settlement/previous close rather than active execution.",
                    )
                )

        # Process historical files using the progressive 3-tier matcher
        dated_rows = []
        field_history: Dict[str, List[float]] = {label: [] for label in PRICE_STAT_FIELDS}

        for f_idx, (filename, hist_df) in enumerate(historical_frames.items(), start=1):
            try:
                matched, match_note = filter_historical_file_flexible(
                    hist_df, symbol, effective_expiry, atm_strike, opt_type
                )
            except ProcessingError as exc:
                warnings.append(ProcessingWarning(source=filename, message=str(exc)))
                continue

            if matched.empty:
                warnings.append(
                    ProcessingWarning(
                        source=filename,
                        message=f"No rows matched symbol='{symbol}' for type='{opt_type}' in this file.",
                    )
                )
                continue

            if match_note and "Cross-Contract" in match_note:
                warnings.append(
                    ProcessingWarning(
                        source=filename,
                        message=f"Using historical data: {match_note}.",
                    )
                )

            if C.TRADE_DATE in matched.columns:
                matched = matched.drop_duplicates(subset=[C.TRADE_DATE], keep="first")

            for _, row in matched.iterrows():
                trade_date = row.get(C.TRADE_DATE, None)
                dated_rows.append((trade_date, filename, row))

        # Deduplicate & exclude current day from historical pool
        seen_dates = set()
        deduped = []
        for trade_date, filename, row in dated_rows:
            parsed = pd.to_datetime(trade_date, errors="coerce", format="mixed") if trade_date is not None else pd.NaT
            if pd.notna(parsed):
                key = parsed.strftime("%Y-%m-%d")

                if current_trade_date_str and key == current_trade_date_str:
                    warnings.append(
                        ProcessingWarning(
                            source=filename,
                            message=f"Date '{trade_date}' in historical file matches current day "
                                    f"({current_trade_date_str}) and was excluded to maintain a pure historical average.",
                        )
                    )
                    continue

                if key in seen_dates:
                    warnings.append(
                        ProcessingWarning(
                            source=filename,
                            message=f"Trading day '{trade_date}' was already found in another file; duplicate row excluded.",
                        )
                    )
                    continue
                seen_dates.add(key)

            deduped.append((trade_date, filename, row))

        dated_rows = deduped

        if not dated_rows:
            warnings.append(
                ProcessingWarning(
                    source=f"Historical Files ({opt_type})",
                    message=f"No historical rows found for strike {atm_strike} ({opt_type}).",
                )
            )
            continue

        def _sort_key(entry):
            t_date = entry[0]
            parsed = pd.to_datetime(t_date, errors="coerce", format="mixed") if t_date is not None else pd.NaT
            return (pd.isna(parsed), parsed if pd.notna(parsed) else pd.Timestamp.min)

        dated_rows.sort(key=_sort_key)

        if len(dated_rows) > history_days:
            skipped = dated_rows[:-history_days]
            dated_rows = dated_rows[-history_days:]
            for trade_date, filename, _ in skipped:
                day_label = trade_date if trade_date is not None else "unknown date"
                warnings.append(
                    ProcessingWarning(
                        source=filename,
                        message=f"More trading day(s) matched than history_days={history_days}; "
                                f"day '{day_label}' was excluded (oldest first).",
                    )
                )
        elif len(dated_rows) < history_days:
            warnings.append(
                ProcessingWarning(
                    source=f"Configuration ({opt_type})",
                    message=f"Only {len(dated_rows)} historical trading day(s) found for {opt_type}, "
                            f"statistics reflect the available days.",
                )
            )

        days_used = len(dated_rows)
        for _, _, row in dated_rows:
            for label, column in PRICE_STAT_FIELDS.items():
                value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
                field_history[label].append(value)

        field_stats = {}
        for label, column in PRICE_STAT_FIELDS.items():
            current_value = pd.to_numeric(pd.Series([current_row.get(column)]), errors="coerce").iloc[0]
            field_stats[label] = compute_field_stats(current_value, field_history[label])

        res = AnalysisResult(
            strike_price=atm_strike,
            symbol=symbol,
            expiry_date=effective_expiry,
            option_type=opt_type,
            days_used=days_used,
            underlying_price=reference_price,
            field_stats=field_stats,
        )
        results.append(res)

    if not results:
        raise ProcessingError(
            f"No matching rows could be evaluated for symbol='{symbol}' with the provided files. "
            "Please check that both files contain data for the specified symbol."
        )

    _report(100, "Analysis complete.")
    return results, warnings


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _require_columns(df: pd.DataFrame, columns: List[str], context: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ProcessingError(
            f"Missing required column(s) {missing} in {context}. "
            f"Available columns: {list(df.columns)}"
        )


def _normalize_date_series(series: pd.Series) -> pd.Series:
    """Normalize a column of dates to 'YYYY-MM-DD' strings for comparison."""
    parsed = pd.to_datetime(series.astype(str).str.strip(), errors="coerce", format="mixed")
    return parsed.dt.strftime("%Y-%m-%d")


def _normalize_date_string(date_str: str) -> str:
    parsed = pd.to_datetime(str(date_str).strip(), errors="coerce", format="mixed")
    if pd.isna(parsed):
        raise ProcessingError(f"Could not parse expiry_date '{date_str}'. Use a format like '21-Jul-2026'.")
    return parsed.strftime("%Y-%m-%d")
