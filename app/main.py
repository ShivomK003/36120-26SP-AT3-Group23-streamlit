
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from students.student_b import show_student_b
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

# Shared cryptocurrency selector
token = st.selectbox(
    "Cryptocurrency",
    ["BTC", "DOGE", "ETH", "SOL", "TRX", "XLM", "XMR", "XRP"],
    key="selected_token",
)

page = st.radio(
    "Page",
    ["Overview", "Trend Category"],
    horizontal=True,
    key="selected_page",
)

if page == "Overview":
    st.info("The dashboard is under development.")

    st.subheader("Machine Learning Services")

    st.write("Student A — Asset Performance Index")

    # Student B — Market Risk Index
    with st.expander("Student B — Market Risk Index", expanded=False):
        show_student_b(token)

    # Student C — Trend Category
    render_home_summary(token)

    st.write("Student D — Trend Opportunity Ranking")

else:
    show_student_c(token)
