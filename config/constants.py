"""
constants.py
------------
Central place for all "magic strings" used across the application:
    * NSE F&O UDIFF Bhavcopy column names
    * Default application settings

Keeping these in one module means that if NSE ever changes a column
name (it has happened before, e.g. the 2024 UDIFF format change),
only this file needs to be updated -- no business logic changes
required. This directly supports the "scalable / easy to extend"
requirement.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BhavcopyColumns:
    """Column names as they appear in the NSE F&O UDIFF Common Bhavcopy file."""

    TICKER_SYMBOL: str = "TckrSymb"
    EXPIRY_DATE: str = "XpryDt"
    STRIKE_PRICE: str = "StrkPric"
    OPTION_TYPE: str = "OptnTp"          # CE / PE / XX (futures)
    INSTRUMENT_TYPE: str = "FinInstrmTp"  # e.g. IDO, STO, IDF, STF
    TRADE_DATE: str = "TradDt"

    OPEN_PRICE: str = "OpnPric"
    HIGH_PRICE: str = "HghPric"
    LOW_PRICE: str = "LwPric"
    CLOSE_PRICE: str = "ClsPric"
    LAST_PRICE: str = "LastPric"
    PREV_CLOSE_PRICE: str = "PrvsClsgPric"
    SETTLEMENT_PRICE: str = "SttlmPric"
    UNDERLYING_PRICE: str = "UndrlygPric"

    OPEN_INTEREST: str = "OpnIntrst"
    CHANGE_IN_OI: str = "ChngInOpnIntrst"
    TOTAL_TRADED_VOLUME: str = "TtlTradgVol"
    TOTAL_TRADED_VALUE: str = "TtlTrfVal"


# --------------------------------------------------------------------------
# Column alias mapping
# --------------------------------------------------------------------------
# NSE publishes F&O data in more than one column-naming scheme depending on
# the report: the newer UDIFF Common Bhavcopy uses short codes like
# "TckrSymb"/"XpryDt"/"StrkPric", while the older "Derivatives" style reports
# (and many broker exports) use readable headers like "Symbol"/"Expiry"/
# "Strike Price". Rather than forcing the user to rename columns by hand,
# the loader normalizes any recognized alias to the canonical name below
# before filtering/analysis runs. To support a new source file's headers,
# just add the alias string here -- no other code changes needed.
#
# Matching is done on a simplified key: lowercase, alphanumeric characters
# only (spaces, punctuation, currency symbols, asterisks etc. stripped).
# e.g. "Turnover * in ₹ Lakhs" -> "turnoverinlakhs", "No. of contracts" ->
# "noofcontracts".
COLUMN_ALIASES = {
    BhavcopyColumns.TICKER_SYMBOL: ["tckrsymb", "symbol", "tickersymbol", "sym"],
    BhavcopyColumns.TRADE_DATE: ["traddt", "date", "tradedate", "bizdt", "businessdate"],
    BhavcopyColumns.EXPIRY_DATE: ["xprydt", "expiry", "expirydate", "expdate"],
    BhavcopyColumns.STRIKE_PRICE: ["strkpric", "strikeprice", "strike"],
    BhavcopyColumns.OPTION_TYPE: ["optntp", "optiontype", "type"],
    BhavcopyColumns.INSTRUMENT_TYPE: ["fininstrmtp", "instrumenttype", "instrument"],
    BhavcopyColumns.OPEN_PRICE: ["opnpric", "open"],
    BhavcopyColumns.HIGH_PRICE: ["hghpric", "high"],
    BhavcopyColumns.LOW_PRICE: ["lwpric", "low"],
    BhavcopyColumns.CLOSE_PRICE: ["clspric", "close"],
    BhavcopyColumns.LAST_PRICE: ["lastpric", "ltp", "lasttradedprice"],
    BhavcopyColumns.PREV_CLOSE_PRICE: ["prvsclsgpric", "previousclose", "prevclose"],
    BhavcopyColumns.SETTLEMENT_PRICE: ["sttlmpric", "settleprice", "settlementprice"],
    BhavcopyColumns.UNDERLYING_PRICE: ["undrlygpric", "underlyingvalue", "underlyingprice", "underlying"],
    BhavcopyColumns.OPEN_INTEREST: ["opnintrst", "openint", "openinterest", "oi"],
    BhavcopyColumns.CHANGE_IN_OI: ["chnginopnintrst", "changeinoi", "oichange"],
    BhavcopyColumns.TOTAL_TRADED_VOLUME: ["ttltradgvol", "noofcontracts", "totaltradedvolume", "volume", "contracts"],
    BhavcopyColumns.TOTAL_TRADED_VALUE: ["ttltrfval", "turnoverinrslakhs", "turnover", "turnoverlakhs"],
}


# Fields for which we calculate Current / 7-Day Avg / Max / Min statistics.
# Adding a new field here (e.g. Open Interest) automatically flows through
# the processor and results table without touching business logic.
PRICE_STAT_FIELDS = {
    "Open": BhavcopyColumns.OPEN_PRICE,
    "High": BhavcopyColumns.HIGH_PRICE,
    "Low": BhavcopyColumns.LOW_PRICE,
    "Close": BhavcopyColumns.CLOSE_PRICE,
}

# Instrument-type prefixes that represent Futures contracts (used as a
# fallback source of underlying price when UndrlygPric is not populated).
FUTURES_INSTRUMENT_PREFIXES = ("IDF", "STF", "FUTIDX", "FUTSTK")

DEFAULT_OPTION_TYPE = "CE"  # Used when config does not specify option_type
SUPPORTED_DATA_EXTENSIONS = (".csv", ".xlsx", ".xls")

APP_NAME = "F&O UDIFF Bhavcopy Analyzer"
APP_VERSION = "1.0.0"
LOG_DIR = "logs"
LOG_FILE = "fno_analyzer.log"
