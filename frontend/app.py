import streamlit as st
import requests
import os
from datetime import datetime

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
def fetch_jobs(endpoint: str):
    try:
        res = requests.get(f"{BACKEND_BASE}{endpoint}", timeout=20)
        if res.status_code == 200:
            return res.json()
        else:
            st.warning(f"Backend returned {res.status_code}")
    except Exception as e:
        st.error("Backend not reachable")
    return []

def format_posted(job: dict) -> str:
    """
    Safely extract posted date from backend
    """
    raw = job.get("posted_at") or job.get("posted")
    if not raw:
        return "Unknown"

    try:
        return datetime.fromisoformat(raw.replace("Z", "")).date().isoformat()
    except Exception:
        return raw

def render_jobs(job_list, section):
    if not job_list:
        st.info("No jobs found")
        return

    for job in job_list:
        title = job.get("title", "N/A")
        company = job.get("company", "N/A")
        location = job.get("location", "N/A")
        source = job.get("source", "N/A")
        posted = format_posted(job)
        apply_url = job.get("apply_url") or job.get("url")
        job_id = job.get("id")

        st.markdown(f"## {title}")
        st.write(f"**Company:** {company}")
        st.write(f"**Location:** {location}")
        st.write(f"**Source:** {source}")
        st.write(f"**Posted:** {posted}")

        if apply_url:
            st.markdown(f"[Apply Here]({apply_url})")

        # ---------- ATS BUTTON ----------
        if job_id and st.button(
            "📊 Check AI ATS Score",
            key=f"ats_{section}_{job_id}"
        ):
            try:
                res = requests.get(
                    f"{BACKEND_BASE}/ats/score/job/{job_id}",
                    timeout=30
                )

                if res.status_code == 200:
                    data = res.json()

                    score = data.get("score", 0)
                    st.success(f"🎯 ATS Match Score: {score}%")

                    strengths = data.get("strengths", [])
                    if strengths:
                        st.markdown("### ✅ Strengths")
                        st.write(", ".join(strengths))

                    gaps = data.get("gaps", [])
                    if gaps:
                        st.markdown("### ❌ Skill Gaps")
                        st.write(", ".join(gaps))
                else:
                    st.error("Failed to calculate ATS score")

            except Exception:
                st.error("ATS service error")

        st.divider()

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs([
    "🟢 Fresh Jobs (≤7 days)",
    "🟡 Older Jobs (8–30 days)",
    "📄 ATS Checker (External Jobs)"
])

# ---------------- FRESH JOBS ----------------
with tab1:
    fresh_jobs = fetch_jobs("/jobs")
    st.caption(f"Showing {len(fresh_jobs)} jobs")
    render_jobs(fresh_jobs, "fresh")

# ---------------- OLDER JOBS ----------------
with tab2:
    older_jobs = fetch_jobs("/jobs")
    st.caption(f"Showing {len(older_jobs)} jobs")
    render_jobs(older_jobs, "older")

# ---------------- ATS ONLY ----------------
with tab3:
    st.subheader("📄 AI ATS Checker (Manual Job Description)")

    job_text = st.text_area("Paste Job Description", height=200)
    resume_text = st.text_area("Paste Resume Text", height=200)

    if st.button("Run AI ATS Check"):
        if not job_text or not resume_text:
            st.warning("Please paste both job description and resume")
        else:
            try:
                res = requests.post(
                    f"{BACKEND_BASE}/ats/score",
                    json={
                        "job_description": job_text
                    },
                    timeout=30
                )

                if res.status_code == 200:
                    data = res.json()

                    st.success(f"🎯 ATS Match Score: {data.get('score', 0)}%")

                    if data.get("strengths"):
                        st.markdown("### ✅ Strengths")
                        st.write(", ".join(data["strengths"]))

                    if data.get("gaps"):
                        st.markdown("### ❌ Skill Gaps")
                        st.write(", ".join(data["gaps"]))
                else:
                    st.error("Failed to calculate ATS score")

            except Exception:
                st.error("ATS service error")
