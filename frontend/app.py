import streamlit as st
import requests
from datetime import datetime, timezone

BACKEND_URL = "https://anvalyx-backend.onrender.com/jobs"
JOBS_PER_PAGE = 10

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Live jobs from cloud backend (Adzuna + USAJobs)")

# -------------------------------------------------
# Helpers
# -------------------------------------------------
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

# -------------------------------------------------
# Fetch & preprocess jobs
# -------------------------------------------------
raw_jobs = fetch_jobs()
now = datetime.now(timezone.utc)

jobs = []
for j in raw_jobs:
    posted_dt = parse_date(j["posted_at"])
    age = (now - posted_dt).days

    # ❌ Hide jobs older than 30 days
    if age > 30:
        continue

    j["posted_dt"] = posted_dt
    j["age"] = age
    jobs.append(j)

# Newest first
jobs.sort(key=lambda x: x["posted_dt"], reverse=True)

# -------------------------------------------------
# Pagination renderer
# -------------------------------------------------
def render_jobs(job_list, section_name):
    total_jobs = len(job_list)
    total_pages = max(1, (total_jobs + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE)

    page_key = f"page_{section_name}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    page = st.session_state[page_key]
    start = (page - 1) * JOBS_PER_PAGE
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

    # ---------------- Pagination Controls ----------------
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button(
            "⬅️ Prev",
            key=f"prev_{section_name}_{page}",
            disabled=page == 1
        ):
            st.session_state[page_key] -= 1
            st.rerun()

    with col3:
        if st.button(
            "Next ➡️",
            key=f"next_{section_name}_{page}",
            disabled=page == total_pages
        ):
            st.session_state[page_key] += 1
            st.rerun()

    with col2:
        new_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=page,
            step=1,
            key=f"page_input_{section_name}"
        )
        if new_page != page:
            st.session_state[page_key] = new_page
            st.rerun()

# -------------------------------------------------
# Tabs
# -------------------------------------------------
fresh_tab, older_tab = st.tabs([
    "🟢 Fresh Jobs (≤7 days)",
    "🟡 Older Jobs (8–30 days)"
])

with fresh_tab:
    fresh_jobs = [j for j in jobs if j["age"] <= 7]
    render_jobs(fresh_jobs, "fresh")

with older_tab:
    older_jobs = [j for j in jobs if 8 <= j["age"] <= 30]
    render_jobs(older_jobs, "older")
