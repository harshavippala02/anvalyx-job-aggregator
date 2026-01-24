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

JOBS_PER_PAGE = 10

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

st.title("💼 Anvalyx – Job Aggregator")
st.caption("Jobs + ATS Match Checker")

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

def extract_keywords(text):
    text = text.lower()
    words = re.findall(r"[a-zA-Z]{3,}", text)

    stopwords = {
        "and","the","with","for","this","that","from","your","you",
        "will","have","are","our","job","role","work","years","experience",
        "ability","skills","responsibilities","requirements"
    }

    return set(w for w in words if w not in stopwords)

def calculate_ats(resume_text, jd_text):
    resume_kw = extract_keywords(resume_text)
    jd_kw = extract_keywords(jd_text)

    matched = resume_kw & jd_kw
    missing = jd_kw - resume_kw

    score = int((len(matched) / max(len(jd_kw), 1)) * 100)

    return score, matched, missing

# --------------------------------------------------
# Backend calls
# --------------------------------------------------
@st.cache_data(ttl=300)
def fetch_jobs():
    res = requests.get(JOBS_API, timeout=20)
    res.raise_for_status()
    return res.json()

@st.cache_data(ttl=300)
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

        # ATS quick check (if resume exists)
        if st.session_state.resume_text:
            if st.button(
                "📊 Check ATS Score",
                key=f"ats_{section}_{job['title']}_{start}"
            ):
                score, matched, missing = calculate_ats(
                    st.session_state.resume_text,
                    job["title"] + " " + job["company"] + " " + job["location"]
                )

                st.info(f"ATS Match Score: {score}%")
                st.write("✅ Matched keywords:", ", ".join(sorted(matched)))
                st.write("❌ Missing keywords:", ", ".join(sorted(list(missing))[:20]))

        st.divider()

    col1, col2, col3 = st.columns([1,2,1])

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
    "📄 ATS Checker"
])

with fresh_tab:
    fresh = [j for j in jobs if j["age"] <= 7]
    render_jobs(fresh, "fresh")

with older_tab:
    older = [j for j in jobs if 8 <= j["age"] <= 30]
    render_jobs(older, "older")

# --------------------------------------------------
# MANUAL ATS TAB (KEPT – NOT REMOVED)
# --------------------------------------------------
with ats_tab:
    st.subheader("📄 ATS Match Checker")
    st.caption("Use this for jobs outside Anvalyx")

    resume_text = st.text_area(
        "📎 Resume text",
        height=200,
        value=st.session_state.resume_text or "",
        placeholder="Paste resume here..."
    )

    jd_text = st.text_area(
        "🧾 Job description",
        height=250,
        placeholder="Paste job description here..."
    )

    if st.button("🔍 Check ATS Score"):
        if not resume_text or not jd_text:
            st.warning("Please paste both resume and job description.")
        else:
            score, matched, missing = calculate_ats(resume_text, jd_text)

            st.markdown(f"## 🎯 ATS Match Score: **{score}%**")

            st.markdown("### ✅ Strong Matches")
            st.write(", ".join(sorted(matched)) if matched else "None")

            st.markdown("### ❌ Missing / Weak")
            st.write(", ".join(sorted(list(missing))[:30]) if missing else "None")
