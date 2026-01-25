import streamlit as st
import requests
from datetime import datetime, timezone

# --------------------------------------------------
# Config
# --------------------------------------------------
BACKEND_BASE = "https://anvalyx-backend.onrender.com"

JOBS_API = f"{BACKEND_BASE}/jobs"
RESUME_API = f"{BACKEND_BASE}/resume"
ATS_JOB_API = f"{BACKEND_BASE}/ats/score/job"
ATS_MANUAL_API = f"{BACKEND_BASE}/ats/score"

JOBS_PER_PAGE = 10

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Jobs + AI ATS Match Checker")

# --------------------------------------------------
# Helpers
# --------------------------------------------------
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
    res = requests.get(JOBS_API, timeout=20)
    res.raise_for_status()
    return res.json()

@st.cache_data(ttl=300)
def fetch_active_resume():
    res = requests.get(RESUME_API, timeout=10)
    if res.status_code == 200:
        data = res.json()
        if "resume_text" in data:
            return data["resume_text"]
    return None

# --------------------------------------------------
# Load resume once
# --------------------------------------------------
if "resume_text" not in st.session_state:
    st.session_state.resume_text = fetch_active_resume()

# Sidebar resume status
st.sidebar.header("📄 Resume Status")
if st.session_state.resume_text:
    st.sidebar.success("Resume loaded from backend")
else:
    st.sidebar.warning("No resume stored yet")

# --------------------------------------------------
# Fetch & preprocess jobs
# --------------------------------------------------
raw_jobs = fetch_jobs()
now = datetime.now(timezone.utc)

jobs = []
for j in raw_jobs:
    posted_dt = parse_date(j["posted_at"])
    age = (now - posted_dt).days
    if age > 30:
        continue

    j["posted_dt"] = posted_dt
    j["age"] = age
    jobs.append(j)

jobs.sort(key=lambda x: x["posted_dt"], reverse=True)

# --------------------------------------------------
# Pagination renderer
# --------------------------------------------------
def render_jobs(job_list, section):
    total = len(job_list)
    pages = max(1, (total + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE)

    page_key = f"page_{section}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    page = st.session_state[page_key]
    start = (page - 1) * JOBS_PER_PAGE
    end = start + JOBS_PER_PAGE

    st.markdown(f"🔎 **Showing {total} jobs**")

    for job in job_list[start:end]:
        st.markdown(f"### {job['title']}")
        st.markdown(f"**Company:** {job['company']}")
        st.markdown(f"**Location:** {job['location']}")
        st.markdown(f"**Source:** {job['source']}")
        st.markdown(f"**Posted:** {days_ago(job['posted_dt'])}")
        st.markdown(f"[Apply Here]({job['url']})")

        # -----------------------------
        # AI ATS score per job
        # -----------------------------
        if st.session_state.resume_text:
            if st.button(
                "📊 Check AI ATS Score",
                key=f"ats_{section}_{job['id']}"
            ):
                with st.spinner("Calculating ATS score..."):
                    res = requests.get(
                        f"{ATS_JOB_API}/{job['id']}",
                        timeout=20
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.success(f"🎯 ATS Match Score: {data['score']}%")
                        st.caption(data["explanation"])
                    else:
                        st.error("Failed to calculate ATS score")

        st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button(
            "⬅️ Prev",
            key=f"prev_{section}_{page}",
            disabled=page == 1
        ):
            st.session_state[page_key] -= 1
            st.rerun()

    with col3:
        if st.button(
            "Next ➡️",
            key=f"next_{section}_{page}",
            disabled=page == pages
        ):
            st.session_state[page_key] += 1
            st.rerun()

    with col2:
        new_page = st.number_input(
            "Page",
            min_value=1,
            max_value=pages,
            value=page,
            step=1,
            key=f"page_input_{section}"
        )
        if new_page != page:
            st.session_state[page_key] = new_page
            st.rerun()

# --------------------------------------------------
# Tabs
# --------------------------------------------------
fresh_tab, older_tab, ats_tab = st.tabs([
    "🟢 Fresh Jobs (≤7 days)",
    "🟡 Older Jobs (8–30 days)",
    "📄 ATS Checker (External Jobs)"
])

with fresh_tab:
    fresh = [j for j in jobs if j["age"] <= 7]
    render_jobs(fresh, "fresh")

with older_tab:
    older = [j for j in jobs if 8 <= j["age"] <= 30]
    render_jobs(older, "older")

# --------------------------------------------------
# MANUAL ATS TAB (AI-BASED)
# --------------------------------------------------
with ats_tab:
    st.subheader("📄 AI ATS Match Checker")
    st.caption("Use this for jobs outside Anvalyx")

    jd_text = st.text_area(
        "🧾 Paste the Job Description",
        height=300,
        placeholder="Paste full job description here..."
    )

    if st.button("🔍 Check AI ATS Score"):
        if not jd_text:
            st.warning("Please paste a job description.")
        else:
            with st.spinner("Calculating ATS score..."):
                res = requests.post(
                    ATS_MANUAL_API,
                    json={"job_description": jd_text},
                    timeout=30
                )

                if res.status_code == 200:
                    data = res.json()
                    st.success(f"🎯 ATS Match Score: {data['score']}%")
                    st.caption(data["explanation"])
                else:
                    st.error("Failed to calculate ATS score")
