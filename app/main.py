
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
        "Market Risk Index",
        "Trend Category",
        "Trading Opportunity Rating",
    ],
    horizontal=True,
    key="selected_page",
)

if page == "Overview":
    st.info("The dashboard is under development.")

    st.subheader("Machine Learning Services")
    st.write("Student A — Asset Performance Index")
    st.write("Student B — Market Risk Index")

    render_home_summary(token)

    st.write("Student D — Trading Opportunity Rating")

elif page == "Market Risk Index":
    show_student_b(token)

elif page == "Trend Category":
    show_student_c(token)

elif page == "Trading Opportunity Rating":
    d_api_url = os.getenv(
        "STUDENT_D_API_URL",
        "https://group23-studentd-tor.onrender.com",
    ).strip()

    if d_api_url:
        student_d.render(d_api_url, token)
    else:
        st.info("Student D's API URL is not configured.")

