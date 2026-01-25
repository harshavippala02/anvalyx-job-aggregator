import streamlit as st
import requests
import os
from datetime import datetime

# -------- Resume parsing libs --------
from docx import Document
import pdfplumber

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
    except Exception:
        st.error("Backend not reachable")
    return []

def format_posted(job: dict) -> str:
    raw = job.get("posted")
    if not raw:
        return "Unknown"
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except Exception:
        return raw

# ---------------- RESUME PARSERS ----------------
def parse_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def parse_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

def parse_txt(file):
    return file.read().decode("utf-8")

# ---------------- RESUME UPLOAD ----------------
st.markdown("### 📄 Upload Resume (Required for ATS)")

uploaded_file = st.file_uploader(
    "Upload your resume (PDF, DOCX, TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    resume_text = ""

    try:
        if uploaded_file.name.endswith(".docx"):
            resume_text = parse_docx(uploaded_file)
        elif uploaded_file.name.endswith(".pdf"):
            resume_text = parse_pdf(uploaded_file)
        elif uploaded_file.name.endswith(".txt"):
            resume_text = parse_txt(uploaded_file)

        if st.button("⬆️ Save Resume"):
            res = requests.post(
                f"{BACKEND_BASE}/resume",
                json={"resume_text": resume_text},
                timeout=30
            )

            if res.status_code == 200:
                st.success("✅ Resume saved successfully")
            else:
                st.error("❌ Failed to save resume")

    except Exception as e:
        st.error("❌ Resume parsing failed")

st.divider()

# ---------------- JOB RENDERER ----------------
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
        apply_url = job.get("apply_url")
        job_id = job.get("id")

        st.markdown(f"## {title}")
        st.write(f"**Company:** {company}")
        st.write(f"**Location:** {location}")
        st.write(f"**Source:** {source}")
        st.write(f"**Posted:** {posted}")

        if apply_url:
            st.markdown(f"[Apply Here]({apply_url})")

        if job_id and st.button(
            "📊 Check AI ATS Score",
            key=f"ats_{section}_{job_id}"
        ):
            res = requests.get(
                f"{BACKEND_BASE}/ats/score/job/{job_id}",
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
                st.error("ATS calculation failed")

        st.divider()

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs([
    "🟢 Fresh Jobs (≤7 days)",
    "🟡 Older Jobs (8–30 days)",
    "📄 ATS Checker (External Jobs)"
])

# ---------------- FRESH JOBS ----------------
with tab1:
    jobs = fetch_jobs("/jobs/fresh")
    st.caption(f"Showing {len(jobs)} fresh jobs")
    render_jobs(jobs, "fresh")

# ---------------- OLDER JOBS ----------------
with tab2:
    jobs = fetch_jobs("/jobs/older")
    st.caption(f"Showing {len(jobs)} older jobs")
    render_jobs(jobs, "older")

# ---------------- MANUAL ATS ----------------
with tab3:
    st.subheader("📄 AI ATS Checker (Manual Job Description)")
    job_text = st.text_area("Paste Job Description", height=200)

    if st.button("Run AI ATS Check"):
        res = requests.post(
            f"{BACKEND_BASE}/ats/score",
            json={"job_description": job_text},
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
            st.error("ATS check failed")
