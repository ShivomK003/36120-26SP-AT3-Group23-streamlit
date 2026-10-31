from datetime import date, datetime, timedelta, timezone
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import pandas as pd
import requests
from streamlit.testing.v1 import AppTest
from students import student_c_data as data
from students import student_c_api as api

ROOT = Path(__file__).resolve().parents[1]


def history():
    today = datetime.now(timezone.utc).date()
    return data.validate_history(pd.DataFrame([
        {"date":today-timedelta(days=35-i),"open":100.+i,"high":103.+i,
         "low":99.+i,"close":102.+i,"volume":1000.+i} for i in range(35)]))


def result():
    as_of=history().date.iloc[-1].date()
    return {"token":"BTC","forecast_horizon":7,"prediction":"Uptrend","class_id":3,
            "confidence":.5,"probabilities":dict(zip(data.CLASSES,[.05,.1,.2,.5,.15])),
            "as_of_date":str(as_of),"prediction_date":str(as_of+timedelta(days=7)),
            "warnings":[],"missing_features":[]}


class DataTests(unittest.TestCase):
    def test_sort_dedup_and_completed_day(self):
        frame=history()
        current=frame.tail(1).copy()
        current['date']=pd.Timestamp(datetime.now(timezone.utc).date())
        mixed=pd.concat([frame.iloc[::-1],frame.tail(1),current])
        actual=data.validate_history(mixed)
        pd.testing.assert_frame_equal(actual,frame)
        self.assertTrue(actual.date.is_monotonic_increasing)

    def test_conflicting_duplicates(self):
        frame=history();other=frame.tail(1).copy();other['volume']=0.
        with self.assertRaises(data.MarketDataError):
            data.validate_history(pd.concat([frame,other]))

    def test_invalid_and_incomplete_history(self):
        for field,value in [('open',0),('volume',-1),('close',float('nan')),('low',99999),('high',True),('date','bad')]:
            frame=history();frame[field]=frame[field].astype(object);frame.loc[0,field]=value
            with self.subTest(field=field),self.assertRaises(data.MarketDataError):
                data.validate_history(frame)
        with self.assertRaises(data.MarketDataError):data.validate_history(history().tail(20))

    def test_bitfinex_mappings_and_request(self):
        frame=history()
        body=[[int(row.date.timestamp()*1000),row.open,row.close,row.high,row.low,row.volume]
              for row in frame.itertuples()]
        for token in data.TOKENS:
            with self.subTest(token=token),patch.object(data.requests,'get') as get,patch.object(data.time,'sleep'):
                get.return_value.json.return_value=body[::-1]
                actual=data.fetch_history(token)
                self.assertEqual(len(actual),35)
                url=get.call_args.args[0]
                self.assertIn(data.BITFINEX_SYMBOLS[token],url)
                self.assertEqual(get.call_args.kwargs['params'],{'limit':250,'sort':-1})
                self.assertEqual(api.payload(token,actual)['token'],token)
        self.assertEqual(data.BITFINEX_SYMBOLS['DOGE'],'tDOGE:USD')

    def test_alpha_btc_only_and_key(self):
        with patch.object(data,'_get') as get:
            for token in [t for t in data.TOKENS if t!='BTC']:
                with self.assertRaises(data.MarketDataError):data.fetch_history(token,'Alpha Vantage','key')
            with self.assertRaises(data.MarketDataError):data.fetch_history('BTC','Alpha Vantage')
            get.assert_not_called()
            rows={str(row.date.date()):{f'{i}. {name}':str(getattr(row,name))
                  for i,name in enumerate(data.COLUMNS[1:],1)} for row in history().itertuples()}
            get.return_value={'Time Series (Digital Currency Daily)':rows}
            actual=data.fetch_history('BTC','Alpha Vantage','test-key')
            self.assertEqual(len(actual),35)
            self.assertEqual(get.call_args.args[1]['symbol'],'BTC')

    def test_provider_errors_and_rate_limit(self):
        for body in [[], {'error':'bad'}, [[1,2]]]:
            with self.subTest(body=body),patch.object(data,'_get',return_value=body):
                with self.assertRaises(data.MarketDataError):data.fetch_history('BTC')
        for body in [{'Note':'limit'}, {'Information':'quota'}, {}]:
            with patch.object(data,'_get',return_value=body):
                with self.assertRaises(data.MarketDataError):data.fetch_history('BTC','Alpha Vantage','key')
        with patch.object(data.requests,'get',side_effect=requests.Timeout),patch.object(data.time,'sleep'):
            with self.assertRaises(data.MarketDataError):data.fetch_history('BTC')

    def test_formula_and_thresholds(self):
        frame=data.indicators(history())
        close=frame.close
        self.assertAlmostEqual(frame.MA5.iloc[-1],close.tail(5).mean())
        self.assertAlmostEqual(frame.MA20.iloc[-1],close.tail(20).mean())
        expected=.7*(close.tail(5).mean()/close.tail(20).mean()-1)+.3*(close.iloc[-1]/close.iloc[-21]-1)
        self.assertAlmostEqual(frame.TrendScore.iloc[-1],expected)
        self.assertEqual(frame.regime.isna().sum(),20)
        for score,label in [(-.11,0),(-.10,1),(-.02,2),(.02,2),(.10,3),(.11,4)]:
            self.assertEqual(data.trend_label(score),data.CLASSES[label])


