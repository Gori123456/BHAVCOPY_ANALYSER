"""
config_manager.py
------------------
Loads, saves, and validates configuration parameters, e.g.:

    {
        "symbol": "NIFTY",
        "expiry_date": "21-Jul-2026",
        "history_days": 7,
        "option_type": "CE"
    }

Can be loaded from or saved to JSON, or configured directly from the GUI dashboard.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.constants import DEFAULT_OPTION_TYPE

logger = logging.getLogger("fno_analyzer")


class ConfigError(Exception):
    """Raised when the configuration is missing, malformed, or invalid."""


@dataclass
class AppConfig:
    symbol: str
    expiry_date: str
    history_days: int
    option_type: str = DEFAULT_OPTION_TYPE
    strike_price: str = "Auto (ATM)"

    def __post_init__(self):
        # Normalize for consistent, case-insensitive matching downstream.
        self.symbol = str(self.symbol).strip().upper()
        self.option_type = str(self.option_type).strip().upper()
        self.strike_price = str(self.strike_price).strip()


REQUIRED_KEYS = ("symbol", "expiry_date", "history_days")


def load_config(json_path: str) -> AppConfig:
    """
    Read and validate the JSON configuration file.
    """
    path = Path(json_path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {json_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in configuration file: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read configuration file: {exc}") from exc

    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        raise ConfigError(f"Configuration is missing required key(s): {', '.join(missing)}")

    try:
        history_days = int(raw["history_days"])
    except (TypeError, ValueError) as exc:
        raise ConfigError("'history_days' must be an integer") from exc

    if history_days <= 0:
        raise ConfigError("'history_days' must be a positive integer")

    symbol = str(raw["symbol"]).strip()
    expiry_date = str(raw["expiry_date"]).strip()

    if not symbol:
        raise ConfigError("'symbol' cannot be empty")
    if not expiry_date:
        raise ConfigError("'expiry_date' cannot be empty")

    option_type: Optional[str] = raw.get("option_type", DEFAULT_OPTION_TYPE)

    config = AppConfig(
        symbol=symbol,
        expiry_date=expiry_date,
        history_days=history_days,
        option_type=option_type,
    )

    logger.info(
        "Configuration loaded: symbol=%s, expiry_date=%s, history_days=%d, option_type=%s",
        config.symbol, config.expiry_date, config.history_days, config.option_type,
    )
    return config


def save_config(config: AppConfig, json_path: str) -> None:
    """Save an AppConfig instance to a JSON file."""
    data = {
        "symbol": config.symbol,
        "expiry_date": config.expiry_date,
        "history_days": config.history_days,
        "option_type": config.option_type,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    logger.info("Configuration saved to '%s'", json_path)
