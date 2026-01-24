import streamlit as st
import requests

BACKEND_URL = "https://anvalyx-backend.onrender.com/jobs"

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Live jobs from multiple sources (backend-powered)")

@st.cache_data(ttl=300)
def fetch_jobs():
    response = requests.get(BACKEND_URL, timeout=30)
    response.raise_for_status()
    return response.json()

try:
    jobs = fetch_jobs()
except Exception as e:
    st.error("Failed to fetch jobs from backend")
    st.stop()

st.subheader(f"🔎 Showing {len(jobs)} jobs")

for job in jobs:
    with st.container(border=True):
        st.markdown(f"### {job['title']}")
        st.write(f"**Company:** {job['company']}")
        st.write(f"**Location:** {job['location']}")
        st.markdown(f"[Apply here]({job['url']})")
