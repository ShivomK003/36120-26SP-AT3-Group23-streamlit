
"""Test shared cryptocurrency selection and Student D navigation."""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest
from students import student_a, student_b, student_c, student_c_summary


APP_PATH = Path(__file__).resolve().parents[1] / "app/main.py"


@pytest.fixture(autouse=True)
def isolate_peer_pages(monkeypatch):
    monkeypatch.setattr(student_a, "render_api_home_card", lambda token: None)
    monkeypatch.setattr(student_a, "render_api_tab", lambda token: None)
    monkeypatch.setattr(student_b, "show_student_b", lambda token: None)
    monkeypatch.setattr(student_c, "show_student_c", lambda token: None)
    monkeypatch.setattr(student_c_summary, "render_home_summary", lambda token: None)


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

    assert tokens == ["BTC"]
    assert any(metric.value == "1.25×" for metric in app.metric)

    # Navigate to Student D's dedicated page.
    tokens.clear()
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


def test_overview_d_failure_does_not_block_other_pages(monkeypatch):
    calls = []

    def unavailable(method, url, **kwargs):
        calls.append(url)
        raise httpx.ConnectError("volume service unavailable")

    monkeypatch.setenv("STUDENT_D_API_URL", "https://student-d.example")
    monkeypatch.setattr(httpx, "request", unavailable)
    app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    assert app.warning
    assert calls == ["https://student-d.example/features"]

    app.radio[0].set_value("Market Risk Index").run()
    assert not app.exception
    assert len(calls) == 1
