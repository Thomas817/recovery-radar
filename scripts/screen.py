#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, statistics, sys, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UNIVERSE = Path(__file__).resolve().with_name("universe.json")
RESULTS, HISTORY, STATE = DATA/"results.json", DATA/"history.json", DATA/"state.json"

def read(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default

def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def clamp(v, lo=0, hi=100): return max(lo, min(hi, v))
def pct(a, b): return (a/b-1)*100 if b else 0.0

def nearest(rows, days):
    target = date.fromisoformat(rows[-1]["date"]) - timedelta(days=days)
    row = min(rows, key=lambda r: abs((date.fromisoformat(r["date"])-target).days))
    return float(row.get("adjusted_close") or row.get("close"))

def fetch(symbol, key):
    end=date.today(); start=end-timedelta(days=370)
    params=urlencode({"api_token":key,"fmt":"json","period":"d","from":start.isoformat(),"to":end.isoformat()})
    url=f"https://eodhd.com/api/eod/{quote(symbol, safe='.-')}?{params}"
    req=Request(url, headers={"User-Agent":"RecoveryRadar/2.1"})
    try:
        with urlopen(req, timeout=35) as r: payload=r.read().decode("utf-8")
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8',errors='replace')[:250]}") from e
    except URLError as e: raise RuntimeError(f"Netzwerkfehler: {e.reason}") from e
    try: data=json.loads(payload)
    except json.JSONDecodeError as e: raise RuntimeError(f"Ungültige API-Antwort: {payload[:150]}") from e
    if isinstance(data, dict): raise RuntimeError(str(data.get("message") or data.get("error") or data))
    rows=[{"date":x["date"],"high":x.get("high"),"low":x.get("low"),
           "adjusted_close":x.get("adjusted_close") or x.get("close")}
          for x in data if x.get("date") and (x.get("adjusted_close") or x.get("close"))]
    rows.sort(key=lambda x:x["date"])
    if len(rows)<20: raise RuntimeError("Zu wenige historische Kursdaten.")
    return rows

def calculate(company, rows):
    closes=[float(r["adjusted_close"]) for r in rows]; current=closes[-1]
    perf={k:pct(current,nearest(rows,d)) for k,d in [("1m",30),("3m",91),("6m",182),("12m",365)]}
    high=max(float(r.get("high") or r["adjusted_close"]) for r in rows)
    low=min(float(r.get("low") or r["adjusted_close"]) for r in rows)
    below=pct(current,high); above=pct(current,low)
    daily=[pct(closes[i],closes[i-1]) for i in range(1,len(closes)) if closes[i-1]]
    vol=statistics.pstdev(daily)*math.sqrt(252) if len(daily)>5 else 0
    under=clamp((-below)/.60)
    recovery=clamp(50+perf["1m"]*1.8+perf["3m"]*1.1+perf["6m"]*.45)
    fromlow=clamp(above/.80); risk=clamp(vol*1.5)
    score=round(clamp(.42*under+.36*recovery+.22*fromlow-.18*risk),1)
    return {**company,"price":round(current,4),"asOf":rows[-1]["date"],
      "performance":{k:round(v,2) for k,v in perf.items()},
      "high52":round(high,4),"low52":round(low,4),
      "belowHigh52Pct":round(below,2),"aboveLow52Pct":round(above,2),
      "volatilityAnnualized":round(vol,2),
      "components":{"underperformance":round(under,1),"recovery":round(recovery,1),
                    "recoveryFromLow":round(fromlow,1),"risk":round(risk,1)},
      "score":score,
      "explanation":f"{abs(below):.1f}% unter dem 52‑Wochen-Hoch; 3‑Monats-Entwicklung {perf['3m']:+.1f}%. "+
        ("Erste Erholungssignale sind erkennbar." if perf["3m"]>0 else "Ein belastbares Erholungssignal fehlt noch."),
      "chart":[{"date":r["date"],"close":round(float(r["adjusted_close"]),4)} for r in rows[-130:]],
      "updatedAt":datetime.now(timezone.utc).isoformat()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--batch-size",type=int,default=3); ap.add_argument("--delay",type=float,default=.35)
    args=ap.parse_args(); key=os.getenv("EODHD_API_KEY","").strip()
    if not key: print("FEHLER: EODHD_API_KEY fehlt.",file=sys.stderr); return 2
    universe=read(UNIVERSE,[])
    if not universe: print("FEHLER: scripts/universe.json fehlt.",file=sys.stderr); return 3
    size=max(1,min(args.batch_size,len(universe))); state=read(STATE,{"cursor":0}); cursor=int(state.get("cursor",0))%len(universe)
    selected=[universe[(cursor+i)%len(universe)] for i in range(size)]
    old=read(RESULTS,{"results":[]}); existing={x["symbol"]:x for x in old.get("results",[]) if x.get("symbol")}
    errors=[]; success=0
    print(f"Starte Screening: {size} Unternehmen ab Position {cursor}.")
    for i,c in enumerate(selected,1):
        print(f"[{i}/{size}] {c['symbol']} – {c['name']}")
        try:
            existing[c["symbol"]]=calculate(c,fetch(c["symbol"],key)); success+=1
            print(f"  OK: Score {existing[c['symbol']]['score']}")
        except Exception as e:
            errors.append({"symbol":c["symbol"],"error":str(e)}); print(f"  FEHLER: {e}",file=sys.stderr)
        if i<size: time.sleep(max(0,args.delay))
    if success==0:
        print("FEHLER: Kein Unternehmen konnte verarbeitet werden.",file=sys.stderr)
        return 4
    ranked=sorted(existing.values(),key=lambda x:x.get("score",-1),reverse=True); now=datetime.now(timezone.utc).isoformat()
    write(RESULTS,{"generatedAt":now,"universeSize":len(universe),"screenedThisRun":success,
      "requestedThisRun":size,"nextCursor":(cursor+size)%len(universe),"errors":errors,
      "methodology":"Preisbasierter Recovery-Score; keine Anlageberatung.","results":ranked})
    hist=read(HISTORY,[]); hist.append({"generatedAt":now,"screened":success,"requested":size,"errors":errors,
      "top":[{"symbol":x["symbol"],"score":x["score"]} for x in ranked[:10]]})
    write(HISTORY,hist[-120:]); write(STATE,{"cursor":(cursor+size)%len(universe),"lastRun":now})
    print(f"Fertig: {success}/{size} erfolgreich. Gesamtbestand: {len(ranked)}.")
    return 0

if __name__=="__main__": raise SystemExit(main())
