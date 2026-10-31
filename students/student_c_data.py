"""Student C market ingestion, adapted from the experiments dataset.py.

Completed UTC daily candles, canonical OHLCV schema, no synthetic fallback.
Latest task policy: Alpha Vantage is permitted only for BTC.
"""
import os
from datetime import datetime, timezone
import math
from threading import Lock
import time

import pandas as pd
import requests
import streamlit as st

TOKENS = ["BTC", "DOGE", "ETH", "SOL", "TRX", "XLM", "XMR", "XRP"]
COLUMNS = ["date", "open", "high", "low", "close", "volume"]
BITFINEX_SYMBOLS = {token: ("tDOGE:USD" if token == "DOGE" else f"t{token}USD") for token in TOKENS}
_request_lock = Lock()
_last_request = 0.0


class MarketDataError(ValueError):
    """Provider or OHLCV validation failure safe to display to users."""


def alpha_vantage_key():
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("ALPHA_VANTAGE_API_KEY", "")
    except (FileNotFoundError, KeyError):
        return ""


def validate_history(frame, today=None):
    if not set(COLUMNS).issubset(frame.columns):
        raise MarketDataError("Provider response is missing required OHLCV columns.")
    frame = frame[COLUMNS].copy()
    try:
        dates = pd.to_datetime(frame.date, utc=True, errors="raise")
        if dates.isna().any() or not dates.eq(dates.dt.normalize()).all():
            raise ValueError("Dates must identify completed UTC daily candles")
        frame["date"] = dates.dt.tz_localize(None)
        for column in COLUMNS[1:]:
            if frame[column].map(lambda x: isinstance(x, bool)).any():
                raise ValueError("Boolean OHLCV values")
            frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
        if not all(math.isfinite(v) for v in frame[COLUMNS[1:]].to_numpy().flat):
            raise ValueError("Non-finite OHLCV values")
    except (ValueError, TypeError, OverflowError) as exc:
        raise MarketDataError("Provider returned invalid dates or numeric OHLCV values.") from exc
    if ((frame[["open", "high", "low", "close"]] <= 0).any().any()
            or (frame.volume < 0).any()
            or (frame.low > frame[["open", "close"]].min(axis=1)).any()
            or (frame.high < frame[["open", "close"]].max(axis=1)).any()):
        raise MarketDataError("Provider returned inconsistent OHLC ranges, prices or volume.")
    # Exact duplicate records are safe to remove; conflicting candles are rejected.
    frame = frame.drop_duplicates().sort_values("date", kind="stable")
    if frame.date.duplicated().any():
        raise MarketDataError("Provider returned conflicting candles for the same date.")
    today = today or datetime.now(timezone.utc).date()
    frame = frame.loc[frame.date.dt.date < today].reset_index(drop=True)
    if len(frame) < 21:
        raise MarketDataError("At least 21 completed daily OHLCV observations are required.")
    return frame


def _get(url, params):
    # Match the reference's 2-second request spacing, shared per process.
    global _last_request
    with _request_lock:
        remaining = 2 - (time.monotonic() - _last_request)
        if remaining > 0:
            time.sleep(remaining)
        _last_request = time.monotonic()
        response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_history(token, source="Bitfinex", api_key=""):
    """Uncached pure adapter; cache boundary lives below for predictable tests."""
    if token not in TOKENS:
        raise MarketDataError("Unsupported cryptocurrency.")
    if source not in ["Bitfinex", "Alpha Vantage"]:
        raise MarketDataError("Unsupported market provider.")
    if source == "Alpha Vantage" and token != "BTC":
        raise MarketDataError("Alpha Vantage is restricted to BTC; use Bitfinex for other tokens.")
    if source == "Alpha Vantage" and not api_key:
        raise MarketDataError("BTC Alpha Vantage requires ALPHA_VANTAGE_API_KEY in environment or Streamlit secrets.")
    try:
        if source == "Bitfinex":
            body = _get(f"https://api-pub.bitfinex.com/v2/candles/trade:1D:{BITFINEX_SYMBOLS[token]}/hist",
                        {"limit": 250, "sort": -1})
            if not isinstance(body, list) or not body:
                raise MarketDataError("Bitfinex returned no daily candles; check availability or rate limits.")
            frame = pd.DataFrame(body, columns=["timestamp", "open", "close", "high", "low", "volume"])
            frame["date"] = pd.to_datetime(frame.timestamp, unit="ms", utc=True, errors="raise")
        else:
            body = _get("https://www.alphavantage.co/query", {
                "function": "DIGITAL_CURRENCY_DAILY", "symbol": "BTC", "market": "USD", "apikey": api_key})
            series = body.get("Time Series (Digital Currency Daily)")
            if not isinstance(series, dict) or not series:
                raise MarketDataError("Alpha Vantage returned no daily series; check credentials, quota or rate limits.")
            frame = pd.DataFrame.from_dict(series, orient="index")
            frame["date"] = frame.index
            frame = frame.rename(columns={f"{i}. {name}": name for i, name in enumerate(COLUMNS[1:], 1)})
        return validate_history(frame).tail(250).reset_index(drop=True)
    except MarketDataError:
        raise
    except (requests.RequestException, ValueError, TypeError, KeyError, OverflowError, AttributeError) as exc:
        raise MarketDataError(f"{source} daily data is unavailable or malformed. Check connectivity and provider rate limits.") from exc


@st.cache_data(ttl=900, max_entries=16, show_spinner=False)
def cached_history(token, source="Bitfinex", _api_key=""):
    return fetch_history(token, source, _api_key)


def indicators(history):
    frame = history.copy()
    frame["MA5"] = frame.close.rolling(5, min_periods=5).mean()
    frame["MA20"] = frame.close.rolling(20, min_periods=20).mean()
    frame["Return20"] = (frame.close - frame.close.shift(20)) / frame.close.shift(20)
    frame["TrendScore"] = .7 * (frame.MA5 / frame.MA20 - 1) + .3 * frame.Return20
    frame["regime"] = frame.TrendScore.map(trend_label)
    return frame


CLASSES = ["Strong Downtrend", "Downtrend", "Sideways", "Uptrend", "Strong Uptrend"]


def trend_label(score):
    if pd.isna(score): return None
    if score < -.10: return CLASSES[0]
    if score < -.02: return CLASSES[1]
    if score <= .02: return CLASSES[2]
    if score <= .10: return CLASSES[3]
    return CLASSES[4]
