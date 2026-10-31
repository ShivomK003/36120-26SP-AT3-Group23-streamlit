from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from students.student_c import show_student_c
from students.student_c_summary import render_home_summary

import streamlit as st

st.set_page_config(
    page_title="Cryptocurrency Financial Intelligence",
    page_icon="📈",
    layout="wide",
)

st.title("Cryptocurrency Financial Intelligence Platform")
st.caption("UTS Advanced Machine Learning — Assignment 3 | Group 23")

# Shared selector and minimal Student C registration; teammate pages stay untouched.
token = st.selectbox("Cryptocurrency", ["BTC", "DOGE", "ETH", "SOL", "TRX", "XLM", "XMR", "XRP"], key="selected_token")
page = st.radio("Page", ["Overview", "Trend Category"], horizontal=True, key="selected_page")
if page == "Overview":
    st.info("The dashboard is under development.")

    st.subheader("Machine Learning Services")
    st.write("Student A — Asset Performance Index")
    st.write("Student B — Market Risk Index")
    render_home_summary(token)
    st.write("Student D — Trend Opportunity Ranking")
else:
    show_student_c(token)
