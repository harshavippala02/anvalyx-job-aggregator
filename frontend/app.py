import streamlit as st
import requests
from datetime import datetime

# -------------------------------------------------
# Config
# -------------------------------------------------
BACKEND_URL = "https://anvalyx-backend.onrender.com"

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Live jobs from backend (cloud-powered)")

# -------------------------------------------------
# HARD RESET CACHE BUTTON (important for Cloud)
# -------------------------------------------------
if st.button("🔄 Refresh jobs (clear cache)"):
    st.cache_data.clear()
    st.rerun()

# -------------------------------------------------
# Fetch jobs safely
# -------------------------------------------------
@st.cache_data(ttl=300)
def fetch_jobs():
    try:
        resp = requests.get(f"{BACKEND_URL}/jobs", timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # Absolute safety checks
        if not isinstance(data, list):
            return []

        clean_jobs = []
        for item in data:
            if isinstance(item, dict):
                clean_jobs.append(item)

        return clean_jobs

    except Exception as e:
        st.error("Failed to fetch jobs from backend")
        st.text(str(e))
        return []

jobs = fetch_jobs()

# -------------------------------------------------
# UI
# -------------------------------------------------
st.markdown(f"🔎 **Showing {len(jobs)} jobs**")

if not jobs:
    st.warning("No jobs available yet.")
else:
    for job in jobs:
        # Final safety net
        title = job.get("title", "No title")
        company = job.get("company", "N/A")
        location = job.get("location", "N/A")
        source = job.get("source", "N/A")
        url = job.get("url")
        posted_at = job.get("posted_at")

        with st.container():
            st.subheader(title)
            st.write(f"**Company:** {company}")
            st.write(f"**Location:** {location}")
            st.write(f"**Source:** {source}")

            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at)
                    st.write(f"**Posted:** {dt.date()}")
                except:
                    pass

            if url:
                st.markdown(f"[Apply Here]({url})")

            st.divider()
