
import os

import pandas as pd
import requests
import streamlit as st

DEFAULT_API_URL = "https://group23-studentb-mri.onrender.com"
API_URL = os.getenv("STUDENT_B_API_URL", DEFAULT_API_URL).rstrip("/")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_student_b_data(token):
    payload = {
        "token": token,
        "forecast_horizon": 7,
    }

    prediction_response = requests.post(
    f"{API_URL}/predict",
    json=payload,
    timeout=120,
    )
    prediction_response.raise_for_status()

    metadata_response = requests.get(
        f"{API_URL}/model-metadata",
        timeout=30,
    )
    metadata_response.raise_for_status()

    return prediction_response.json(), metadata_response.json()


def show_student_b(token):
    st.header("Market Risk Index (MRI)")
    st.caption("Student B | LightGBM Regression | Seven-day forecast")

    st.write(
        "The Market Risk Index estimates cryptocurrency market risk "
        "on a scale from 0 to 100. Higher values represent greater "
        "estimated market risk."
    )

    try:
        with st.spinner(f"Retrieving the latest {token} risk forecast..."):
            prediction, metadata = fetch_student_b_data(token)

        score = float(prediction["prediction"])
        score = max(0.0, min(100.0, score))

        if score < 33.33:
            risk_label = "Lower predicted risk"
        elif score < 66.67:
            risk_label = "Moderate predicted risk"
        else:
            risk_label = "Higher predicted risk"

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Predicted Market Risk Index",
                value=f"{score:.2f} / 100",
            )

        with col2:
            st.metric(
                label="Forecast Horizon",
                value=f"{prediction.get('forecast_horizon', 7)} days",
            )

        with col3:
            st.metric(
                label="Prediction Date",
                value=str(prediction.get("prediction_date", "N/A")),
            )

        st.subheader("Predicted Risk Score")
        st.progress(score / 100.0)
        st.write(f"**Risk interpretation:** {risk_label}")
        st.caption(
            "The risk categories are illustrative display bands, "
            "not separately validated classification outputs."
        )

        st.subheader("Model Feature Importance")
        importance = metadata.get("feature_importance", {})

        if importance:
            importance_df = pd.DataFrame(
                {
                    "Feature": list(importance.keys()),
                    "Importance": [
                        float(value) for value in importance.values()
                    ],
                }
            ).set_index("Feature")

            st.bar_chart(
                importance_df,
                horizontal=True,
                x_label="LightGBM feature importance",
            )
            st.caption(
                "Feature importance is reported by the trained LightGBM "
                "model. It does not establish causal influence."
            )
        else:
            st.info("Feature importance is currently unavailable.")

        st.subheader("Features Used for Prediction")

        features = prediction.get("features_used", {})
        if features:
            features_df = pd.DataFrame(
                [
                    {"Feature": name, "Value": value}
                    for name, value in features.items()
                ]
            )
            st.dataframe(
                features_df,
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("The API did not return individual feature values.")

        st.caption(
            f"Market data observation date: "
            f"{prediction.get('as_of', 'Not provided')}"
        )

        missing = prediction.get("missing_features", [])
        if missing:
            st.warning(
                "Some model features are unavailable: "
                + ", ".join(missing)
            )

        with st.expander("Model Details"):
            st.write("**Target:**", metadata.get("target", "MRI"))
            st.write(
                "**Algorithm:**",
                metadata.get("algorithm", "LightGBM"),
            )
            st.write(
                "**Model inputs:**",
                ", ".join(metadata.get("features", [])),
            )
            st.write(
                "**Supported tokens:**",
                ", ".join(metadata.get("supported_tokens", [])),
            )
            st.write(
                "**Optimised parameters:**",
                metadata.get("best_params", {}),
            )

        st.info(
            "This is a statistical risk forecast, not financial advice. "
            "Predictions may be affected by changing market conditions, "
            "differences between data providers and model uncertainty."
        )

    except requests.Timeout:
        st.warning(
            "The Market Risk API is taking too long to respond. "
            "Please retry shortly."
        )
    except requests.RequestException as exc:
        st.warning(
            "The Market Risk API is temporarily unavailable. "
            "The other dashboard tabs remain usable."
        )
        st.caption(f"Connection details: {exc}")
    except (ValueError, KeyError, TypeError) as exc:
        st.error("The Market Risk API returned an unexpected response.")
        st.caption(f"Response details: {exc}")
