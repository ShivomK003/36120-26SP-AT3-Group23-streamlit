from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from students.student_d import render

token = st.selectbox('Cryptocurrency', ['BTC', 'ETH', 'XRP', 'SOL', 'DOGE', 'XMR', 'XLM', 'TRX'])
render('https://student-d.example', token)
