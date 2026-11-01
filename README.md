# Cryptocurrency Financial Intelligence Platform

UTS Advanced Machine Learning and Applications — Assignment 3, Group 23.

## Overview

Shared Streamlit frontend integrating the individual machine learning APIs developed by Group 23.

## Project Structure

- `app/main.py` — Streamlit application entry point
- `students/student_a.py` — Asset Performance Index
- `students/student_b.py` — Market Risk Index
- `students/student_c.py` — Trend Classification
- `students/student_d.py` — Trend Opportunity Ranking

## Local Setup

Requires Python 3.12 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
