import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE = "https://api.massive.com"
API_KEY = os.environ.get("MASSIVE_API_KEY")
MIN_CAP = 50_000_000
MAX_CAP = 300_000_000
TARGET_COUNT = 20
MAX_CANDIDATES = 450
REQUEST_GAP = 12.2  # Stocks Basic is limited to 5 requests per minute.
LAST_REQUEST = 0.0
SESSION = requests.Session()

def api_get(path, params=None):
    global LAST_REQUEST
    if not API_KEY:
        raise RuntimeError("Missing MASSIVE_API_KEY environment variable.")
    elapsed = time.monotonic() - LAST_REQUEST
    if LAST_REQUEST and elapsed < REQUEST_GAP:
        time.sleep(REQUEST_GAP - elapsed)
    p = dict(params or {})
    p["apiKey"] = API_KEY
    response = SESSION.get(BASE + path, params=p, timeout=45)
    LAST_REQUEST = time.monotonic()
    if response.status_code == 429:
        time.sleep(65)
        response = SESSION.get(BASE + path, params=p, timeout=45)
        LAST_REQUEST = time.monotonic()
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") == "ERROR":
        raise RuntimeError(payload.get("error") or payload.get("message") or "Massive API error")
    return payload

def grouped_for_date(day):
    return api_get(f"/v2/aggs/grouped/locale/us/market/stocks/{day.isoformat()}",
                   {"adjusted":"true"})

def find_latest_sessions():
    # Search backward to accommodate weekends, holidays, and delayed publication.
    today = datetime.now(ZoneInfo("America/New_York")).date()
    found = []
    for offset in range(0, 12):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        payload = grouped_for_date(d)
        results = payload.get("results") or []
        if results:
            found.append((d, results))
            if len(found) == 2:
                return found[0], found[1]
    raise RuntimeError("Could not find two recent trading sessions with grouped daily data.")

def calc_ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1-alpha) * result[-1])
    return result

def calculate_macd(bars):
    closes = [float(b["c"]) for b in bars]
    if len(closes) < 35:
        return None
    ema12, ema26 = calc_ema(closes,12), calc_ema(closes,26)
    line = [a-b for a,b in zip(ema12,ema26)]
    signal = calc_ema(line,9)
    hist = [a-b for a,b in zip(line,signal)]
    points = []
    for bar, value in zip(bars[-5:],hist[-5:]):
        d = datetime.fromtimestamp(bar["t"]/1000,timezone.utc).date().isoformat()
        points.append({"date":d,"value":round(value,6)})
    return {"macd":round(line[-1],6),"signal":round(signal[-1],6),
            "latest_histogram":round(hist[-1],6),"histogram":points}

def get_ticker_overview(ticker):
    payload = api_get(f"/v3/reference/tickers/{ticker}")
    return payload.get("results") or {}

def get_daily_history(ticker, start, end):
    payload = api_get(f"/v2/aggs/ticker/{ticker}/range/1/day/{start.isoformat()}/{end.isoformat()}",
                      {"adjusted":"true","sort":"asc","limit":5000})
    return payload.get("results") or []

def date_from_bar(bar):
    return datetime.fromtimestamp(bar["t"]/1000,timezone.utc).date().isoformat()

def process():
    latest, previous = find_latest_sessions()
    session_date, today_bars = latest
    previous_date, prior_bars = previous
    prior_close = {b["T"]:float(b["c"]) for b in prior_bars if b.get("T") and b.get("c") is not None}
    decliners=[]
    for bar in today_bars:
        ticker=bar.get("T")
        close=bar.get("c")
        old=prior_close.get(ticker)
        if not ticker or close is None or not old or old <= 0:
            continue
        change=(float(close)-old)/old*100
        if change < 0:
            decliners.append((change,ticker,float(close)))
    decliners.sort(key=lambda x:x[0])
    print(f"{session_date}: found {len(decliners)} negative movers; checking up to {MAX_CANDIDATES} market caps.")

    selected=[]
    checked=0
    end_date=session_date
    start_date=end_date-timedelta(days=370)
    for change,ticker,close in decliners[:MAX_CANDIDATES]:
        checked += 1
        try:
            overview=get_ticker_overview(ticker)
            cap=overview.get("market_cap")
            name=overview.get("name") or ticker
            if cap is None or not (MIN_CAP <= float(cap) <= MAX_CAP):
                continue
            bars=get_daily_history(ticker,start_date,end_date)
            macd=calculate_macd(bars)
            if not macd:
                continue
            sorted_highs=sorted(bars,key=lambda b:float(b.get("h",0)),reverse=True)[:3]
            sorted_lows=sorted(bars,key=lambda b:float(b.get("l",float("inf"))))[:3]
            selected.append({
                "ticker":ticker,"name":name,"close":round(close,4),
                "change_pct":round(change,4),"market_cap":round(float(cap)),
                "macd":macd,
                "highs":[{"date":date_from_bar(b),"price":round(float(b["h"]),4)} for b in sorted_highs],
                "lows":[{"date":date_from_bar(b),"price":round(float(b["l"]),4)} for b in sorted_lows]
            })
            print(f"Qualified {len(selected)}/{TARGET_COUNT}: {ticker} ({cap:,.0f})")
            if len(selected)>=TARGET_COUNT:
                break
        except requests.RequestException as exc:
            print(f"Skipping {ticker}: request problem: {exc}")
        except (KeyError,TypeError,ValueError,RuntimeError) as exc:
            print(f"Skipping {ticker}: {exc}")

    note=(f"Checked {checked} of the session's largest decliners. "
          f"Found {len(selected)} stocks in the $50M–$300M market-cap range. "
          f"Free data-plan request limits may prevent a full list of 20.")
    output={
        "provider":"Massive (Stocks Basic)",
        "session_date":session_date.isoformat(),
        "comparison_session":previous_date.isoformat(),
        "updated_at":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "market_cap_min":MIN_CAP,"market_cap_max":MAX_CAP,
        "stocks":selected,"note":note,
        "scan_complete":len(selected)>=TARGET_COUNT
    }
    Path("data").mkdir(exist_ok=True)
    Path("data/stocks.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    print(note)

if __name__=="__main__":
    process()