class APITests(unittest.TestCase):
    def test_payload_and_prediction(self):
        with patch.object(api.requests,'post') as post:
            post.return_value.json.return_value=result()
            actual=api.predict('https://c.test','BTC',history())
            body=post.call_args.kwargs['json']
            self.assertEqual(set(body),{'token','forecast_horizon','history'})
            self.assertEqual(len(body['history']),35)
            self.assertEqual(set(body['history'][0]),set(data.COLUMNS))
            self.assertEqual(body['forecast_horizon'],7)
            self.assertEqual(body['history'][-1]['date'],actual['as_of_date'])
            self.assertEqual(actual['confidence'],.5)

    def test_malformed_prediction_and_failure(self):
        for body in [None,[],{},dict(result(),class_id=0),dict(result(),confidence=float('nan')),
                     dict(result(),prediction_date='2000-01-01'),dict(result(),warnings='bad')]:
            with self.subTest(body=body),patch.object(api.requests,'post') as post:
                post.return_value.json.return_value=body
                with self.assertRaises(api.StudentCAPIError):api.predict('https://c.test','BTC',history())
        with patch.object(api.requests,'post',side_effect=requests.Timeout):
            with self.assertRaises(api.StudentCAPIError):api.predict('https://c.test','BTC',history())

    def test_genuine_metadata_only(self):
        api.metadata.clear()
        with patch.object(api.requests,'get') as get:
            get.return_value.json.return_value={'algorithm':'XGBoost Classifier','features':['Return20'],
                'feature_importance':{'Return20':1.},'class_names':data.CLASSES,'forecast_horizon':7}
            self.assertEqual(api.metadata('https://valid.test')['feature_importance'],{'Return20':1.})
            get.return_value.json.return_value={}
            with self.assertRaises(api.StudentCAPIError):api.metadata('https://bad.test')
        api.metadata.clear()


class UITests(unittest.TestCase):
    def setUp(self):
        # Isolate detailed-page checks from the live homepage summary.
        self.home_patch = patch('students.student_c_summary.render_home_summary')
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def app(self):
        return AppTest.from_file(str(ROOT/'app/main.py'),default_timeout=15).run()

    def test_navigation_all_tokens_and_no_automatic_requests(self):
        with patch.object(data.requests,'get',side_effect=AssertionError('no auto fetch')):
            app=self.app()
            self.assertEqual(len(app.exception),0)
            app.radio[0].set_value('Trend Category').run()
            for token in data.TOKENS:
                app.selectbox[0].set_value(token).run()
                self.assertEqual(len(app.exception),0)
                self.assertIn(token,app.header[0].value)
                self.assertEqual(app.selectbox[1].options,['Bitfinex','Alpha Vantage'] if token=='BTC' else ['Bitfinex'])
            app.radio[0].set_value('Overview').run()
            self.assertEqual(len(app.exception),0)

    def test_fetch_predict_and_metadata_smoke(self):
        with patch.object(data,'cached_history',return_value=history()),patch.object(api,'predict',return_value=result()),patch.object(api,'metadata') as meta:
            meta.return_value={'algorithm':'XGBoost Classifier','features':['Return20'],'feature_importance':{'Return20':1.},'class_names':data.CLASSES,'forecast_horizon':7}
            app=self.app();app.radio[0].set_value('Trend Category').run()
            app.button[0].click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.get('plotly_chart')),2)
            app.button[1].click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn('Uptrend',[metric.value for metric in app.metric])
            self.assertEqual(len(app.get('plotly_chart')),3)
            app.button[2].click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.get('plotly_chart')),4)

    def test_failures_do_not_crash_or_show_fake_predictions(self):
        with patch.object(data,'cached_history',side_effect=data.MarketDataError('Provider rate limit')):
            app=self.app();app.radio[0].set_value('Trend Category').run();app.button[0].click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.error),1)
            self.assertEqual(len(app.metric),0)
        with patch.object(data,'cached_history',return_value=history()),patch.object(api,'predict',side_effect=api.StudentCAPIError('Service unavailable')):
            app=self.app();app.radio[0].set_value('Trend Category').run();app.button[0].click().run();app.button[1].click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.error),1)
            self.assertEqual(len(app.metric),3)
            self.assertEqual(len(app.get('plotly_chart')),2)


if __name__=='__main__':unittest.main()
