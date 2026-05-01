# Options Volatility Surface & Scenario Analytics Dashboard

A portfolio-style **Streamlit research app** for exploring listed options using public Yahoo Finance data via `yfinance`.

## Why this project exists
This project demonstrates practical options analytics workflows in a transparent, reproducible way:
- Normalize option-chain data
- Visualize IV smile/skew and term structure
- Compare implied and realized volatility
- Run scenario-based theoretical P&L using Black-Scholes

> Educational research tool only. Not investment advice.

## Features
- Ticker input (e.g., NVDA, SPY)
- Option-chain loading across user-selected upcoming expirations
- Quality filtering (IV validity, spread/liquidity, moneyness)
- Interactive IV smile/skew and 3D IV surface charts
- Realized volatility metrics (20/30/60 day annualized)
- Relative richness/cheapness diagnostics (crude score)
- Scenario analytics over spot, IV, and time shifts
- Black-Scholes Greeks for selected contract

## Screenshots
- `docs/screenshots/dashboard_overview.png` *(placeholder)*
- `docs/screenshots/scenario_heatmap.png` *(placeholder)*

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

## Data source note
Data is pulled from Yahoo Finance through `yfinance` (unofficial/public source). This is suitable for research/demo use and may contain delays, missing values, or inconsistencies.


## Data Source and Quote Latency
Data in this app comes from `yfinance`/Yahoo public endpoints and is intended for research/demo workflows.

- Quotes may be delayed or stale relative to live broker feeds.
- Validate actionable bid/ask levels against your broker/platform (for example, thinkorswim) before any live trading decision.
- Differences between this app's displayed quotes and broker live quotes do not necessarily indicate a calculation bug in this project.

## Black-Scholes assumptions
This app uses a simplified calendar-time European Black-Scholes model for scenario pricing. Time to expiration (T) is computed from exact seconds remaining until 4:00pm ET on the expiration date. Assumptions include lognormal dynamics, constant volatility/rates, frictionless markets, and no early exercise modeling. Results may differ from broker platforms that apply proprietary assumptions, dividend inputs, American exercise adjustments, or trading-time conventions.

## Relative value score
The app computes a **relative_value_score** within expiration/option-type groups:
- `iv_zscore_within_expiration`
- `liquidity_penalty` from spread%
- `relative_value_score = -iv_zscore_within_expiration - liquidity_penalty`

Higher scores indicate relatively lower IV vs peers with better liquidity; lower scores indicate relatively richer IV and/or weaker liquidity. This is a crude diagnostic, **not** a prediction or recommendation.

## Future enhancements
- Historical IV rank/percentile (if a paid volatility history source is added)
- Earnings calendar overlays
- Dividend and American-option adjustments
- Portfolio-level scenario analysis
- Cross-ticker comparison views
- Saved watchlists
