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


## Student C — Trend Category frontend

Branch: `student-c-trend-classification`, created from verified latest `main`.
Only Student C modules and minimal selector/navigation registration were added;
Student A/B/D page files are unchanged. No teammate branch was merged or copied.

### Run

Use Python 3.12 and uv:

```sh
uv sync --locked
uv run streamlit run app/main.py
```

Open http://localhost:8501, select a cryptocurrency, then select **Trend Category**.
Choose a provider, click **Fetch latest market data**, then **Predict seven-day
trend**. The detailed page makes requests only through its action buttons. The homepage
summary automatically loads the selected token through the caches described below.
The displayed observations are the exact ones sent to Student C's HTTP API.
There is no local model inference, trained model file, or synthetic-data fallback.

### Data and credentials

- Bitfinex is the default for all eight tokens. It uses the experiments
  `dataset.py` candle schema and UTC completion rules, with descending retrieval
  of the latest 250 candles rather than the oldest historical page. The verified
  four-letter DOGE symbol is `tDOGE:USD`; other symbols are `t{TOKEN}USD`.
- Alpha Vantage is optional **only for BTC**, using DIGITAL_CURRENCY_DAILY and
  USD. Set `ALPHA_VANTAGE_API_KEY` in the environment or Streamlit secrets.
- Reference discrepancy: the inspected experiments branch
  `experiments/student-c-trend-classification` assigns DOGE to Alpha Vantage.
  This frontend follows the latest task's stricter BTC-only Alpha policy and
  does not alter the experiments code. Provider/volume differences can affect
  predictions; training used pooled data from the reference providers.
- Live observations are cached for 15 minutes with at most 16 token/provider
  entries. Uncached requests are spaced by at least two seconds per process.
  Provider quotas still apply. A fetch within the cache interval reuses its
  snapshot. Rate limits, missing credentials and malformed/short histories show
  clear errors; no data is fabricated. Exact duplicate candles are removed,
  conflicting same-date records are rejected, and at least 21 completed daily
  observations are required.
- Dates are sorted and normalized to timezone-naive UTC midnight. The current
  UTC day's partial candle is excluded. Gaps are retained; rolling windows count
  observations. The last actual provider date and its age are displayed, and
  stale data is flagged rather than described as current.

### Prediction, analysis and diagnostics

`students/student_c_api.py` calls POST `/predict` with token, horizon 7 and history.
Default URL: `https://three6120-26sp-at3-25977543-api.onrender.com`.
Override with `STUDENT_C_API_URL` (or `STUDENT_C_BASE_URL`); Streamlit secrets also
support `STUDENT_C_API_URL`. Secrets files and `.env` are ignored by Git; `.env`
is not loaded automatically. Never put credentials in source or URLs.

The adapter validates all five probabilities, class IDs, confidence, response
observation/forecast dates and diagnostics. Timeouts are 45 seconds. Failures
leave historical charts available and never produce a pretend prediction.
Missing-feature diagnostics and upstream warnings remain visible. The forecast
region ends exactly seven calendar days after the last observation, with no
future price values or moving averages drawn.

Historical regimes are calculated independently from the observed closes:
`TrendScore = 0.7*(MA5/MA20 - 1) + 0.3*Return20`.
MA windows include the current observation; Return20 compares close with its
20-observation-prior close. Class thresholds are `< -0.10`, `< -0.02`, `<= 0.02`,
`<= 0.10`, `> 0.10` in order. Warm-up rows have no label. These historical labels
are explicitly distinct from future XGBoost predictions.

Global importance is hidden until genuine `/model-metadata` data is retrieved
using **Load model metadata**. The page never substitutes illustrative values.
The metadata cache lasts 15 minutes. Global importance is not a local explanation.

### Checks and integration notes

```sh
uv run python -m unittest discover -s tests -v
```

Tests mock provider and prediction HTTP calls and cover OHLCV validation,
provider mappings, BTC-only credentials policy, API payload/response validation,
indicator thresholds, all eight selector options, navigation and Streamlit
fetch/predict/error/metadata rendering. No credentials are required by tests.

