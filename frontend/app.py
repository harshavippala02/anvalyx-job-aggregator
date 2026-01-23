import streamlit as st
import requests
import pandas as pd

API_URL = "https://anvalyx.onrender.com/jobs"

st.set_page_config(page_title="Anvalyx Jobs", layout="wide")

st.title("🔍 Anvalyx – Job Aggregator")
st.caption("Live jobs fetched from Anvalyx backend")

@st.cache_data(ttl=300)
def fetch_jobs():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    return response.json()

try:
    jobs = fetch_jobs()

    if not jobs:
        st.warning("No jobs found.")
    else:
        df = pd.DataFrame(jobs)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error("Failed to load jobs")
    st.code(str(e))
