
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from students.student_a import render_api_home_card, render_api_tab
from students.student_b import show_student_b
from students.student_c import show_student_c
from students.student_c_summary import render_home_summary
from students import student_d

import streamlit as st

st.set_page_config(
    page_title="Cryptocurrency Financial Intelligence",
    page_icon="📈",
    layout="wide",
)

st.title("Cryptocurrency Financial Intelligence Platform")
st.caption("UTS Advanced Machine Learning — Assignment 3 | Group 23")

# Shared cryptocurrency selector
token = st.selectbox(
    "Cryptocurrency",
    ["BTC", "DOGE", "ETH", "SOL", "TRX", "XLM", "XMR", "XRP"],
    key="selected_token",
)



page = st.radio(
    "Page",
    [
        "Overview",
        "Asset Performance Index",
        "Market Risk Index",
        "Trend Category",
        "Trading Opportunity Rating",
    ],
    horizontal=True,
    key="selected_page",
)

d_api_url = os.getenv(
    "STUDENT_D_API_URL",
    "https://group23-studentd-tor.onrender.com",
).strip()

if page == "Overview":
    st.subheader(f"{token} Market Overview")

    # Student A — Asset Performance Index
    render_api_home_card(token)

    # Student B — Market Risk Index
    st.write("Student B — Market Risk Index")

    # Student C — Trend Category
    render_home_summary(token)

    # Student D — Trading Opportunity Rating
    st.subheader("Student D — Trading activity")
    if d_api_url:
        student_d.volume_panel(d_api_url, token)
    else:
        st.info("Student D's API URL is not configured.")

elif page == "Asset Performance Index":
    render_api_tab(token)

elif page == "Market Risk Index":
    show_student_b(token)

elif page == "Trend Category":
    show_student_c(token)

elif page == "Trading Opportunity Rating":
    if d_api_url:
        student_d.render(d_api_url, token)
    else:
        st.info("Student D's API URL is not configured.")

