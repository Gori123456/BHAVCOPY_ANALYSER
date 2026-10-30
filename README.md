# F&O UDIFF Bhavcopy Analyzer & Institutional Derivatives Terminal

An institutional quantitative trading terminal for analyzing NSE F&O UDIFF Bhavcopy data.
It evaluates current-day option pricing against historical baselines at the ATM (At-The-Money) strike, revealing overpricing and underpricing regimes for profitable option selling and buying strategies.

## Two Ways to Run

### Option A: Modern Web Terminal Pro (Recommended for Best Visual Experience)
- **Direct 1-Click**: Double-click `launch_web_terminal.bat` or open `web_terminal.html` in Chrome/Edge.
- **Via Local Server**: Run `python run_web_terminal.py` (opens `http://localhost:8055/web_terminal.html`).
- **Features**: Live ticker tape, 5 real-world KPI cards, interactive Chart.js volatility corridor, drag-and-drop CSV parser, actionable Trade Playbook, and 1-click Excel export.

### Option B: Python Desktop Terminal (PySide6 Fusion Dark Mode)
```bash
python main.py
```

## 3. Documentation & Strategy Guides

* **[Quantitative Logic & Mathematics Explained](file:///d:/fno_bhavcopy_analyzer/QUANTITATIVE_LOGIC_AND_MATHEMATICS_EXPLAINED.md)**: Full breakdown of every mathematical operation, normalization formula, ATM calculation, statistical mean, breakevens, and risk parameters.
* **[How This Process Makes Money](file:///d:/fno_bhavcopy_analyzer/HOW_THIS_MAKES_MONEY_TRADING_STRATEGY.md)**: Institutional quantitative trading strategy playbook on mean-reversion, straddle arbitrage, and risk management.
* **[Data Download Guide](file:///d:/fno_bhavcopy_analyzer/DATA_DOWNLOAD_GUIDE.md)**: Step-by-step instructions on where and how to download official NSE Bhavcopy and historical files.
* **[Project Architecture & Code Structure](file:///d:/fno_bhavcopy_analyzer/PROJECT_EXPLANATION.md)**: Detailed breakdown of the Python codebase and module responsibilities.

## 4. Project Structure

```
fno_bhavcopy_analyzer/
├── main.py                  # Application entry point
├── config/
│   ├── constants.py         # Bhavcopy column names & app constants (edit here if NSE changes columns)
│   └── config_manager.py    # Loads/validates the JSON configuration file
├── core/
│   ├── models.py            # Dataclasses shared across layers
│   ├── data_loader.py       # CSV/Excel file reading (I/O only)
│   ├── data_processor.py    # Filtering, ATM strike logic, statistics (business logic)
│   └── exporter.py          # Excel export
├── gui/
│   ├── worker.py            # QThread background worker (keeps UI responsive)
│   └── main_window.py       # PySide6 main window
├── utils/
│   └── logger_setup.py      # Rotating file + console logging
├── sample_config.json       # Example configuration
├── requirements.txt
└── logs/                    # Created automatically at runtime
```

## 4. Configuration File

```json
{
    "symbol": "NIFTY",
    "expiry_date": "30-Jul-2026",
    "history_days": 7,
    "option_type": "CE"
}
```

- `symbol`, `expiry_date`, `history_days` are required (as per the original spec).
- `option_type` (`CE` or `PE`) is optional and defaults to `CE`. It is needed
  because a single strike price maps to two Bhavcopy rows (Call and Put); without
  it, "filter by StrkPric" alone would be ambiguous.

## 5. How the ATM Strike Is Determined

The app filters the current-day file(s) by `TckrSymb` + `XpryDt`, then finds the
strike price closest to the underlying market price, using this priority order:

1. Mean of the `UndrlygPric` column, if present.
2. Mean closing price of futures rows (`FinInstrmTp` starting with `IDF`/`STF`/
   `FUTIDX`/`FUTSTK`), if `UndrlygPric` is unavailable.
3. Median of all strikes in the file, as a last-resort fallback (a warning is
   logged/shown in this case, since it is an approximation).

## 6. Usage Flow

1. Click **Upload Current Day Files** and select today's data file(s) (.csv/.xlsx/.xls).
2. Click **Upload Historical Bhavcopy Files** and select your historical file(s).
   This is additive -- click it again to add more files without losing what's
   already selected (e.g. add one day at a time, or mix single-day files with
   a multi-day range file). Select rows in the list and click **Remove Selected**
   to drop specific files.
3. Click **Load JSON Configuration** and select your config file (see `sample_config.json`).
4. Click **Process**. A progress bar shows loading/filtering/calculation progress.
5. Review the results table.
6. Click **Export Results to Excel** to save the output as `.xlsx`.
7. Click **Clear** to reset the app and start over.

### Historical file flexibility

Historical Bhavcopy data can be supplied in whichever shape you have it:

- **One file per trading day** (classic case) -- each file contributes one day.
- **One file covering multiple trading days** (e.g. a range export named like
  `..._13-Jul-2026_TO_17-Jul-2026.csv`) -- every distinct date found inside the
  file's date column is treated as its own trading day.
- **Any mix of the above**, across any number of uploaded files.
- **Files with no date column at all** are still supported: the file is
  treated as one trading day and (since its position in time is unknown) is
  treated as one of the most recent days for ordering/trimming purposes. A
  warning is shown in this case so you know the ordering may be approximate --
  for fully accurate "last N trading days" behavior, prefer files that include
  a date column.

In all cases:
- The **same calendar date appearing in more than one file** is only counted once.
- If more trading days are found than `history_days`, the **oldest** ones are
  dropped first (a warning names which day was excluded).
- If fewer trading days are found than `history_days`, the app proceeds with
  whatever is available and warns you how many days were actually used.

## 7. Extending the App

The code is deliberately layered so new analytics can be added without touching
existing logic:

- **New Bhavcopy column / renamed column** → edit `config/constants.py` only.
- **New statistic (e.g. Open Interest change)** → add an entry to
  `PRICE_STAT_FIELDS` in `constants.py`; `run_analysis()` and the results
  table pick it up automatically via `AnalysisResult.to_flat_dict()`.
- **New analysis step** (e.g. multi-strike ladder around ATM) → add a function
  to `core/data_processor.py` and call it from `run_analysis()`, or add a new
  orchestration function alongside it and wire a new button in `main_window.py`.
- **New export format** (CSV, PDF) → add a sibling function in `core/exporter.py`.

## 8. Logging

All runs are logged to `logs/fno_analyzer.log` (rotating, 3 backups, 2 MB each)
as well as the console and the in-app "Log / Warnings" panel.

## 9. Notes on Real UDIFF Files

NSE's UDIFF Common Bhavcopy is typically a single daily CSV covering all F&O
symbols (equity + index, futures + options) with columns such as `TckrSymb`,
`XpryDt`, `StrkPric`, `OptnTp`, `OpnPric`, `HghPric`, `LwPric`, `ClsPric`,
`UndrlygPric`, etc. This app expects those exact column names by default;
update `config/constants.py` if you are working with a differently-formatted
export.
