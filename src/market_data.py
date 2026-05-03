from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import yfinance as yf

from src.data import fetch_option_chain
from src.skew import compute_skew_metrics
from src.vol_metrics import compute_return_metrics
from src.market_metrics import correlation_beta


def _pick_exp(expirations:list[str], target_days:int)->str|None:
    if not expirations: return None
    today=pd.Timestamp.utcnow().date()
    scored=sorted(expirations, key=lambda e: abs((pd.to_datetime(e).date()-today).days-target_days))
    return scored[0]

@st.cache_data(ttl=600)
def load_universe_metrics(tickers:list[str])->tuple[pd.DataFrame,dict[str,pd.DataFrame],dict[str,pd.DataFrame],list[str]]:
    rows=[]; hist_map={}; chain_map={}; warns=[]
    spy_ret=None
    for t in tickers:
        try:
            tk=yf.Ticker(t)
            hist=tk.history(period='1y', interval='1d')
            if hist.empty: raise ValueError('No history')
            close=hist['Close'].dropna()
            price=float(close.iloc[-1])
            rets=close.pct_change().dropna()
            if t=='SPY': spy_ret=rets
            expirations=list(tk.options)
            e30=_pick_exp(expirations,30); e90=_pick_exp(expirations,90)
            chain30=fetch_option_chain(t,[e30],price) if e30 else pd.DataFrame()
            chain90=fetch_option_chain(t,[e90],price) if e90 else pd.DataFrame()
            chain_map[t]=chain30
            def atm_iv(df):
                if df.empty:return float('nan')
                d=df[df['moneyness'].between(0.97,1.03)]
                d=d[d['impliedVolatility'].notna() & (d['impliedVolatility']>0)]
                return float(d['impliedVolatility'].mean()) if not d.empty else float('nan')
            iv30=atm_iv(chain30); iv90=atm_iv(chain90)
            skew30=compute_skew_metrics(chain30,price)
            skew90=compute_skew_metrics(chain90,price)
            liq={
                'total_call_volume': float(chain30.loc[chain30['option_type']=='call','volume'].fillna(0).sum()) if not chain30.empty else 0.0,
                'total_put_volume': float(chain30.loc[chain30['option_type']=='put','volume'].fillna(0).sum()) if not chain30.empty else 0.0,
                'total_call_open_interest': float(chain30.loc[chain30['option_type']=='call','openInterest'].fillna(0).sum()) if not chain30.empty else 0.0,
                'total_put_open_interest': float(chain30.loc[chain30['option_type']=='put','openInterest'].fillna(0).sum()) if not chain30.empty else 0.0,
            }
            liq['total_option_volume']=liq['total_call_volume']+liq['total_put_volume']
            liq['put_call_volume_ratio']=liq['total_put_volume']/liq['total_call_volume'] if liq['total_call_volume']>0 else float('nan')
            liq['put_call_oi_ratio']=liq['total_put_open_interest']/liq['total_call_open_interest'] if liq['total_call_open_interest']>0 else float('nan')
            toi=liq['total_call_open_interest']+liq['total_put_open_interest']
            liq['volume_to_oi']=liq['total_option_volume']/toi if toi>0 else float('nan')
            r=compute_return_metrics(close)
            row={'ticker':t,'price':price,'approx_30d_iv':iv30,'approx_90d_iv':iv90,**r,
                 'vrp_30d':iv30-r['rv_1m'] if pd.notna(iv30) and pd.notna(r['rv_1m']) else float('nan'),
                 'vrp_90d':iv90-r['rv_3m'] if pd.notna(iv90) and pd.notna(r['rv_3m']) else float('nan'),
                 'put_skew_30d':skew30['put_skew'],'call_skew_30d':skew30['call_skew'],'skew_steepness_30d':skew30['skew_steepness'],
                 'put_skew_90d':skew90['put_skew'],'call_skew_90d':skew90['call_skew'],'skew_steepness_90d':skew90['skew_steepness'],
                 **liq,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
            rows.append(row); hist_map[t]=hist
        except Exception as e:
            warns.append(f'{t}: {e}')
    df=pd.DataFrame(rows)
    if spy_ret is not None and not df.empty:
        for i,row in df.iterrows():
            ret=hist_map[row['ticker']]['Close'].pct_change().dropna()
            c1,b1=correlation_beta(ret,spy_ret,21); c3,b3=correlation_beta(ret,spy_ret,63)
            df.loc[i,'corr_spy_1m']=c1; df.loc[i,'beta_spy_1m']=b1; df.loc[i,'corr_spy_3m']=c3; df.loc[i,'beta_spy_3m']=b3
    return df,hist_map,chain_map,warns
