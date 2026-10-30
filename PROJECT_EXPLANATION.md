# F&O UDIFF Bhavcopy Analyzer — Project Explanation & Working Guide

## 1. What is this Project?

The **F&O UDIFF Bhavcopy Analyzer** is a high-performance Python desktop application (built with **PySide6 / Qt**) designed for financial market traders, options strategists, and quantitative analysts who analyze Indian stock market derivatives (**NSE Futures & Options**).

Every trading day, the National Stock Exchange of India (NSE) publishes a daily summary file known as the **Bhavcopy** (specifically the modern **UDIFF** Common Bhavcopy format). This file contains daily trading statistics for every single futures and options contract traded that day: ticker symbol, expiry date, strike price, option type (CE/PE), open price, high price, low price, close price, open interest, and underlying asset prices.

### Core Problem This Project Solves:
Traders analyzing options need to know how today's **At-The-Money (ATM)** option contract is priced relative to its recent historical behavior (e.g., over the last 7 trading days):
- **Current Day**: Open, High, Low, Close (OHLC).
- **Historical Comparison ($N$ days, e.g., 7 days)**: Average, Maximum, and Minimum values for Open, High, Low, and Close.
- **Premium Valuation**: Whether today's closing price is at a premium or discount compared to the historical average ($\Delta\%$).

This application automates this entire workflow in seconds through a graphical desktop interface.

---

## 2. High-Level Working Workflow

```
[ Current Day File(s) ]       [ Historical File(s) ]       [ In-Dashboard Config ]
         │                              │                             │
         └───────────────┬──────────────┴─────────────────────────────┘
                         ▼
             [ 1. Data Loader & Column Normalizer ]
               • Maps various column headers to standard names (UDIFF & derivatives)
               • Reads CSV / XLSX / XLS formats
               • Auto-detects symbols & expiries for instant dropdown selection
                         ▼
             [ 2. Filter Current Day ]
               • Filters for Symbol (e.g., NIFTY) and Expiry (e.g., 21-Jul-2026)
                         ▼
             [ 3. High-Accuracy ATM Strike Resolution ]
               • 1st Priority: Filter positive (>0) Underlying Spot Price (UndrlygPric)
               • 2nd Priority: Near-Month Futures Closing Price (IDF / STF)
               • 3rd Priority: Median of available strikes
               • Selects Strike closest to reference spot price
                         ▼
             [ 4. Historical Processing & Date Alignment ]
               • Matches Symbol + Expiry + ATM Strike + Option Type (CE, PE, or BOTH)
               • Excludes current day from historical files to prevent double-counting
               • Deduplicates duplicate dates across overlapping files
               • Chronologically sorts by trade date
               • Selects the exact 'history_days' (e.g. last 7 trading days)
                         ▼
             [ 5. Statistics Calculation & Liquidity Check ]
               • Checks if contracts actually traded (volume > 0)
               • Computes Current, N-Day Average, Maximum, Minimum for OHLC
               • Calculates Close vs Avg % change (Premium vs Discount)
                         ▼
         ┌────────────────────────────────┐
         ▼                                ▼
[ Interactive Dashboard UI ]   [ Multi-Sheet Excel Export ]
 • Live KPI Metric Cards        • ATM Analysis summary table
 • Color-Coded Results Table    • Comprehensive Run Info metadata
 • Live Audit Console
```

---

## 3. Directory & Code Architecture

The codebase follows a clean, decoupled **layered architecture**:

```
d:/fno_bhavcopy_analyzer/
│
├── main.py                     # Entry point — launches the PySide6 Qt GUI application
├── requirements.txt            # Python dependencies (PySide6, pandas, openpyxl)
├── sample_config.json          # Example configuration parameters
├── PROJECT_EXPLANATION.md      # Detailed project guide & working explanation
│
├── config/                     # Configuration and Constants Layer
│   ├── constants.py            # Column names, aliases, price stat fields, defaults
│   └── config_manager.py       # Configuration reader, validator, and preset saver
│
├── core/                       # Pure Business & Data Logic (GUI-independent)
│   ├── models.py               # Shared dataclasses (AnalysisResult, FieldStats, etc.)
│   ├── data_loader.py          # File I/O, column normalization, and metadata auto-detection
│   ├── data_processor.py       # High-accuracy ATM calculation, date deduplication, statistics
│   └── exporter.py             # Exporting multi-row results and run metadata to Excel (.xlsx)
│
├── gui/                        # Presentation Layer
│   ├── main_window.py          # Pro dashboard UI (KPI cards, table, in-dashboard config)
│   ├── styles.py               # Modern Dark Theme stylesheet (Financial Terminal palette)
│   └── worker.py               # Background QThread worker to keep UI responsive
│
├── utils/                      # Utilities
│   └── logger_setup.py         # Rotating file logger and console logging
│
├── logs/                       # Application logs directory (auto-created)
│   └── fno_analyzer.log        # Detailed execution logs
└── atm_analysis_results.xlsx   # Output analysis file from previous export
```

