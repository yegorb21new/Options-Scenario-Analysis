# Options Market Cockpit (Streamlit)

Educational/research dashboard for **ticker-level options context first**, then contract-level drilldown.

## What it does
- **Today’s Markets**: options activity, research flags, skew extremes, return bar view.
- **Cockpit**: sortable multi-metric table for returns, RV, IV, VRP, beta/correlation, skew, and liquidity.
- **Skew Monitor**: ticker-level smile/skew diagnostics for near-30D context.
- **Option Chain / Scenario P&L**: existing chain filters, IV visuals, intrinsic/extrinsic diagnostics, and scenario pricing.
- **Methodology / Validation**: formulas, caveats, and assumptions.

## Why cockpit context helps
Naive contract-level rankings can be distorted by illiquidity, stale quotes, or deep ITM/OTM mechanics. Ticker-level context (returns, realized vol, implied vol, VRP, skew, liquidity) helps frame diagnostics before contract-level investigation.

## Setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Methodology highlights
- Data source: `yfinance`/Yahoo (public/unofficial; suitable for research/demo).
- Realized vol: close-to-close return std annualized by `sqrt(252)`.
- Approx ATM IV: near-ATM options (`~0.97-1.03` moneyness) around target tenors.
- VRP: `approx_iv - realized_vol` over matched horizons.
- Skew: OTM put/call IV relative to ATM.
- Scenario pricing: simplified Black-Scholes with calendar-time T.
- Time-to-expiration uses seconds to **4:00pm ET** on expiration date.

## Limitations
- Yahoo quotes may be delayed/stale versus broker feeds.
- No paid OPRA quality feed, no full historical options tape.
- Simplified assumptions (no full dividend/borrow/jump/early-exercise modeling).
- Research diagnostics only; not investment advice.

## Future enhancements
- Paid historical options data and OPRA-quality quotes
- Earnings calendar overlay
- Snapshot database for longitudinal changes
- Historical IV rank/percentile
- Sector-relative rankings
- Portfolio-level scenario analytics
