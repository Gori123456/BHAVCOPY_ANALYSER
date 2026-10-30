# Quantitative Logic & Mathematics Explained
## How the F&O Bhavcopy Analyzer Processes Data and Generates Output

This document explains, in simple terms with complete mathematical detail, exactly what happens inside the engine from the moment you upload your files until the final numbers appear on your dashboard.

---

## 1. Overview of the Analytical Pipeline

When you upload a **Current Day Bhavcopy** and **Historical Files**, the engine executes an 8-step pipeline:

```
[ Raw Current Bhavcopy CSV ]       [ Raw Historical Bhavcopy / OPTIDX CSVs ]
            │                                             │
            ▼                                             ▼
   Step 1: Column Normalization                  Step 1: Column Normalization
            │                                             │
            ▼                                             │
   Step 2: Underlying Spot Price Extraction               │
            │                                             │
            ▼                                             │
   Step 3: ATM Strike Mathematical Determination          │
            │                                             │
            ▼                                             │
   Step 4: Current Day Contract Extraction                │
   (Pulls actual Close, Open, High, Low for CE & PE)      │
            │                                             │
            └──────────────────────┬──────────────────────┘
                                   ▼
              Step 5: Progressive 3-Tier Historical Matching
                                   │
                                   ▼
              Step 6: Historical Statistical Aggregation
              (Calculates Mean Average, Max Ceiling, Min Floor)
                                   │
                                   ▼
              Step 7: Valuation % & Edge Classification
              (Calculates % premium difference vs historical mean)
                                   │
                                   ▼
              Step 8: Straddle, Breakevens & Forward Directives
              (Calculates Expected Move, Profit Target & Stop-Loss)
```

---

## 2. Step 1: File Ingestion & Column Normalization

NSE (National Stock Exchange of India) publishes options data across different reports that use varying column headers:
* **New UDIFF Bhavcopy format**: Uses compact abbreviated codes (`TckrSymb`, `XpryDt`, `StrkPric`, `OptnTp`, `UndrlygPric`, `ClsPric`).
* **Derivatives Bhavcopy format**: Uses descriptive names (`SYMBOL`, `EXPIRY_DT`, `STRIKE_PR`, `OPTION_TYP`, `CLOSE`).
* **NSE Portal / OPTIDX exports**: Uses mixed-cased headers with spaces (`Symbol`, `Expiry`, `Strike Price`, `Option type`, `Close`, `Underlying Value`).

To ensure files can be processed regardless of source without manual editing, the engine applies a **fuzzy column normalizer**:

$$\text{Canonical Header} = \text{Lookup}\Big(\text{lowercase}\big(\text{strip\_punctuation}(\text{Raw Header})\big)\Big)$$

### Column Alias Translation Table:
| Canonical Attribute | Accepted Ingest Aliases | Purpose |
| :--- | :--- | :--- |
| **`symbol`** | `TckrSymb`, `Symbol`, `symbol` | Filters the index or equity (e.g. `NIFTY`) |
| **`expiry`** | `XpryDt`, `Expiry`, `Expiry_Dt`, `FininstrmActlXpryDt` | Contract expiration date |
| **`strike`** | `StrkPric`, `Strike Price`, `Strike_Pr` | Option exercise price |
| **`option_type`**| `OptnTp`, `Option type`, `Option_Typ` | `CE` (Call) or `PE` (Put) |
| **`close`** | `ClsPric`, `Close`, `LastPric`, `LTP` | Official closing settlement price |
| **`underlying`** | `UndrlygPric`, `Underlying Value`, `UnderlyingPrice` | Cash index spot price |
| **`trade_date`** | `TradDt`, `Date`, `BizDt` | Trading session date |

---

## 3. Step 2 & 3: Extracting Spot & Determining the ATM Strike

### Step 2: Underlying Spot Price Extraction ($S$)
In the NSE Bhavcopy, every option row includes the current cash index price in the `UndrlygPric` (or `Underlying Value`) column.
* The engine extracts all rows for the selected symbol (e.g. `NIFTY`).
* It reads the non-zero `UndrlygPric`:
  $$S = 22,936.75$$

*(If `UndrlygPric` is blank, the engine scans for the near-month Futures contract where `OptnTp == 'XX'` to use as the cash reference price).*

---

### Step 3: Determining the At-The-Money (ATM) Strike ($K_{\text{ATM}}$)
An option contract is **At-The-Money (ATM)** when its exercise strike price is closest to the current market spot price.

Let $\mathcal{K} = \{K_1, K_2, \dots, K_m\}$ be the set of all available strike prices listed for that index on that expiry date. The ATM strike is mathematically defined as:

