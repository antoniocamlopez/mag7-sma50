import csv, json
from datetime import datetime, timezone
from urllib.request import urlopen, Request

TICKERS = [
  "AAPL","MSFT","AMZN","GOOGL","META","TSLA","NVDA",
  "AVGO","BRK-B","LLY","V","JPM","XOM","WMT","UNH"
]

BAND = 0.015          # ±1,5%
STOP_PCT = 0.05       # -5%
TARGET_PCT = 0.05     # +5%
SMA_SLOPE_LOOKBACK = 5  # SMA50 hoy > SMA50 hace 5 sesiones
MIN_ROWS = 260

def stooq_csv_url(ticker: str) -> str:
    return f"https://stooq.com/q/d/l/?s={ticker}.US&i=d"

def fetch_daily_closes(ticker: str):
    req = Request(stooq_csv_url(ticker), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(text.splitlines())
    rows = [(row["Date"], float(row["Close"])) for row in reader]
    if len(rows) < MIN_ROWS:
        raise RuntimeError(f"{ticker}: insuficientes datos ({len(rows)})")
    return rows

def sma(values, n):
    return sum(values[-n:]) / n

def main():
    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rows": []
    }

    for t in TICKERS:
        data = fetch_daily_closes(t)
        closes = [c for _, c in data]
        close_today = closes[-1]

        sma50_today = sma(closes, 50)
        sma50_prev = sum(closes[-50 - SMA_SLOPE_LOOKBACK:-SMA_SLOPE_LOOKBACK]) / 50
        sma_up = sma50_today > sma50_prev

        sma200_today = sma(closes, 200)
        sma200_prev = sum(closes[-200 - SMA_SLOPE_LOOKBACK:-SMA_SLOPE_LOOKBACK]) / 200
        sma200_up = sma200_today > sma200_prev

      
        zone_low = sma50_today * (1 - BAND)
        zone_high = sma50_today * (1 + BAND)

        if close_today < zone_low:
            signal = "TOO_LOW"
            entry_ref = zone_low
        elif close_today > zone_high:
            signal = "TOO_HIGH"
            entry_ref = zone_high
        else:
            signal = "IN_ZONE"
            entry_ref = close_today

        stop = entry_ref * (1 - STOP_PCT)
        target = entry_ref * (1 + TARGET_PCT)

        alert = (signal == "IN_ZONE") and sma_up

        out["rows"].append({
            "ticker": t,
            "close": close_today,
            "sma200": sma200_today,
            "sma200_up": sma200_up,
            "sma50": sma50_today,
            "sma50_up": sma_up,
            "zone_low": zone_low,
            "zone_high": zone_high,
            "signal": signal,
            "entry_ref": entry_ref,
            "stop": stop,
            "target": target,
            "alert": alert
        })

    with open("signals.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
