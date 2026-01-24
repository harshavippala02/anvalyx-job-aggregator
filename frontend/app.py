import streamlit as st
import requests
from datetime import datetime, timezone

BACKEND_URL = "https://anvalyx-backend.onrender.com/jobs"
JOBS_PER_PAGE = 10

st.set_page_config(page_title="Anvalyx – Job Aggregator", layout="wide")

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Live jobs from backend (cloud-powered)")

# -----------------------------
# Helpers
# -----------------------------
def parse_date(date_str):
    return datetime.fromisoformat(date_str.replace("Z", "")).replace(tzinfo=timezone.utc)

def days_ago(posted_at):
    now = datetime.now(timezone.utc)
    diff = (now - posted_at).days
    if diff == 0:
        return "Today"
    elif diff == 1:
        return "1 day ago"
    return f"{diff} days ago"

@st.cache_data(ttl=300)
def fetch_jobs():
    res = requests.get(BACKEND_URL, timeout=20)
    res.raise_for_status()
    return res.json()

# -----------------------------
# Fetch & preprocess
# -----------------------------
jobs = fetch_jobs()

now = datetime.now(timezone.utc)

processed = []
for j in jobs:
    posted_at = parse_date(j["posted_at"])
    age = (now - posted_at).days

    # 🔴 HARD RULE: hide jobs older than 30 days
    if age > 30:
        continue

    j["posted_dt"] = posted_at
    j["age"] = age
    processed.append(j)

# Sort newest first
processed.sort(key=lambda x: x["posted_dt"], reverse=True)

# -----------------------------
# Tabs
# -----------------------------
fresh_tab, older_tab = st.tabs(["🟢 Fresh Jobs (≤7 days)", "🟡 Older Jobs (8–30 days)"])

def render_jobs(job_list):
    total_jobs = len(job_list)
    total_pages = max(1, (total_jobs + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE)

    if "page" not in st.session_state:
        st.session_state.page = 1

    start = (st.session_state.page - 1) * JOBS_PER_PAGE
    end = start + JOBS_PER_PAGE
    page_jobs = job_list[start:end]

    st.markdown(f"🔎 **Showing {total_jobs} jobs**")

    for job in page_jobs:
        st.markdown(f"### {job['title']}")
        st.markdown(f"**Company:** {job['company']}")
        st.markdown(f"**Location:** {job['location']}")
        st.markdown(f"**Source:** {job['source']}")
        st.markdown(f"**Posted:** {days_ago(job['posted_dt'])}")
        st.markdown(f"[Apply Here]({job['url']})")
        st.divider()

    # -----------------------------
    # Pagination controls
    # -----------------------------
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Prev", disabled=st.session_state.page == 1):
            st.session_state.page -= 1
            st.rerun()

    with col3:
        if st.button("Next ➡️", disabled=st.session_state.page == total_pages):
            st.session_state.page += 1
            st.rerun()

    with col2:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.page,
            step=1
        )
        if page != st.session_state.page:
            st.session_state.page = page
            st.rerun()

# -----------------------------
# Tab content
# -----------------------------
with fresh_tab:
    fresh_jobs = [j for j in processed if j["age"] <= 7]
    st.session_state.page = 1
    render_jobs(fresh_jobs)

with older_tab:
    older_jobs = [j for j in processed if 8 <= j["age"] <= 30]
    st.session_state.page = 1
    render_jobs(older_jobs)
