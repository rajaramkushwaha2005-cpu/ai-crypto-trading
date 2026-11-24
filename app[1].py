import time
from datetime import datetime, timezone

import pandas as pd
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "BTCUSD"
TIMEFRAME = "4h"
REFRESH_SECONDS = 30


def get_json(url, params=None):
    response = requests.get(
        url,
        params=params,
        headers={"Accept": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", False):
        raise RuntimeError(f"Delta API returned an unsuccessful response: {payload}")
    return payload.get("result")


def get_ticker_price():
    result = get_json(f"{BASE_URL}/v2/tickers/{SYMBOL}")
    # Delta's ticker response is normally an object; handle list responses too.
    if isinstance(result, list):
        result = next((item for item in result if item.get("symbol") == SYMBOL), result[0] if result else {})
    if not isinstance(result, dict):
        raise RuntimeError("Unexpected ticker response from Delta Exchange.")

    for key in ("close", "last_price", "last", "price", "mark_price"):
        value = result.get(key)
        if value not in (None, ""):
            return float(value), result
    raise RuntimeError(f"Could not find a live price in ticker response. Fields: {list(result.keys())}")


def build_analysis():
    now = int(time.time())
    # Keep the original strategy's 200 four-hour candles.
    start = now - (200 * 4 * 60 * 60)
    params = {
        "resolution": TIMEFRAME,
        "symbol": SYMBOL,
        "start": start,
        "end": now,
    }

    candles = get_json(f"{BASE_URL}/v2/history/candles", params=params)
    df = pd.DataFrame(candles or [])
    if df.empty or "close" not in df.columns:
        raise RuntimeError("No candle data received from Delta Exchange.")

    df = df.sort_values("time").reset_index(drop=True)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])
    if len(df) < 50:
        raise RuntimeError("Not enough candle data to calculate EMA50.")

    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(100)

    last = df.iloc[-1]
    if last["EMA20"] > last["EMA50"] and 50 < last["RSI"] < 70:
        signal = "BUY"
    elif last["EMA20"] < last["EMA50"] and 30 < last["RSI"] < 50:
        signal = "SELL"
    else:
        signal = "WAIT"

    live_price, ticker = get_ticker_price()
    chart_rows = df.tail(80)
    chart = [
        {
            "time": datetime.fromtimestamp(int(row["time"]), tz=timezone.utc).strftime("%d %b %H:%M"),
            "close": round(float(row["close"]), 2),
        }
        for _, row in chart_rows.iterrows()
    ]

    return {
        "symbol": SYMBOL,
        "timeframe": "4 Hours",
        "live_price": live_price,
        "candle_close": round(float(last["close"]), 2),
        "ema20": round(float(last["EMA20"]), 2),
        "ema50": round(float(last["EMA50"]), 2),
        "rsi": round(float(last["RSI"]), 2),
        "signal": signal,
        "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M:%S %p"),
        "chart": chart,
        "refresh_seconds": REFRESH_SECONDS,
        "note": "Signal is calculated from 4-hour candles; live price is from the ticker. No real order is placed.",
    }


@app.route("/")
def home():
    return render_template("index.html", refresh_seconds=REFRESH_SECONDS)


@app.route("/api/analysis")
def analysis_api():
    try:
        return jsonify({"ok": True, "data": build_analysis()})
    except Exception as exc:
        app.logger.exception("Analysis request failed")
        return jsonify({"ok": False, "error": str(exc)}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
