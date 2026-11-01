"""Student C Trend Category page; compatible with a shared token selector."""
from datetime import datetime, timedelta, timezone

import plotly.graph_objects as go
import streamlit as st

from . import student_c_api as api
from . import student_c_data as data

COLORS = ["#dc5668", "#e89a56", "#8495ac", "#23aa91", "#568be0"]


def _chart(fig, height=380):
    fig.update_layout(height=height, margin=dict(l=15,r=15,t=30,b=20),
                      legend=dict(orientation="h", y=1.15), hovermode="x unified")
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, config={"displayModeBar": False})


def render(api_url=None, token="BTC"):
    """Register with render(url, token), or use show_student_c(token)."""
    url = (api_url or api.base_url()).rstrip("/")
    st.header(f"Trend Category · {token}")
    st.caption("STUDENT C · XGBOOST CLASSIFICATION · SEVEN-CALENDAR-DAY OUTLOOK")
    st.write("Calculate historical market regimes, then request a future trend classification from the independent Student C service.")
    options = ["Bitfinex", "Alpha Vantage"] if token == "BTC" else ["Bitfinex"]
    source = st.selectbox("Daily OHLCV provider", options, key=f"c_source_{token}")
    state_key = f"c_market_{token}_{source}"
    prediction_key = f"c_prediction_{token}_{source}"
    st.caption("Real provider data only · completed UTC days · 15-minute cache · Alpha Vantage restricted to BTC")
    if st.button("Fetch latest market data", key="c_fetch", type="primary"):
        # Clear previous displays first so a failed fetch cannot look successful.
        st.session_state.pop(state_key, None)
        st.session_state.pop(prediction_key, None)
        try:
            with st.spinner("Retrieving daily market observations…"):
                history = data.cached_history(token, source, data.alpha_vantage_key() if source == "Alpha Vantage" else "")
            st.session_state[state_key] = history
        except data.MarketDataError as exc:
            st.error(str(exc))
    history = st.session_state.get(state_key)
    if history is None:
        st.info("Fetch market data to see price history, historical regimes and enable prediction. No synthetic data is substituted.")
        return
    frame = data.indicators(history)
    as_of = frame.date.iloc[-1].date()
    target = as_of + timedelta(days=7)
    age = (datetime.now(timezone.utc).date() - as_of).days
    a,b,c = st.columns(3)
    a.metric("Last market observation (UTC)", str(as_of))
    b.metric("Forecast date · t+7", str(target))
    c.metric("Completed observations", len(history))
    st.caption(f"Source: {source} · USD daily candles. Forecast dates are anchored to the last observation, not today's date.")
    if age > 1:
        st.warning(f"Latest provider candle is {age} calendar days old. Any prediction is relative to {as_of}, not current market conditions.")
    gaps = int(frame.date.diff().dt.days.gt(1).sum())
    if gaps:
        st.info(f"History contains {gaps} date gaps. Indicators use trailing observations without filling missing dates, matching training.")
    if st.button("Predict seven-day trend", key="c_predict", type="primary"):
        st.session_state.pop(prediction_key, None)
        try:
            with st.spinner("Requesting Student C prediction (up to 45 seconds)…"):
                st.session_state[prediction_key] = api.predict(url, token, history)
        except api.StudentCAPIError as exc:
            st.error(str(exc))
    result = st.session_state.get(prediction_key)
    if result:
        a,b,c = st.columns(3)
        a.metric("Predicted trend at t+7", result["prediction"])
        b.metric("Classification confidence", f"{result['confidence']:.1%}")
        c.metric("API forecast date", result["prediction_date"])
        st.caption("Model-predicted future category · class probability is not a guarantee of future returns.")
        if result["missing_features"] or result["warnings"]:
            st.warning("The API reported degraded inputs or upstream warnings. Review diagnostics before interpreting this prediction.")
        st.subheader("Five-class prediction probabilities")
        fig = go.Figure(go.Bar(x=data.CLASSES, y=list(result["probabilities"].values()), marker_color=COLORS))
        fig.update_yaxes(range=[0,1], tickformat=".0%", title="Model probability")
        _chart(fig, 320)
    else:
        st.info("No future prediction yet. The charts below describe observed history only.")
    st.subheader("Historical price & moving averages")
    days = st.select_slider("Visible history", options=[30,60,90,180,250], value=180, key="c_window")
    visible = frame.tail(days)
    fig = go.Figure()
    for name, color in [("close", "#568be0"), ("MA5", "#23aa91"), ("MA20", "#e89a56")]:
        fig.add_scatter(x=visible.date, y=visible[name], name=name, line=dict(color=color, width=2 if name=="close" else 1.5))
    if result:
        fig.add_vrect(x0=frame.date.iloc[-1], x1=frame.date.iloc[-1]+timedelta(days=7),
                      fillcolor=COLORS[result["class_id"]], opacity=.14, line_width=0)
        fig.add_annotation(x=frame.date.iloc[-1]+timedelta(days=3.5), y=1, yref="paper",
                           text=f"t+7: {result['prediction']}", showarrow=False)
        fig.update_xaxes(range=[visible.date.iloc[0],frame.date.iloc[-1]+timedelta(days=8)])
    fig.update_yaxes(title="USD price")
    _chart(fig, 470)
    st.caption("MA5/MA20 are calculated from the same observed closes sent to the API. Shading identifies a prediction horizon only; no future prices or moving averages are drawn.")
    with st.expander("Historical regimes · calculated rules, not future predictions", expanded=True):
        st.latex(r"TrendScore_t = 0.7(MA5_t/MA20_t - 1) + 0.3Return20_t")
        fig = go.Figure()
        valid = visible.dropna(subset=["TrendScore"])
        for label, color in zip(data.CLASSES, COLORS):
            group = valid.loc[valid.regime == label]
            fig.add_scatter(x=group.date,y=group.TrendScore, mode="markers",name=label,marker=dict(color=color,size=6))
        for threshold in [-.10,-.02,.02,.10]:
            fig.add_hline(y=threshold,line_dash="dot",line_color="#8a94a8")
        fig.update_yaxes(title="Observed TrendScore",tickformat=".0%")
        _chart(fig,350)
        st.caption("Strong Downtrend < −0.10; Downtrend −0.10 to < −0.02; Sideways −0.02 to 0.02 inclusive; Uptrend > 0.02 to 0.10; Strong Uptrend > 0.10. First 20 observations have no regime. These are historical rule labels, not model predictions.")
    with st.expander("Model information & genuine global feature importance"):
        st.write("Prediction service: XGBoost multiclass classifier · horizon 7 days. Local calculations are indicators only; inference runs through HTTP.")
        metadata_key = f"c_metadata_{url}"
        if st.button("Load model metadata", key="c_metadata"):
            st.session_state.pop(metadata_key, None)
            try:
                st.session_state[metadata_key] = api.metadata(url)
            except api.StudentCAPIError as exc:
                st.info(str(exc))
        metadata = st.session_state.get(metadata_key)
        if metadata:
            items = sorted(metadata["feature_importance"].items(),key=lambda item:item[1])
            fig = go.Figure(go.Bar(y=[k for k,v in items],x=[v for k,v in items],orientation="h",marker_color="#23aa91"))
            fig.update_xaxes(title="Global model feature importance")
            _chart(fig,max(350,len(items)*28))
            st.json({k:metadata[k] for k in ["algorithm","features","class_names","forecast_horizon"]})
            st.caption("Fetched from the deployed model-metadata endpoint; global importance is not a per-prediction explanation.")
        else:
            st.caption("Importance is hidden until genuine model metadata is successfully retrieved. No mock importance is shown.")
    with st.expander("API diagnostics & data provenance", expanded=bool(result and (result["warnings"] or result["missing_features"]))):
        st.json({"service":url,"token":token,"provider":source,"as_of_date":str(as_of),
                 "prediction_date":result["prediction_date"] if result else None,
                 "class_id":result["class_id"] if result else None,
                 "missing_features":result["missing_features"] if result else [],
                 "warnings":result["warnings"] if result else [],
                 "prediction_requested":result is not None})


def show_student_c(token):
    render(token=token)
