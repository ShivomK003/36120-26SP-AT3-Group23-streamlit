"""Compact live Student C overview; detailed-page design remains independent."""
from datetime import datetime, timezone

import plotly.graph_objects as go
import streamlit as st

from . import student_c_api as api
from . import student_c_data as data


@st.cache_data(ttl=300, max_entries=16, show_spinner=False)
def summary(token, url):
    """Cache successes and unavailable states to avoid retrying every rerun.

    Data uses the existing 15-minute market cache; predictions/errors last five
    minutes and are keyed by the selected token and configured service URL.
    """
    try:
        history = data.cached_history(token, "Bitfinex")
        return api.predict(url, token, history), None
    except (data.MarketDataError, api.StudentCAPIError):
        return None, "Market data or prediction service is unavailable. Try again shortly or open the detailed page."


def _open_details():
    st.session_state.selected_page = "Trend Category"


def render_home_summary(token):
    with st.container(border=True):
        st.subheader(f"Trend Category · {token}")
        st.caption("STUDENT C · SEVEN-DAY OUTLOOK · LIVE BITFINEX INPUTS")
        with st.spinner("Loading Student C outlook…"):
            result, error = summary(token, api.base_url())
        if error:
            st.info(f"Trend outlook unavailable — {error}")
        else:
            left, right = st.columns([1, 1.4])
            with left:
                st.metric("Predicted trend at t+7", result["prediction"])
                st.metric("Confidence", f"{result['confidence']:.1%}")
                st.caption(f"Forecast: {result['prediction_date']} · Observed: {result['as_of_date']}")
            with right:
                fig = go.Figure(go.Bar(
                    x=[result["probabilities"][name] for name in data.CLASSES],
                    y=data.CLASSES, orientation="h",
                    marker_color=["#dc5668", "#e89a56", "#8495ac", "#23aa91", "#568be0"],
                    hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
                fig.update_layout(height=210, margin=dict(l=0,r=15,t=5,b=15),
                                  showlegend=False, xaxis=dict(range=[0,1],tickformat=".0%"),
                                  yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, config={"displayModeBar":False})
            if result["missing_features"] or result["warnings"]:
                st.warning("Degraded prediction: upstream features or warnings were reported. See the detailed page for diagnostics.")
            age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(result["as_of_date"]).date()).days
            if age > 1:
                st.caption(f"Data is {age} calendar days old; this forecast is anchored to the observation date.")
            st.caption("Probabilities reflect model uncertainty. Prediction refresh: five minutes; market-data cache: 15 minutes.")
        st.button("Open Student C trend analysis →", key="c_home_details", on_click=_open_details)
