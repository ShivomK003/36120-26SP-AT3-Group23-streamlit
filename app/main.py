"""Shared currency selection, overview and member analytics pages."""
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from students import student_a, student_b, student_c, student_d

st.set_page_config(
    page_title="Cryptocurrency Financial Intelligence",
    page_icon="📈",
    layout="wide",
)

st.title("Cryptocurrency Financial Intelligence Platform")
st.caption("UTS Advanced Machine Learning — Assignment 3 | Group 23")

token = st.selectbox('Cryptocurrency', ['BTC', 'ETH', 'XRP', 'SOL', 'DOGE', 'XMR', 'XLM', 'TRX'])
d_api_url = os.getenv('STUDENT_D_API_URL', '')
overview, a_tab, b_tab, c_tab, d_tab = st.tabs([
    'Overview', 'Asset Performance Index', 'Market Risk Index', 'Trend Category', 'Trading Opportunity Rating'
])

with overview:
    st.subheader(f'{token} market overview')
    if d_api_url:
        st.subheader('Trading activity')
        student_d.volume_panel(d_api_url, token)
    else:
        st.info('The trading activity service is being prepared.')

for tab, module, setting, title in [
    (a_tab, student_a, 'STUDENT_A_API_URL', 'Asset Performance Index'),
    (b_tab, student_b, 'STUDENT_B_API_URL', 'Market Risk Index'),
    (c_tab, student_c, 'STUDENT_C_API_URL', 'Trend Category'),
]:
    with tab:
        render = getattr(module, 'render', None)
        if callable(render):
            render(os.getenv(setting, ''), token)
        else:
            st.info(f'The {title} page is being prepared.')

with d_tab:
    if d_api_url:
        student_d.render(d_api_url, token)
    else:
        st.info('The trading outlook service is being prepared.')
