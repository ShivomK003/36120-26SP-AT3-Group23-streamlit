from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest


def response(request, data, status=200):
    return httpx.Response(status, json=data, request=request)


def test_pending_model_still_shows_volume_and_switches_token(monkeypatch):
    def request(method, url, **kwargs):
        req = httpx.Request(method,url)
        if url.endswith('/features'):
            return response(req, {'token':kwargs['json']['token'],'date':'2025-01-31','features':{'RelativeVolume':1.25,'SMA20Volume':2000000}})
        return response(req, {'status':'awaiting_trained_model'})
    monkeypatch.setattr(httpx,'request',request)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/apps/student_d_only.py')).run()
    assert not app.exception
    assert app.metric[0].value == '1.25×'
    assert app.info
    app.selectbox[0].select('XMR').run()
    assert not app.exception
    assert 'XMR' in app.markdown[0].value


def test_prediction_and_importance_render_without_local_model(monkeypatch):
    labels = ['Strong Sell','Sell','Hold','Buy','Strong Buy']
    def request(method,url,**kwargs):
        req = httpx.Request(method,url)
        if url.endswith('/features'): return response(req, {'date':'2025-01-31','features':{'RelativeVolume':1.25,'SMA20Volume':2000000}})
        if url.endswith('/model-metadata'): return response(req, {'status':'ready','feature_importance':{'Return20':.6,'RelativeVolume':.4},'classification_labels':labels})
        return response(req, {'prediction':'Buy','confidence':.7,'as_of_date':'2025-01-31','prediction_date':'2025-02-07','degraded':True,'class_probabilities':dict(zip(labels,[.02,.03,.15,.7,.1]))})
    monkeypatch.setattr(httpx,'request',request)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/apps/student_d_only.py')).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any(m.value == 'Buy' for m in app.metric)
    assert any(m.value == '70.0%' for m in app.metric)
    assert app.warning


def test_service_failure_is_contained(monkeypatch):
    def request(method,url,**kwargs):
        raise httpx.ConnectError('unavailable')
    monkeypatch.setattr(httpx,'request',request)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/apps/student_d_only.py')).run()
    assert not app.exception
    assert app.warning
    assert app.info
