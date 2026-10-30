# NSE F&O Bhavcopy Data Download Guide

A step-by-step walkthrough on where and how to download the required **Current-Day** and **Historical** Bhavcopy data files from the **National Stock Exchange of India (NSE)** for use with the **F&O UDIFF Bhavcopy Analyzer**.

---

## 1. What Files Are Required by the Analyzer?

The application requires two groups of files:

| File Category | What It Represents | Examples |
| :--- | :--- | :--- |
| **Current-Day File(s)** | Today's (or most recent session's) market data. Used to determine the spot reference price, current ATM strike, and today's OHLC. | `OPTIDX_NIFTY_CE_20-Jul-2026_TO_20-Jul-2026.csv` or `BhavCopy_NSE_FO_0_0_0_20260720_F_0000.csv` |
| **Historical Bhavcopy File(s)** | Prior trading days (e.g. last 7 trading days). Used to calculate historical Average, Max, and Min. | `OPTIDX_NIFTY_CE_13-Jul-2026_TO_17-Jul-2026.csv` or individual daily files |

> [!NOTE]
> Supported formats are **`.csv`**, **`.xlsx`**, and **`.xls`**. If a file downloads inside a `.zip` archive, extract the `.csv` file before uploading to the app.

---

## 2. Method 1 (Recommended): Download Specific Contract Data from NSE Quote Page

This is the fastest and cleanest method when you want to analyze a specific index or stock (such as **NIFTY**, **BANKNIFTY**, or **FINNIFTY**).

### Detailed Steps:

1. **Open the NSE Derivatives Quote Page**:
   - URL: [https://www.nseindia.com/get-quotes/derivatives?symbol=NIFTY](https://www.nseindia.com/get-quotes/derivatives?symbol=NIFTY)
   - *(To analyze Bank Nifty, simply replace `NIFTY` with `BANKNIFTY`)*.

2. **Navigate to the "Historical Data" Tab**:
   - Scroll below the summary chart to the tabbed section.
   - Click on the **Historical Data** tab (located next to *Option Chain* and *Contracts*).

3. **Select Your Filters**:
   - **Instrument Type**: Select `Index Options` (`OPTIDX`) or `Stock Options` (`OPTSTK`).
   - **Symbol**: `NIFTY` (or your chosen ticker).
   - **Expiry Date**: Select your target expiry date (e.g., `21-Jul-2026`).
   - **Option Type**: Select `CE` (Call) or `PE` (Put).
   - **Strike Price**: Select your target strike (or leave blank if available).
   - **Date Range**:
     - *For Current Day*: Set both **From** and **To** to today's date.
     - *For Historical Data*: Set **From** to 7–10 trading days back, and **To** to the previous trading day (e.g. `13-Jul-2026` to `17-Jul-2026`).

4. **Filter & Download**:
   - Click **Filter** (or **Get Data**).
   - Click the **Download (.csv)** link.
   - The file will be saved in your `Downloads` folder with a filename like:
     - `OPTIDX_NIFTY_CE_20-Jul-2026_TO_20-Jul-2026.csv` (Current Day)
     - `OPTIDX_NIFTY_CE_13-Jul-2026_TO_17-Jul-2026.csv` (Historical Range)

---

## 3. Method 2: Download Full Market Daily UDIFF Bhavcopy

Use this method if you want the official end-of-day market-wide Bhavcopy containing all traded futures and options contracts for all equities and indices in a single file.

### Detailed Steps:

1. **Visit the NSE All Reports Page**:
   - URL: [https://w ww.nseindia.com/all-reports](https://www.nseindia.com/all-reports)

2. **Open the "Derivatives" Category**:
   - Click on the **Derivatives** tab in the report categories.

3. **Locate the Bhavcopy Section**:
   - Look for **"Bhavcopy (UDIFF format)"** or **"UDIFF Common Bhavcopy Final"**.

4. **Select Date & Download**:
   - Pick the target trading day on the calendar picker.
   - Click the **Download** link/icon.
   - The downloaded file is a ZIP archive named:
     `BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip`
     *(e.g., `BhavCopy_NSE_FO_0_0_0_20260720_F_0000.csv.zip`)*.

5. **Extract the ZIP Archive**:
   - Right-click the `.zip` file $\rightarrow$ **Extract All...**
   - The extracted `.csv` file is ready to be loaded directly into the analyzer.

---

## 4. Method 3: Historical Derivatives Archive (Past Daily Dates)

If you need daily Bhavcopy files across specific past dates:

1. Navigate to: [https://www.nseindia.com/all-reports-derivatives](https://www.nseindia.com/all-reports-derivatives)
2. Select:
   - **Report**: *Bhavcopy* / *UDIFF Bhavcopy*
   - **Date**: Choose the individual past dates you need (e.g., each day of the past week).
3. Download and extract each day's CSV into a folder (e.g., `D:\Bhavcopy_History\`).

---

## 5. Column Reference: What the Data Headers Mean

The application's built-in intelligent column normalizer seamlessly maps both NSE UDIFF codes and human-readable quote headers:

| UDIFF Column Code | Quote Page Header | What It Means |
| :--- | :--- | :--- |
| `TckrSymb` | `Symbol` | Ticker symbol (e.g. `NIFTY`, `BANKNIFTY`) |
| `TradDt` | `Date` | The trading date of the record (e.g. `20-Jul-2026`) |
| `XpryDt` | `Expiry` | Contract expiry date (e.g. `21-Jul-2026`) |
| `StrkPric` | `Strike Price` | The strike price of the option |
| `OptnTp` | `Option type` | `CE` (Call Option) or `PE` (Put Option) |
| `OpnPric` | `Open` | The opening price of the contract |
| `HghPric` | `High` | The highest price during the trading session |
| `LwPric` | `Low` | The lowest price during the trading session |
| `ClsPric` | `Close` | Official closing price of the contract |
| `UndrlygPric` | `Underlying Value` | Cash / Spot price of the underlying index or stock |
| `TtlTradgVol` | `No. of contracts` | Total contracts traded on that day |
| `OpnIntrst` | `Open Int` | Outstanding Open Interest (OI) |

---

## 6. Critical Timings, Trading Holidays & Tips

> [!IMPORTANT]
> **Daily Release Time**: NSE publishes the daily Bhavcopy file between **6:30 PM IST and 7:30 PM IST** on active trading days (Monday to Friday). Downloading before 6:30 PM will yield the previous day's report.

> [!WARNING]
> **Weekends & Trading Holidays**: Indian markets are closed on Saturdays, Sundays, and exchange holidays. Do not expect data files for these days. For a 7-day history, the app expects **7 active trading days** (which covers about 9 to 10 calendar days).

> [!TIP]
> **Browser Tip**: NSE India sometimes restricts automated bot scraping. Always download files manually using a standard desktop browser (Google Chrome, Microsoft Edge, Brave, or Mozilla Firefox).

---

## 7. How to Load the Files into the App

1. Run the app:
   ```bash
   python main.py
   ```
2. **Current Day Data** (Card 1):
   - Click **Upload Current Day File(s)**.
   - Select your today's file (e.g., `OPTIDX_NIFTY_CE_20-Jul-2026_TO_20-Jul-2026.csv`).
   - *Notice:* The app automatically detects and selects the **Symbol** and **Expiry Date** in the dashboard.
3. **Historical Bhavcopy Files** (Card 2):
   - Click **Upload Historical File(s)**.
   - Select your prior files (e.g., `OPTIDX_NIFTY_CE_13-Jul-2026_TO_17-Jul-2026.csv`).
4. **Confirm Dashboard Parameters** (Card 3):
   - Ensure Symbol, Expiry Date, History Days (e.g. 7), and Option Type (`CE`, `PE`, or `BOTH`) are set as desired.
5. Click **▶ Run Analysis**:
   - Live KPI cards and results table update instantly.
   - Click **📊 Export to Excel** to export to `.xlsx`.