---

## 4. Key Data Accuracy & Logic Enhancements

While maintaining the core At-The-Money comparative logic, the system includes 5 critical accuracy safeguards:

1. **Zero-Price / Unpopulated Spot Filtering**:
   - In UDIFF files, unpopulated rows occasionally default to `0.0` in the `UndrlygPric` column.
   - The processor filters `UndrlygPric > 0` before calculating the reference price, ensuring zeros never pull down the spot price or select a wrong ATM strike.

2. **Near-Month Futures Spot Proxy**:
   - When falling back to futures for spot price approximation, the engine evaluates contracts with `ClsPric > 0` and chooses the **near-month (earliest expiry) contract**, avoiding carrying cost/contango distortions from distant expiries.

3. **Current-Day Date Exclusion from Historical Pool**:
   - If a historical file contains or overlaps with today's date, the current day is automatically detected and excluded from the historical average calculation. This guarantees the $N$-day average reflects pure prior history without double-counting today.

4. **Liquidity & Zero-Volume Validation**:
   - In derivatives, illiquid strikes with zero trading volume (`TtlTradgVol == 0`) often carry synthetic settlement prices. The analyzer audits volume and alerts the user if zero-volume contracts are detected.

5. **Multi-Option Type & Straddle Capability**:
   - Supports selecting `CE (Call)`, `PE (Put)`, or `BOTH (CE & PE)`. When `BOTH` is selected, both Call and Put contracts at the ATM strike are processed and displayed side by side.

6. **Premium / Discount Calculation ($\Delta\%$)**:
   - Calculates percentage difference:
     $$\Delta\% = \frac{\text{Current Close} - \text{Avg Close}}{\text{Avg Close}} \times 100$$
   - Highlights in green (`+X% Premium`) or red (`-X% Discount`).

---

## 5. In-Dashboard Configuration & Modern UI Features

Users no longer need to prepare or upload an external `sample_config.json` file:
- **Interactive Controls**: Symbol, Expiry Date, History Days (1–90), and Option Type (`CE`, `PE`, `BOTH`) are placed directly on the top panel.
- **Smart Auto-Detection**: Uploading a current-day file automatically scans and populates the **Symbol** and **Expiry Date** dropdowns.
- **KPI Summary Cards**:
  - 🎯 **Target ATM Strike** with underlying reference price.
  - 💰 **Current Close** with Open price comparison.
  - 📊 **Historical Avg Close** with $\pm\Delta\%$ badge.
  - ↕️ **7-Day Price Range** showing the min and max boundaries.
- **Financial Terminal Styling**: Deep slate dark mode (`#0B0F19`), cyan and emerald accents, monospace numbers, and color-coded table cells.

---

## 6. Summary Table of Output Metrics

| Column Header in Output | Description |
| :--- | :--- |
| `Option Type` | `CE` (Call Option) or `PE` (Put Option) |
| `Strike Price` | The calculated At-The-Money strike price |
| `Current Open` / `Avg Open` / `Max Open` / `Min Open` | Today's open vs $N$-day average, maximum, and minimum |
| `Current High` / `Avg High` / `Max High` / `Min High` | Today's high vs $N$-day average, maximum, and minimum |
| `Current Low` / `Avg Low` / `Max Low` / `Min Low` | Today's low vs $N$-day average, maximum, and minimum |
| `Current Close` / `Avg Close` / `Max Close` / `Min Close` | Today's close vs $N$-day average, maximum, and minimum |
| `Close vs Avg %` | Percentage premium/discount vs historical average |

---

## 7. How to Run the Project

1. **Activate Python Virtual Environment & Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch Application**:
   ```bash
   python main.py
   ```
3. **Execute Analysis**:
   - Upload Current Day Bhavcopy file(s).
   - Upload Historical Bhavcopy file(s).
   - Confirm parameters on the dashboard (Symbol, Expiry, Days, Option Type).
   - Click **▶ Run Analysis**.
   - Review live KPI cards and results table; export via **📊 Export to Excel**.
