from __future__ import annotations
import numpy as np
import pandas as pd


def correlation_beta(asset_returns: pd.Series, spy_returns: pd.Series, window:int)->tuple[float,float]:
    a=asset_returns.dropna(); s=spy_returns.dropna()
    joined=pd.concat([a,s],axis=1).dropna().tail(window)
    if len(joined)<window:
        return np.nan,np.nan
    corr=float(joined.iloc[:,0].corr(joined.iloc[:,1]))
    var=float(joined.iloc[:,1].var(ddof=1))
    cov=float(joined.cov().iloc[0,1])
    beta=cov/var if var!=0 else np.nan
    return corr,beta
