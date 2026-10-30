import requests
import pandas as pd
import streamlit as st
from typing import List, Dict
from threading import Lock
from cachetools import TTLCache

#------------------------------------------------------------
# Configuration
#------------------------------------------------------------
API_BASE_URL = "https://three6120-26sp-at3-api.onrender.com"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
REQUEST_TIMEOUT = 20  # Accommodates cold start on Render free tier

# Map token symbols to CoinGecko API IDs
COIN_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "XRP": "ripple",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "XMR": "monero",
    "XLM": "stellar",
    "TRX": "tron"
}

live_ohlcv_lock = Lock()
live_ohlcv_cache = TTLCache(maxsize=20, ttl=60)
pred_lock = Lock()
pred_cache = TTLCache(maxsize=20, ttl=60)

#------------------------------------------------------------
# Unified API Error Handler
#------------------------------------------------------------
def _safe_api_call(func):
    """
    Decorator to catch all API exceptions and return standardized results.
    Ensures that a single API failure does not break the entire application.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out. The service may be cold starting. Please try again."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Unable to connect to the API service. Please check if the service is running."}
        except Exception as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
    return wrapper

#------------------------------------------------------------
# Backend Prediction API Wrappers
#------------------------------------------------------------
@_safe_api_call
def get_health() -> Dict:
    """Check backend API service health status"""
    resp = requests.get(f"{API_BASE_URL}/health", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return {"success": True, "data": resp.json()}

@_safe_api_call
def get_model_metadata() -> Dict:
    """Fetch model metadata: algorithm, target, horizon and feature importance"""
    resp = requests.get(f"{API_BASE_URL}/model-metadata", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    result = {"success": True, "data": resp.json()}
    return result

@_safe_api_call
def get_prediction(token: str, forecast_horizon: int = 7) -> Dict:
    """Call prediction endpoint to get 7-day API score forecast"""
    payload = {"token": token, "forecast_horizon": forecast_horizon}
    key = (token, forecast_horizon)
    with pred_lock:
        if key in pred_cache:
            print(f"[PRED CACHE HIT] {key}")
            return pred_cache[key].copy()
        else:
            print(f"[PRED CACHE MISS] {key}")     
            resp = requests.post(
                f"{API_BASE_URL}/predict",
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            result = {"success": True, "data": resp.json()}
            pred_cache[key] = result.copy()
            return result

@_safe_api_call
def get_engineered_features(ohlcv_data: List[Dict]) -> Dict:
    """Call feature engineering endpoint to calculate derived indicators"""
    payload = {"ohlcv_data": ohlcv_data}
    resp = requests.post(
        f"{API_BASE_URL}/features",
        json=payload,
        timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    result = {"success": True, "data": resp.json()}
    return result

#------------------------------------------------------------
# Live Market Data (CoinGecko Public API)
#------------------------------------------------------------
@_safe_api_call
def get_live_ohlcv(token: str, days: int = 30) -> List[Dict]:
    """
    Fetch live OHLCV data from CoinGecko public API.
    """
    coin_id = COIN_ID_MAP.get(token)
    if not coin_id:
        return {"success": False, "error": "Unsupported cryptocurrency"}
    
    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": days}
    key = token
    with live_ohlcv_lock:
        if key in live_ohlcv_cache:
            print(f"[LIVE OHLCV CACHE HIT] {token}")
            return live_ohlcv_cache[key].copy()
        else:
            print(f"[LIVE OHLCV CACHE MISS] {token}")        
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            raw_data = resp.json()
            formatted_data = []
            for entry in raw_data:
                timestamp, open_p, high_p, low_p, close_p = entry
                date_str = pd.to_datetime(timestamp, unit="ms").strftime("%Y-%m-%d")
                formatted_data.append({
                    "date": date_str,
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                    "volume": 0  # CoinGecko free OHLCV does not include volume
                })
            result = {"success": True, "data": formatted_data}
            live_ohlcv_cache[key] = result.copy()
            return result

#------------------------------------------------------------
# Homepage Card Render (for dashboard view)
#------------------------------------------------------------
def render_api_home_card(token: str):
    """
    Render a compact visualisation card for the homepage dashboard.
    Shows closing price trend + latest API forecast score.
    """
    st.subheader("Asset Performance Index")
    
    # Fetch live market data
    ohlcv_result = get_live_ohlcv(token)
    if not ohlcv_result["success"]:
        st.warning("Market data unavailable")
        return
    
    df_ohlcv = pd.DataFrame(ohlcv_result["data"])
    st.line_chart(df_ohlcv.set_index("date")["close"], height=200)
    
    # Fetch latest prediction
    pred_result = get_prediction(token)
    if pred_result["success"]:
        score = pred_result["data"].get("predicted_score", 0)
        st.metric(label="7-Day API Forecast", value=round(score, 4))
    else:
        st.caption("Prediction service unavailable")

#------------------------------------------------------------
# Full Tab Render Function (called by main.py)
#------------------------------------------------------------
def render_api_tab(token: str):
    """
    Render the full Asset Performance Index tab page.
    Includes prediction results, feature engineering and model metadata.
    Receives the globally selected cryptocurrency token as input.
    """
    st.header("Asset Performance Index (API)")
    st.caption("7-day composite performance forecast powered by XGBoost | Student A Module")

    # Sidebar: service health check
    # with st.sidebar:
    #     st.subheader("API Service Status")
    #     if st.button("Check Connectivity", key="a_health_check"):
    #         result = get_health()
    #         if result["success"]:
    #             st.success("Service is running normally")
    #         else:
    #             st.warning(f"{result['error']}")

    ## Section 1: service health check
    st.subheader("API Service Status")
    if st.button("Check Connectivity", key="a_health_check_2"):
        result = get_health()
        if result["success"]:
            st.success("Service is running normally")
        else:
            st.warning(f"{result['error']}")
    
    st.divider()
    
    ## Section 2: Prediction Result
    st.subheader("7-Day API Score Forecast")
    
    col_pred, col_info = st.columns([2, 1])
    with col_pred:
        if st.button("Generate Prediction", type="primary", key="a_predict_btn"):
            with st.spinner("Calling prediction API. First request may take a moment for cold start..."):
                res = get_prediction(token=token, forecast_horizon=7)
                if res["success"]:
                    predicted_score = res["data"].get("predicted_score", 0)
                    st.metric(
                        label=f"{token} 7-Day API Forecast",
                        value=round(predicted_score, 4),
                        delta="Composite Performance Score"
                    )
                    with st.expander("View full response"):
                        st.json(res["data"])
                else:
                    st.error(res["error"])
                    st.info("Note: A single API failure does not affect other features of the platform.")

    with col_info:
        st.info("""
        **About this index**
        The Asset Performance Index evaluates short-term cryptocurrency performance
        across four dimensions: return strength, trend momentum, trading activity
        and price stability.
        """)

    st.divider()

    ## Section 3: Feature Engineering & Market Chart
    st.subheader("Engineered Features")
    st.markdown("Calculate derived indicators such as returns and momentum from live market data")

    ohlcv_result = get_live_ohlcv(token)
    if not ohlcv_result["success"]:
        st.error(f"Failed to load market data: {ohlcv_result['error']}")
    else:
        df_ohlcv = pd.DataFrame(ohlcv_result["data"])
        col1, col2 = st.columns([3, 2])
        with col1:
            st.line_chart(df_ohlcv.set_index("date")["close"], height=300)
            st.caption(f"Recent {token} closing price trend (live data from CoinGecko)")

        with col2:
            if st.button("Calculate Features", key="a_feature_btn"):
                with st.spinner("Calling feature calculation API..."):
                    res = get_engineered_features(ohlcv_result["data"])
                    if res["success"]:
                        st.success("Feature calculation completed")
                        feat_dict = res["data"].get("features", {})
                        df_features = pd.DataFrame([
                            {"FeatureName": k, "Value": v} for k, v in feat_dict.items()
                        ])
                        st.dataframe(df_features, width="stretch")
                    else:
                        st.error(res["error"])

    st.divider()

    ## Section 4: Model Metadata
    st.subheader("Model Metadata")
    if st.button("Load Model Details", key="a_meta_btn"):
        res = get_model_metadata()
        if res["success"]:
            data = res["data"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Algorithm", data.get("algorithm", "-"))
            col2.metric("Target", data.get("target", "-"))
            col3.metric("Horizon", f"{data.get('horizon', '-')} days")
            
            if "feature_importance" in data:
                st.markdown("**Feature Importance**")
                fi_df = pd.DataFrame(
                    list(data["feature_importance"].items()),
                    columns=["Feature", "Importance"]
                )
                st.bar_chart(fi_df.set_index("Feature"))
        else:
            st.error(res["error"])

