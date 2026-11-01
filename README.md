# Cryptocurrency Financial Intelligence Platform

UTS Advanced Machine Learning and Applications — Assignment 3, Group 23.

## Overview

Shared Streamlit frontend integrating the individual machine learning APIs developed by Group 23.

## Project Structure

- `app/main.py` — Streamlit application entry point
- `students/student_a.py` — Asset Performance Index
- `students/student_b.py` — Market Risk Index
- `students/student_c.py` — Trend Classification
- `students/student_d.py` — Trading Opportunity Rating

## Local Setup

Requires Python 3.12.13.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py

```

## Student D integration

D preview: https://group23-crypto-preview.streamlit.app . It runs `frontend-student-d-tor` from the private fork `RainyxWang/36120-26SP-AT3-Group23-streamlit-preview`, because Streamlit Community Cloud requires repository administrator access. The upstream PR remains the group review path. This preview supplies D and shared navigation; A/B/C pages are still being developed by their owners.

D API: https://group23-studentd-tor.onrender.com . Root, health, model metadata and all eight feature/prediction pairs passed live checks on 30 October 2026.

Yuxiang Wang (25509050) provides `students/student_d.py`. The homepage calls `volume_panel(api_url, token)` and the TOR tab calls `render(api_url, token)`. Both use HTTP only. Set `STUDENT_D_API_URL` to the verified D Render base URL in the deployment environment. The page contains failures and labels forecasts with missing peer indicators.

The shared entry point supplies one currency selection to all tabs. Member A/B/C modules can expose the same `render(api_url, token)` interface; their existing files are preserved for their owners. Their deployment settings are `STUDENT_A_API_URL`, `STUDENT_B_API_URL` and `STUDENT_C_API_URL`.

The core dependency versions match the course environment. Starlette 1.3.1 is pinned because later response handling conflicts with Streamlit 1.59.0 image compression; four regression tests cover this behaviour. Run `python -m pytest tests -q` after installing pytest.

Generative AI assisted with the D module, integration code, tests and documentation. Each member remains responsible for their own contribution.