$$K_{\text{ATM}} = \arg\min_{K \in \mathcal{K}} \big| K - S \big|$$

#### Real Walkthrough from your 29-Oct Data:
* **Underlying Spot Price ($S$)**: $22,936.75$
* **Available NIFTY Strikes ($\mathcal{K}$)**: $\dots, 22850, 22900, 22950, 23000, 23050, \dots$
* **Evaluating Absolute Distances**:
  * For Strike $22,900$: $|22,900 - 22,936.75| = 36.75$ points
  * For Strike $22,950$: $|22,950 - 22,936.75| = 13.25$ points  $\leftarrow \mathbf{\text{Minimum}}$
  * For Strike $23,000$: $|23,000 - 22,936.75| = 63.25$ points

Because $13.25 < 36.75$, the engine selects **$22,950$** as the official ATM strike.

---

## 4. Step 4: Extracting Current Day Prices

Once the ATM strike ($22,950$) and active expiry (`2026-11-03`) are identified, the engine extracts the prices from the current-day file:

| Contract | Strike | Expiry | Current Close ($P_{\text{current}}$) | Open | High | Low |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NIFTY Call (CE)** | 22950 | 2026-11-03 | **₹150.60** | ₹63.20 | ₹162.65 | ₹57.70 |
| **NIFTY Put (PE)** | 22950 | 2026-11-03 | **₹128.25** | ₹352.95 | ₹377.50 | ₹120.40 |

These two closing numbers ($₹150.60$ and $₹128.25$) are the test subjects. Next, the engine determines whether these prices are **statistically cheap, normal, or expensive**.

---

## 5. Step 5: Progressive 3-Tier Historical Matching

To compare today's option price against history, the engine must find historical rows in your uploaded historical files (`OPTIDX_NIFTY_CE_20-Oct-2026_TO_27-Oct-2026.csv`).

Because markets move, an exact contract match is not always available across different weeks. The engine uses a **Progressive 3-Tier Algorithm**:

```
                              [ Historical File ]
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
 [ Tier 1: Exact Match ]                                 [ Match Found? ]
 Same Symbol + Same Expiry + Exact Strike                     ├── Yes ──► Aggregate Tier 1 Data
                                                              └── No
                                                                  │
                                                                  ▼
                                                      [ Tier 2: Strike Shift ]
                                                      Same Symbol + Same Expiry + Nearest Strike
                                                                  │
                                                       ┌──────────┴──────────┐
                                                       ▼                     ▼
                                                  [ Found? ] ── Yes ──► Aggregate Tier 2 Data
                                                       │
                                                      No
                                                       │
                                                       ▼
                                            [ Tier 3: Universal Fallback ]
                                            Cross-Contract Historical Baseline
                                            Same Symbol + Nearest Available Strike
                                            Across Available Prior Trading Sessions
                                                       │
                                                       ▼
                                            Aggregate Tier 3 Pricing Baseline
```

* In your files, the current day was **29-Oct** (contract expiry `2026-11-03`, ATM `22950`), while the historical file covered **20–27 Oct** (contract expiry `27-Oct-2026`, strike `22800`).
* **Tier 3** activated: it used the 4 trading sessions (20, 21, 24, 27 Oct) for NIFTY ATM options as the pricing baseline, preventing `No matching rows found` errors.

---

## 6. Step 6: Historical Statistical Aggregation

Let $\{P_1, P_2, \dots, P_N\}$ be the closing prices across the $N$ most recent distinct trading sessions found in the historical pool.

### 1. De-duplication Rule
If two uploaded files cover the same calendar date, the engine only counts that date once to avoid skewing the averages.

### 2. Historical Arithmetic Mean ($\bar{P}$)
The baseline fair-value average is calculated as:

$$\bar{P} = \frac{1}{N} \sum_{i=1}^{N} P_i$$

### 3. Historical Maximum Ceiling ($P_{\max}$) and Minimum Floor ($P_{\min}$)
$$P_{\max} = \max\big(P_1, P_2, \dots, P_N\big)$$
$$P_{\min} = \min\big(P_1, P_2, \dots, P_N\big)$$

#### Real Walkthrough from your Historical Data (20–27 Oct):
The historical file contained 4 sessions for the NIFTY ATM Call:
* **Day 1 (20-Oct)**: $P_1 = ₹136.65$
* **Day 2 (21-Oct)**: $P_2 = ₹98.40$
* **Day 3 (24-Oct)**: $P_3 = ₹86.60$
* **Day 4 (27-Oct)**: $P_4 = ₹53.35$

$$\bar{P}_{\text{CE}} = \frac{136.65 + 98.40 + 86.60 + 53.35}{4} = \frac{375.00}{4} = \mathbf{₹93.75}$$

