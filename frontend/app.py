import streamlit as st
import requests
from datetime import datetime, timezone
import re

# --------------------------------------------------
# Config
# --------------------------------------------------
BACKEND_BASE = "https://anvalyx-backend.onrender.com"
JOBS_API = f"{BACKEND_BASE}/jobs"
RESUME_API = f"{BACKEND_BASE}/resume"
ATS_JOB_API = f"{BACKEND_BASE}/ats/score/job"

JOBS_PER_PAGE = 10

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Jobs + Resume + Real ATS Match")

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

def ats_badge(score):
    if score >= 75:
        return "🟢 Strong"
    elif score >= 50:
        return "🟡 Moderate"
    return "🔴 Weak"

# --------------------------------------------------
# Backend calls
# --------------------------------------------------
@st.cache_data(ttl=300)
def fetch_jobs():
    res = requests.get(JOBS_API, timeout=20)
    res.raise_for_status()
    return res.json()

def fetch_active_resume():
    try:
        res = requests.get(RESUME_API, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "resume_text" in data:
                return data["resume_text"]
    except:
        pass
    return None

def save_resume_to_backend(resume_text):
    payload = {"resume_text": resume_text}
    res = requests.post(RESUME_API, json=payload, timeout=15)
    res.raise_for_status()
    return res.json()

def fetch_ats_for_job(job_id):
    try:
        res = requests.get(f"{ATS_JOB_API}/{job_id}", timeout=15)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

# --------------------------------------------------
# Load resume once
# --------------------------------------------------
if "resume_text" not in st.session_state:
    st.session_state.resume_text = fetch_active_resume()

# --------------------------------------------------
# Sidebar: Resume Upload (NEW)
# --------------------------------------------------
st.sidebar.header("📄 Your Resume")

with st.sidebar:
    resume_input = st.text_area(
        "Paste your resume (saved until you change it)",
        height=200,
        value=st.session_state.resume_text or ""
    )

    if st.button("💾 Save Resume"):
        if not resume_input.strip():
            st.warning("Resume cannot be empty.")
        else:
            save_resume_to_backend(resume_input)
            st.session_state.resume_text = resume_input
            st.success("Resume saved successfully!")

    if st.session_state.resume_text:
        st.success("Active resume loaded")
    else:
        st.warning("No resume stored yet")

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

        if st.session_state.resume_text:
            if st.button("📊 Check ATS Match", key=f"ats_{section}_{job['id']}"):
                with st.spinner("Calculating ATS score..."):
                    result = fetch_ats_for_job(job["id"])

                if not result or "ats_score" not in result:
                    st.error("ATS score unavailable.")
                else:
                    score = result["ats_score"]
                    st.success(f"ATS Match: **{score}%** {ats_badge(score)}")

                    with st.expander("Why this score?"):
                        for k, v in result["breakdown"].items():
                            st.write(f"- {k.replace('_',' ').title()}: {v}%")

                        st.write("**Matched skills:**")
                        st.write(", ".join(result["matched_core_skills"]) or "None")

                        st.write("**Missing skills:**")
                        st.write(", ".join(result["missing_core_skills"]) or "None")

        st.divider()

    col1, col2, col3 = st.columns([1,2,1])

    with col1:
        if st.button("⬅️ Prev", key=f"prev_{section}_{page}", disabled=page == 1):
            st.session_state[page_key] -= 1
            st.rerun()

    with col3:
        if st.button("Next ➡️", key=f"next_{section}_{page}", disabled=page == pages):
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
    render_jobs([j for j in jobs if j["age"] <= 7], "fresh")

with older_tab:
    render_jobs([j for j in jobs if 8 <= j["age"] <= 30], "older")

# --------------------------------------------------
# MANUAL ATS TAB (UNCHANGED)
# --------------------------------------------------
with ats_tab:
    st.subheader("📄 ATS Match Checker")
    st.caption("Use this for jobs outside Anvalyx")

    resume_text = st.text_area("Resume text", height=200)
    jd_text = st.text_area("Job description", height=250)

    if st.button("🔍 Check ATS Score"):
        if not resume_text or not jd_text:
            st.warning("Please paste both resume and job description.")
        else:
            st.info("Manual ATS uses basic keyword logic. Job cards use real backend ATS.")
