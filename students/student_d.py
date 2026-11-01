"""Trading Opportunity Rating page consuming the Student D HTTP service."""
from __future__ import annotations

import httpx
import pandas as pd
import streamlit as st


def fetch_json(api_url: str, endpoint: str, token: str | None = None) -> dict:
    method = 'POST' if endpoint in ('features', 'predict') else 'GET'
    payload = {'token': token, **({'forecast_horizon': 7} if endpoint == 'predict' else {})} if token else None
    response = httpx.request(method, f'{api_url.rstrip("/")}/{endpoint}', json=payload, timeout=25, follow_redirects=False)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError('Unexpected API response')
    return data


def volume_panel(api_url: str, token: str):
    try:
        data = fetch_json(api_url, 'features', token)
        values = data['features']
        left, right = st.columns(2)
        left.metric('Relative volume', f'{values["RelativeVolume"]:.2f}×')
        right.metric('20-day average turnover', f'${values["SMA20Volume"]:,.0f}')
        st.caption(f'Completed UTC day: {data["date"]}. Kraken USD spot turnover; ratio to its trailing 20-day mean.')
        st.bar_chart(pd.DataFrame({'Relative volume': [values['RelativeVolume']], '20-day reference': [1.]}, index=[token]), horizontal=True, stack=False, color=['#2266A3','#9AA4AF'], x_label='Cryptocurrency', y_label='Ratio to 20-day mean')
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        st.warning('The latest volume indicators are unavailable. Please try again shortly.')


def render(api_url: str, token: str):
    st.header('Trading Opportunity Rating')
    st.write(f'A seven-day trading outlook for {token}, with current volume context and model interpretation.')
    volume_panel(api_url, token)
    try:
        metadata = fetch_json(api_url, 'model-metadata')
    except (httpx.HTTPError, ValueError):
        st.info('The trading outlook is temporarily unavailable. Other pages can still be used.')
        return
    if metadata.get('status') != 'ready':
        st.info('The trading outlook is not available yet. Current volume indicators are shown above.')
        return
    if st.button('Generate seven-day outlook', key=f'tor_predict_{token}'):
        try:
            prediction = fetch_json(api_url, 'predict', token)
            left, right = st.columns(2)
            left.metric('Recommendation', prediction['prediction'])
            right.metric('Model confidence', f'{prediction["confidence"]:.1%}')
            st.caption(f'Based on {prediction["as_of_date"]}; outlook date {prediction["prediction_date"]}. Confidence is the model probability of the displayed class.')
            if prediction.get('degraded'):
                st.warning('Some indicators are unavailable. This outlook uses the remaining inputs and may be less reliable.')
            probabilities = prediction.get('class_probabilities', {})
            if probabilities:
                st.bar_chart(pd.DataFrame({'Probability': probabilities}).reindex(metadata['classification_labels']), x_label='TOR class', y_label='Probability', sort=False)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            st.warning('A trading outlook could not be generated. Please try again shortly.')
    importance = metadata.get('feature_importance')
    if importance:
        st.subheader('Feature importance')
        st.bar_chart(pd.DataFrame({'Importance': importance}).sort_values('Importance'), horizontal=True, x_label='Feature', y_label='Normalised model gain', sort=False)
    st.caption('Model outputs describe the assigned forecasting task and do not account for individual financial circumstances or trading costs.')