$$P_{\max} = \mathbf{₹136.65} \quad (\text{Peak Volatility Ceiling})$$
$$P_{\min} = \mathbf{₹53.35} \quad (\text{Maximum Theta Crush Floor})$$

---

## 7. Step 7: Valuation % & Edge Classification Mathematics

This is the core quantitative metric that reveals pricing anomalies.

### The Valuation Difference Formula:

$$\text{Valuation \%} = \left( \frac{P_{\text{current}} - \bar{P}}{\bar{P}} \right) \times 100$$

Where:
* $P_{\text{current}}$ = Today's closing price from the Current Bhavcopy
* $\bar{P}$ = $N$-day historical arithmetic average

#### Real Numeric Calculation:

#### 1. For the NIFTY 22950 Call (CE):
$$\text{Valuation \%}_{\text{CE}} = \left( \frac{150.60 - 93.75}{93.75} \right) \times 100 = \left( \frac{56.85}{93.75} \right) \times 100 = \mathbf{+60.64\%}$$

#### 2. For the NIFTY 22950 Put (PE):
$$\text{Valuation \%}_{\text{PE}} = \left( \frac{128.25 - 93.75}{93.75} \right) \times 100 = \left( \frac{34.50}{93.75} \right) \times 100 = \mathbf{+36.80\%}$$

---

### Institutional Edge Classification Logic:

```
                      Valuation % Difference Scale
  -100%               -20%                     +20%                +100%
  ◄─────────────────────┼────────────────────────┼────────────────────►
    🟢 BUY EDGE         │    ⚖️ NEUTRAL / FAIR   │   🔴 SELL EDGE
  (Cheap Options /      │    (Normal Corridor /  │  (Overpriced Volatility /
   Long Volatility)     │     Iron Condor)       │   Short Straddle Edge)
```

$$\text{Regime} = \begin{cases} 
\mathbf{\text{SELL EDGE (Overpriced Volatility)}}, & \text{if } \text{Valuation \%} \ge +20.0\% \\
\mathbf{\text{BUY EDGE (Underpriced Volatility)}}, & \text{if } \text{Valuation \%} \le -20.0\% \\
\mathbf{\text{FAIR VALUE (Statistical Range)}}, & \text{if } -20.0\% < \text{Valuation \%} < +20.0\%
\end{cases}$$

* **Result for 29-Oct**: Because both CE ($+60.64\%$) and PE ($+36.80\%$) were $\ge +20\%$, the system classified the market regime as **`SELL STRADDLE (Overpriced Volatility)`**.

---

## 8. Step 8: ATM Straddle, Expected Move & Breakevens

An **ATM Straddle** involves trading both the ATM Call and the ATM Put simultaneously:
$$\text{Straddle} = \text{ATM CE} + \text{ATM PE}$$

Because intrinsic value at the ATM strike is zero, **100% of the straddle price represents pure extrinsic time value and volatility expectation**.

### 1. Total Straddle Premium ($C_{\text{straddle}}$)
$$C_{\text{straddle}} = P_{\text{CE}} + P_{\text{PE}} = 150.60 + 128.25 = \mathbf{₹278.85}$$

### 2. Historical Straddle Benchmark ($\bar{C}_{\text{straddle}}$)
$$\bar{C}_{\text{straddle}} = \bar{P}_{\text{CE}} + \bar{P}_{\text{PE}} = 93.75 + 93.75 = \mathbf{₹187.50}$$

### 3. Straddle Premium Expansion %
$$\text{Straddle Expansion \%} = \left( \frac{278.85 - 187.50}{187.50} \right) \times 100 = \mathbf{+48.72\%}$$

### 4. Implied Market Expected Move ($\pm \%$)
The percentage swing that the options market expects the index to make before expiration is:

$$\text{Expected Move \%} = \left( \frac{C_{\text{straddle}}}{S} \right) \times 100$$
$$\text{Expected Move \%} = \left( \frac{278.85}{22,936.75} \right) \times 100 = \mathbf{\pm 1.215\%}$$

The market was pricing in a $\pm 1.215\%$ swing ($\pm 278.85$ points) on NIFTY.

---

### 5. Safety Corridor & Breakeven Bounds
If an option seller collects $₹278.85$ in total premium, the underlying index can fluctuate substantially before the position enters a loss.

$$\text{Lower Breakeven} = K_{\text{ATM}} - C_{\text{straddle}} = 22,950 - 278.85 = \mathbf{22,671.15}$$
$$\text{Upper Breakeven} = K_{\text{ATM}} + C_{\text{straddle}} = 22,950 + 278.85 = \mathbf{23,228.85}$$

