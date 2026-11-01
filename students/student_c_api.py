"""Student C HTTP service adapter. No local model execution."""
from datetime import date, timedelta
import math
import os

import requests
import streamlit as st

from .student_c_data import CLASSES, COLUMNS

DEFAULT_URL = "https://three6120-26sp-at3-25977543-api.onrender.com"


class StudentCAPIError(ValueError):
    pass


def base_url():
    configured = os.getenv("STUDENT_C_API_URL") or os.getenv("STUDENT_C_BASE_URL")
    if configured:
        return configured.rstrip("/")
    try:
        return str(st.secrets.get("STUDENT_C_API_URL", DEFAULT_URL)).rstrip("/")
    except (FileNotFoundError, KeyError):
        return DEFAULT_URL


def payload(token, history):
    frame = history[COLUMNS].copy()
    frame["date"] = frame.date.map(lambda d: d.date().isoformat())
    return {"token": token, "forecast_horizon": 7, "history": frame.to_dict("records")}


def _probability(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0 <= value <= 1)


def predict(url, token, history):
    body = payload(token, history)
    try:
        response = requests.post(url.rstrip("/") + "/predict", json=body, timeout=45)
        response.raise_for_status()
        result = response.json()
        probabilities = result["probabilities"]
        if set(probabilities) != set(CLASSES) or not all(_probability(v) for v in probabilities.values()):
            raise ValueError("Invalid five-class probabilities")
        if abs(sum(probabilities.values()) - 1) > 1e-4:
            raise ValueError("Probabilities do not sum to one")
        index = result["class_id"]
        if type(index) is not int or index not in range(5) or result["prediction"] != CLASSES[index]:
            raise ValueError("Class encoding mismatch")
        if not _probability(result["confidence"]) or abs(result["confidence"]-probabilities[CLASSES[index]]) > 1e-5:
            raise ValueError("Confidence mismatch")
        as_of = date.fromisoformat(result["as_of_date"])
        forecast = date.fromisoformat(result["prediction_date"])
        if as_of.isoformat() != body["history"][-1]["date"] or forecast != as_of + timedelta(days=7):
            raise ValueError("Response dates differ from the submitted observations/horizon")
        if result.get("token", token) != token or result.get("forecast_horizon", 7) != 7:
            raise ValueError("Token/horizon mismatch")
        for name in ["missing_features", "warnings"]:
            if not isinstance(result[name], list) or not all(isinstance(x, str) for x in result[name]):
                raise ValueError("Invalid diagnostics")
        result["probabilities"] = {name: probabilities[name] for name in CLASSES}
        return result
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError, IndexError, OverflowError) as exc:
        raise StudentCAPIError("Student C prediction service is unavailable or returned an invalid response. Other pages remain available.") from exc


@st.cache_data(ttl=900, max_entries=4, show_spinner=False)
def metadata(url):
    try:
        response = requests.get(url.rstrip("/") + "/model-metadata", timeout=15)
        response.raise_for_status()
        result = response.json()
        values = result["feature_importance"]
        features = result["features"]
        if (not isinstance(values, dict) or not values or not isinstance(features, list)
                or set(values) != set(features) or not all(isinstance(k,str) for k in features)
                or not all(_probability(v) for v in values.values())
                or result["forecast_horizon"] != 7 or result["class_names"] != CLASSES
                or not isinstance(result["algorithm"], str)):
            raise ValueError("Invalid model metadata")
        return result
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise StudentCAPIError("Genuine model metadata is unavailable; feature importance is not displayed.") from exc