`show_student_c(token)` is the simple shared entry point. `render(api_url, token)`
is also available for an environment-configured group router. Future merges
should preserve one shared token selector and register this function in the
Trend Category tab/page. `app/main.py` is the likely shared merge-conflict point;
Student C's data/client modules should merge independently. Student A/B/D page
files, Dockerfile and requirements are not changed by this contribution.

No commits, pushes or deployments are made by this task. Original prototype
branch cleanup is performed only after checking it has no unique commits or
uncommitted work; no remote branch is deleted.

### Verified on 30 October 2026

- All 13 automated test methods passed, including all-token and Streamlit smoke
  subcases. The initial `main` scaffold had no existing tracked tests.
- Live Bitfinex retrieval succeeded for all eight tokens: 249 completed candles
  per token, with last observation 2026-10-29. No static/synthetic input was used.
- The initial live prediction attempt failed; a warm-service retry succeeded
  with as-of date 2026-10-29 and forecast date 2026-11-05. The deployed API reported
  missing DailyReturn, Return20, DistanceMA5, DistanceMA20 and MACrossover, plus
  Student A/B upstream warnings. Those diagnostics are surfaced in the UI; no
  backend change is attempted by this frontend contribution.
- Genuine model metadata loaded successfully with 11 features. BTC Alpha Vantage
  live fetching remains unverified without credentials; the authenticated adapter
  and BTC-only restriction passed mocked tests.
- The local prototype branch had zero unique commits and was deleted safely.
  The remote prototype branch remains. Main and teammate page files are unchanged.

The `.python-version` file selects Python 3.12 for uv. Visual browser inspection
was not available through the browser access host; AppTest verifies the rendered
widgets/charts and interactions, not final pixel-level responsiveness. Group
review should include the chart layout at desktop and narrow viewport sizes.


### Student C homepage summary

The Overview contains a compact Student C section using the shared cryptocurrency
selector. `students/student_c_summary.py` reuses `cached_history` (real Bitfinex
OHLCV, 15-minute cache) and the existing validated `predict` HTTP client. Prediction
results and unavailable states are cached for five minutes per token/service URL,
so reruns do not repeatedly wake Render or retry an unavailable service.

The section shows the actual seven-day class, confidence, forecast/observation
dates and all five probabilities. Degraded inputs receive a visible warning;
unavailable data/services produce a small informative state. There are no JSON
diagnostics or mock values on the homepage. **Open Student C trend analysis**
navigates to the detailed page while retaining the shared token. That page's
implementation and design are unchanged.

Homepage checks plus existing Student C checks: **18 test methods passed**.
They cover cache reuse, token/URL cache isolation, cached failures, compact
rendering, degraded warnings and navigation. HTTP calls are mocked in these
checks; no new live endpoint availability claim is made by this summary update.
## Student D integration

D preview: https://group23-crypto-preview.streamlit.app . It runs `frontend-student-d-tor` from the private fork `RainyxWang/36120-26SP-AT3-Group23-streamlit-preview`, because Streamlit Community Cloud requires repository administrator access. The upstream PR remains the group review path. This preview supplies D and shared navigation; A/B/C pages are still being developed by their owners.

D API: https://group23-studentd-tor.onrender.com . Root, health, model metadata and all eight feature/prediction pairs passed live checks on 30 October 2026.

Yuxiang Wang (25509050) provides `students/student_d.py`. On `integration/student-a-b-c-d`, the Overview calls `volume_panel(api_url, token)` and the dedicated Trading Opportunity Rating page calls `render(api_url, token)`. The shared cryptocurrency selection reaches both views. Both use HTTP only. `STUDENT_D_API_URL` defaults to the verified D Render base URL above and can be set in the deployment environment. The page contains failures and labels forecasts with missing peer indicators.

The integrated entry point shares one currency selection across A's `render_api_tab(token)`, B's `show_student_b(token)`, C's `show_student_c(token)` and D's `render(api_url, token)`. The Overview uses each available homepage component. Service settings remain in the individual member modules and deployment environment.

The core dependency versions match the course environment. Starlette 1.3.1 is pinned because later response handling conflicts with Streamlit 1.59.0 image compression; four regression tests cover this behaviour. Run `python -m pytest tests -q` after installing pytest.

Generative AI assisted with the D module, integration code, tests and documentation. Each member remains responsible for their own contribution.