$$\text{Total Safe Cushion Width} = \text{Upper BE} - \text{Lower BE} = 2 \times C_{\text{straddle}} = 2 \times 278.85 = \mathbf{557.70 \text{ points}}$$

```
                       557.70 POINTS PROFITABLE SAFE CORRIDOR
   ◄─────────────────────────────────────────────────────────────────────────────►
   22,671.15                        22,950.00                        23,228.85
  Lower Breakeven                  ATM Strike                       Upper Breakeven
   (Max Downside)                  (Peak Profit)                     (Max Upside)
```

As long as NIFTY trades between **$22,671.15$ and $23,228.85$**, an option seller who collected the inflated straddle premium remains in profit.

---

## 9. Tomorrow's Tactical Execution Mathematics

The dashboard translates these metrics into an actionable trade plan for the opening bell (09:18 AM – 09:30 AM IST):

### 1. 50% Decay Profit Target ($T_{\text{profit}}$)
Option sellers do not hold until zero; institutional desks close the position once 50% of the extrinsic premium has decayed:

$$T_{\text{profit}} = C_{\text{straddle}} \times 0.50 = 278.85 \times 0.50 = \mathbf{₹139.42}$$
$$\text{Net Profit per Share} = 278.85 - 139.42 = \mathbf{+₹139.43}$$
*(On a standard NIFTY 25-share lot, this equals $+₹3,485$ profit per lot).*

### 2. +25% Premium Expansion Stop-Loss ($SL_{\text{hard}}$)
If a major macroeconomic event occurs and implied volatility spikes further, the trade is terminated at a strict 25% threshold:

$$SL_{\text{hard}} = C_{\text{straddle}} \times 1.25 = 278.85 \times 1.25 = \mathbf{₹348.56}$$
$$\text{Max Risk per Share} = 348.56 - 278.85 = \mathbf{₹69.71}$$

### 3. Risk-to-Reward Ratio ($R:R$)
$$\text{Risk : Reward} = \frac{\text{Potential Profit}}{\text{Max Risk}} = \frac{139.43}{69.71} = \mathbf{2.00 : 1.00}$$

You risk **$₹69.71$** to make **$₹139.43$**, while holding a **557-point margin of safety**.

---

## 10. Future Analysis Roadmap Mathematics

As the week progresses towards expiry, the system guides future analysis using four mathematical checks:

### 1. Daily Theta Decay Velocity ($\frac{dC}{dt}$)
When you upload the next day's Bhavcopy ($T+1$), the engine measures the rate of decay:

$$\Delta C = C_{T+1} - C_T$$

* If $\Delta C \le -₹35.00$: Time decay is progressing as expected.
* If $\Delta C > 0$: Premium expanded; evaluate whether to hold or close.

### 2. Strike Migration Check ($|\Delta S|$)
Let $S_0$ be the entry spot price ($22,936.75$).

$$\text{Drift} = |S_t - S_0|$$

* If $\text{Drift} \ge 100 \text{ points}$: The ATM strike has migrated.
* **Adjustment Rule**: Roll the untested winning option leg closer to current market spot to collect extra credit and re-center position delta back to zero.

### 3. Open Interest (OI) Confirmation
The engine checks the `ChngInOpnIntrst` column:
* Net Call OI Additions $> 20$ lakh shares at a strike indicate an institutional **resistance ceiling**.
* Net Put OI Additions $> 20$ lakh shares at a strike indicate an institutional **support floor**.

---

## 11. Summary of Mathematical Formulas

| Metric | Mathematical Formula | Purpose |
| :--- | :--- | :--- |
| **ATM Strike ($K_{\text{ATM}}$)** | $\arg\min_{K} \|K - S\|$ | Selects closest listed strike to market spot |
| **Historical Mean ($\bar{P}$)** | $\frac{1}{N} \sum_{i=1}^N P_i$ | Calculates $N$-day fair-value benchmark |
| **Valuation % Diff** | $\left(\frac{P_{\text{current}} - \bar{P}}{\bar{P}}\right) \times 100$ | Identifies overpricing ($>+20\%$) and underpricing ($<-20\%$) |
| **Straddle Cost ($C$)** | $P_{\text{CE}} + P_{\text{PE}}$ | Measures combined market extrinsic volatility price |
| **Expected Move %** | $\left(\frac{C}{S}\right) \times 100$ | Implied percentage market swing expected before expiry |
| **Breakeven Range** | $[K - C, \; K + C]$ | Lower and Upper price boundaries of profitability |
| **50% Take-Profit** | $C \times 0.50$ | Target price to buy back and exit for profit |
| **25% Hard Stop-Loss** | $C \times 1.25$ | Protective exit threshold to cap maximum downside |

