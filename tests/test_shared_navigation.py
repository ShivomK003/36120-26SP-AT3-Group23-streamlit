
"""Test shared cryptocurrency selection and Student D navigation."""

from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app/main.py"


def test_shared_currency_reaches_student_d(monkeypatch):
    tokens = []

    def request(method, url, **kwargs):
        req = httpx.Request(method, url)

        if url.endswith("/features"):
            tokens.append(kwargs["json"]["token"])
            return httpx.Response(
                200,
                request=req,
                json={
                    "date": "2026-10-29",
                    "features": {
                        "RelativeVolume": 1.25,
                        "SMA20Volume": 2000000,
                    },
                },
            )

        return httpx.Response(
            200,
            request=req,
            json={"status": "awaiting_trained_model"},
        )

    monkeypatch.setenv(
        "STUDENT_D_API_URL",
        "https://student-d.example",
    )
    monkeypatch.setattr(httpx, "request", request)

    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    assert app.radio[0].value == "Overview"

    # Student D must not make requests on initial Overview load.
    assert tokens == []

    # Navigate to Student D's dedicated page.
    app.radio[0].set_value("Trading Opportunity Rating").run()

    assert not app.exception
    assert tokens == ["BTC"]

    # Changing the shared token must update Student D's API request.
    tokens.clear()
    app.selectbox[0].select("XMR").run()

    assert not app.exception
    assert tokens == ["XMR"]

    # Leaving Student D must stop its page-specific requests.
    tokens.clear()
    app.radio[0].set_value("Market Risk Index").run()

    assert not app.exception
    assert tokens == []
