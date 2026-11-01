from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest
from students import student_c_api as api, student_c_data as data
from students import student_c_summary as home

ROOT = Path(__file__).resolve().parents[1]


def fixture(token="BTC"):
    as_of = datetime.now(timezone.utc).date() - timedelta(days=1)
    return {"token":token,"prediction":"Uptrend","confidence":.5,"class_id":3,
            "probabilities":dict(zip(data.CLASSES,[.05,.1,.2,.5,.15])),
            "as_of_date":str(as_of),"prediction_date":str(as_of+timedelta(days=7)),
            "missing_features":[],"warnings":[]}


class HomeSummaryTests(unittest.TestCase):
    def setUp(self):
        home.summary.clear()
        self.addCleanup(home.summary.clear)

    def app(self):
        return AppTest.from_file(str(ROOT/'app/main.py'),default_timeout=15).run()

    def test_summary_reuses_data_and_caches_predictions_by_token(self):
        frame=pd.DataFrame({'date':[pd.Timestamp('2026-10-30')]})
        with patch.object(data,'cached_history',return_value=frame) as market,patch.object(api,'predict',return_value=fixture()) as predict:
            for _ in range(2):
                result,error=home.summary('BTC','https://c.test')
                self.assertIsNone(error)
            market.assert_called_once_with('BTC','Bitfinex')
            predict.assert_called_once_with('https://c.test','BTC',frame)
            home.summary('ETH','https://c.test')
            self.assertEqual(predict.call_count,2)
            home.summary('BTC','https://other.test')
            self.assertEqual(predict.call_count,3)

    def test_unavailable_states_are_cached(self):
        for exception in [data.MarketDataError('limited'),api.StudentCAPIError('offline')]:
            home.summary.clear()
            with patch.object(data,'cached_history') as market,patch.object(api,'predict') as predict:
                if isinstance(exception,data.MarketDataError):market.side_effect=exception
                else:predict.side_effect=exception
                for _ in range(2):
                    result,error=home.summary('BTC','https://c.test')
                    self.assertIsNone(result)
                    self.assertIn('unavailable',error)
                self.assertEqual(market.call_count,1)

    def test_compact_summary_navigation_and_shared_selector(self):
        def get(token,url):return fixture(token),None
        with patch.object(home,'summary',side_effect=get) as summary:
            app=self.app()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.metric),2)
            self.assertEqual(len(app.get('plotly_chart')),1)
            self.assertEqual(len(app.json),0)
            app.selectbox[0].set_value('ETH').run()
            self.assertEqual(summary.call_args.args[0],'ETH')
            self.assertIn('ETH',app.subheader[-1].value)
            app.button[0].click().run()
            self.assertEqual(app.radio[0].value,'Trend Category')
            self.assertIn('ETH',app.header[0].value)
            self.assertEqual(len(app.exception),0)

    def test_degraded_prediction_visible(self):
        for updates in [{'warnings':['peer unavailable']},{'missing_features':['DailyReturn']}]:
            with self.subTest(updates=updates),patch.object(home,'summary',return_value=({**fixture(),**updates},None)):
                app=self.app()
                self.assertEqual(len(app.exception),0)
                self.assertTrue(any('Degraded prediction' in warning.value for warning in app.warning))
                self.assertEqual(len(app.json),0)

    def test_unavailable_homepage_remains_usable(self):
        with patch.object(home,'summary',return_value=(None,'Service unavailable')):
            app=self.app()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.metric),0)
            self.assertEqual(len(app.get('plotly_chart')),0)
            self.assertTrue(any('unavailable' in info.value for info in app.info))
            app.button[0].click().run()
            self.assertEqual(app.radio[0].value,'Trend Category')
            self.assertEqual(len(app.exception),0)


if __name__=='__main__':unittest.main()
