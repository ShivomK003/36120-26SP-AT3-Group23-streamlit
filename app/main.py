
import streamlit as st

from students.student_b import show_student_b

st.set_page_config(
    page_title="Cryptocurrency Financial Intelligence",
    page_icon="📈",
    layout="wide",
)

st.title("Cryptocurrency Financial Intelligence Platform")
st.caption("UTS Advanced Machine Learning — Assignment 3 | Group 23")

st.markdown(
    "Explore seven-day cryptocurrency market predictions generated "
    "by four independently deployed machine learning services."
)

TOKENS = ["BTC", "ETH", "XRP", "SOL", "DOGE", "XMR", "XLM", "TRX"]

token = st.selectbox(
    "Select Cryptocurrency",
    TOKENS,
    index=0,
)

st.divider()

tab_a, tab_b, tab_c, tab_d = st.tabs(
    [
        "Asset Performance Index",
        "Market Risk Index",
        "Trend Category",
        "Trading Opportunity Rating",
    ]
)

with tab_a:
    st.header("Student A — Asset Performance Index")
    st.info("Student A's dashboard will be integrated here.")

with tab_b:
    show_student_b(token)

with tab_c:
    st.header("Student C — Trend Category")
    st.info("Student C's dashboard will be integrated here.")

with tab_d:
    st.header("Student D — Trading Opportunity Rating")
    st.info("Student D's dashboard will be integrated here.")
