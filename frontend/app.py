import streamlit as st
import requests
import os
from datetime import datetime, timezone

# ---------------- CONFIG ----------------
BACKEND_BASE = os.getenv(
    "BACKEND_BASE",
    "https://anvalyx-backend.onrender.com"
)

st.set_page_config(
    page_title="Anvalyx – Job Aggregator",
    layout="wide"
)

# ---------------- HEADER ----------------
st.title("💼 Anvalyx – Job Aggregator")
st.caption("Jobs + AI ATS Match Checker")

# ---------------- HELPERS ----------------
def fetch_jobs():
    try:
        res = requests.get(f"{BACKEND_BASE}/jobs", timeout=20)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def days_ago(date_str):
    try:
        posted = datetime.fromisoformat(date_str.replace("Z", "")).replace(tzinfo=timezone.utc)
        diff = (datetime.now(timezone.utc) - posted).days
        if diff == 0:
            return "Today"
        if diff == 1:
            return "1 day ago"
        return f"{diff} days ago"
    except:
        return "Unknown"

def render_jobs(job_list, section):
    if not job_list:
        st.info("No jobs found")
        return

    for job in job_list:
        st.markdown(f"## {job['title']}")
        st.write(f"**Company:** {job['company']}")
        st.write(f"**Location:** {job['location']}")
        st.write(f"**Source:** {job['source']}")
        st.write(f"**Posted:** {days_ago(job['posted_at'])}")

        st.markdown(f"[Apply Here]({job['url']})")

        # ---------- ATS BUTTON ----------
        if st.button(
            "📊 Check AI ATS Score",
            key=f"ats_{section}_{job['id']}"
        ):
            with st.spinner("Calculating ATS score..."):
                res = requests.get(
                    f"{BACKEND_BASE}/ats/score/job/{job['id']}",
                    timeout=30
                )

                if res.status_code == 200:
                    data = res.json()

                    st.success(f"🎯 ATS Match Score: {data['score']}%")

                    if data.get("strengths"):
                        st.markdown("### ✅ Strengths")
                        st.write(", ".join(data["strengths"]))

                    if data.get("gaps"):
                        st.markdown("### ❌ Skill Gaps")
                        st.write(", ".join(data["gaps"]))

                    if data.get("explanation"):
                        st.caption(data["explanation"])

                else:
                    st.error("Failed to calculate ATS score")

        st.divider()

# ---------------- LOAD JOBS ----------------
all_jobs = fetch_jobs()
now = datetime.now(timezone.utc)

fresh_jobs = []
older_jobs = []

for j in all_jobs:
    posted = datetime.fromisoformat(j["posted_at"].replace("Z", "")).replace(tzinfo=timezone.utc)
    age = (now - posted).days
    if age <= 7:
        fresh_jobs.append(j)
    elif 8 <= age <= 30:
        older_jobs.append(j)

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs([
    "🟢 Fresh Jobs (≤7 days)",
    "🟡 Older Jobs (8–30 days)",
    "📄 ATS Checker (External Jobs)"
])

# ---------------- FRESH JOBS ----------------
with tab1:
    st.caption(f"Showing {len(fresh_jobs)} jobs")
    render_jobs(fresh_jobs, "fresh")

# ---------------- OLDER JOBS ----------------
with tab2:
    st.caption(f"Showing {len(older_jobs)} jobs")
    render_jobs(older_jobs, "older")

# ---------------- MANUAL ATS ----------------
with tab3:
    st.subheader("📄 AI ATS Checker (Manual Job Description)")

    job_text = st.text_area("Paste Job Description", height=200)
    resume_text = st.text_area("Paste Resume Text", height=200)

    if st.button("Run AI ATS Check"):
        if not job_text or not resume_text:
            st.warning("Please paste both job description and resume")
        else:
            with st.spinner("Calculating ATS score..."):
                res = requests.post(
                    f"{BACKEND_BASE}/ats/score",
                    json={
                        "job_description": job_text
                    },
                    timeout=30
                )

                if res.status_code == 200:
                    data = res.json()

                    st.success(f"🎯 ATS Match Score: {data['score']}%")

                    if data.get("strengths"):
                        st.markdown("### ✅ Strengths")
                        st.write(", ".join(data["strengths"]))

                    if data.get("gaps"):
                        st.markdown("### ❌ Skill Gaps")
                        st.write(", ".join(data["gaps"]))

                    if data.get("explanation"):
                        st.caption(data["explanation"])

                else:
                    st.error("Failed to calculate ATS score")
