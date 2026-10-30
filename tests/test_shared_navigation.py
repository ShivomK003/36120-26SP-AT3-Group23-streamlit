from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest


def test_shared_currency_reaches_d_overview_and_tab(monkeypatch):
    tokens = []
    def request(method, url, **kwargs):
        req = httpx.Request(method, url)
        if url.endswith('/features'):
            tokens.append(kwargs['json']['token'])
            return httpx.Response(200, request=req, json={'date': '2026-10-29', 'features': {'RelativeVolume': 1.25, 'SMA20Volume': 2000000}})
        return httpx.Response(200, request=req, json={'status': 'awaiting_trained_model'})
    monkeypatch.setenv('STUDENT_D_API_URL', 'https://student-d.example')
    monkeypatch.setattr(httpx, 'request', request)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app/main.py')).run()
    assert not app.exception
    assert len(app.tabs) == 5
    assert tokens == ['BTC', 'BTC']
    tokens.clear()
    app.selectbox[0].select('XMR').run()
    assert not app.exception
    assert tokens == ['XMR', 'XMR']
