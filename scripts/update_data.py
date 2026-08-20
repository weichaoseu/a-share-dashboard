import json, os
from pathlib import Path
import numpy as np, pandas as pd, akshare as ak

ROOT=Path(__file__).resolve().parents[1]
TARGETS={
"科创50":("index","sh000688"),"创业板50":("index","sz399673"),"沪深300":("index","csi000300"),
"红利低波ETF":("etf",os.getenv("DIV_LOW_ETF","515300")),
"煤炭ETF":("etf",os.getenv("COAL_ETF","515220")),
"银行ETF":("etf",os.getenv("BANK_ETF","512800"))}

def hist(kind,code):
    if kind=="index":
        d=ak.stock_zh_index_daily_em(symbol=code)
    else:
        d=ak.fund_etf_hist_em(symbol=code,period="daily",start_date="20190101",end_date="20991231",adjust="qfq")
    if d is None or d.empty:
        raise RuntimeError(f"AKShare returned empty data: kind={kind}, code={code}")
    aliases={"date":"date","日期":"date","close":"close","收盘":"close","volume":"volume","成交量":"volume","amount":"amount","成交额":"amount"}
    d=d.rename(columns={c:aliases[c] for c in d.columns if c in aliases})
    missing={"date","close","volume"}-set(d.columns)
    if missing:
        raise RuntimeError(f"AKShare columns missing {sorted(missing)} for {code}; actual columns={list(d.columns)}")
    keep=[c for c in ["date","close","volume","amount"] if c in d.columns]
    d=d[keep].copy()
    d["date"]=pd.to_datetime(d["date"])
    for c in ["close","volume","amount"]:
        if c in d.columns: d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["date","close","volume"]).sort_values("date").reset_index(drop=True)
    if len(d)<130: raise RuntimeError(f"Not enough history for {code}: {len(d)} rows")
    return d

def pr(s,n=250):
    x=s.dropna().tail(n)
    return 50. if len(x)<20 else float((x<=x.iloc[-1]).mean()*100)

def factors(d):
    c=d.close; r=c.pct_change(); v=d.volume
    r20,r60,r120=c.pct_change(20),c.pct_change(60),c.pct_change(120)
    trend=.35*pr(r20)+.4*pr(r60)+.25*pr(r120)
    rv=v/v.rolling(60).median()
    up=rv.where(r>0).rolling(40).mean(); dn=rv.where(r<0).rolling(40).mean()
    asym=((up-dn)/(up.abs()+dn.abs()+1e-9)).fillna(0)
    asym_score=np.clip(50+50*asym.iloc[-1],0,100)
    neg=(-r).where(r<0,0); rebound=r.shift(-1).clip(lower=0)
    absorb=(rebound/(neg+1e-6)).replace([np.inf,-np.inf],np.nan).clip(0,3).rolling(20).mean()
    eff=(r/rv.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).rolling(20).mean()
    smart=.4*asym_score+.3*pr(absorb)+.3*pr(eff)
    crowd=.45*pr(r60)+.25*pr(r120)+.20*pr(rv)+.10*pr(r.rolling(20).std())
    return dict(trend=round(float(trend),1),smart_money=round(float(smart),1),crowding=round(float(np.clip(crowd,0,100)),1),
      daily_ret=round((c.iloc[-1]/c.iloc[-2]-1)*100,2),ret20=round((c.iloc[-1]/c.iloc[-21]-1)*100,2),
      ret60=round((c.iloc[-1]/c.iloc[-61]-1)*100,2),ret120=round((c.iloc[-1]/c.iloc[-121]-1)*100,2))

raw={k:hist(*v) for k,v in TARGETS.items()}
common=sorted(set.intersection(*[set(x.date.dt.strftime("%Y-%m-%d")) for x in raw.values()]))[-800:]
if len(common)<130: raise RuntimeError(f"Not enough common trading dates: {len(common)}")
aligned={}
for k,d in raw.items():
    z=d.assign(ds=d.date.dt.strftime("%Y-%m-%d")).set_index("ds").reindex(common); aligned[k]=z
base=aligned["沪深300"].close.astype(float)
out={"asof":common[-1],"dates":common,"series":{}}
for k,z in aligned.items():
    s=z.close.astype(float); x=factors(raw[k]); rs=s/base
    x["cum"]=(s/s.iloc[0]*100).round(4).tolist()
    x["rs60"]=(rs/rs.shift(60)*100).round(4).replace([np.inf,-np.inf],np.nan).where(lambda q:q.notna(),None).tolist()
    out["series"][k]=x
(ROOT/"data/data.json").write_text(json.dumps(out,ensure_ascii=False),encoding="utf-8")
print(out["asof"])
