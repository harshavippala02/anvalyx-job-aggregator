import streamlit as st
import requests

st.set_page_config(page_title="Anvalyx – Job Aggregator", layout="wide")

BACKEND_URL = "https://anvalyx-backend.onrender.com/jobs"

@st.cache_data(ttl=60)
def fetch_jobs():
    response = requests.get(
        BACKEND_URL,
        timeout=30  # ⬅️ very important for Render
    )
    response.raise_for_status()
    return response.json()

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Live jobs from multiple sources (backend-powered)")

try:
    jobs = fetch_jobs()
except Exception as e:
    st.error("Failed to fetch jobs from backend")
    st.code(str(e))
    st.stop()

st.subheader(f"🔎 Showing {len(jobs)} jobs")

for job in jobs:
    with st.container(border=True):
        st.markdown(f"### {job['title']}")
        st.write(f"**Company:** {job['company']}")
        st.write(f"**Location:** {job['location']}")
        st.markdown(f"[Apply here]({job['url']})")
