import streamlit as st
import requests
import os
from datetime import datetime
from docx import Document
import pdfplumber

BACKEND_BASE = os.getenv(
    "BACKEND_BASE",
    "https://anvalyx-backend.onrender.com"
)

st.set_page_config(
    page_title="Anvalyx",
    page_icon="💼",
    layout="wide"
)

# ---------- HEADER ----------
st.title("💼 Anvalyx")
st.caption("AI-Powered Job Aggregator + ATS Match")

# ---------- SIDEBAR ----------
st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    ["Jobs", "ATS Checker"]
)

# ---------- HELPERS ----------
def fetch_jobs(endpoint):
    try:
        res = requests.get(f"{BACKEND_BASE}{endpoint}", timeout=20)
        if res.status_code == 200:
            return res.json()
    except:
        st.error("Backend not reachable")
    return []

def format_posted(raw):
    if not raw:
        return "Unknown"
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except:
        return raw

# ---------- RESUME ----------
st.sidebar.subheader("Upload Resume")

uploaded_file = st.sidebar.file_uploader(
    "Upload resume",
    type=["pdf", "docx", "txt"]
)

def parse_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def parse_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text()
    return text

def parse_txt(file):
    return file.read().decode()

if uploaded_file:
    if uploaded_file.name.endswith(".docx"):
        resume_text = parse_docx(uploaded_file)
    elif uploaded_file.name.endswith(".pdf"):
        resume_text = parse_pdf(uploaded_file)
    else:
        resume_text = parse_txt(uploaded_file)

    if st.sidebar.button("Save Resume"):
        requests.post(
            f"{BACKEND_BASE}/resume",
            json={"resume_text": resume_text}
        )
        st.sidebar.success("Resume saved")

# ---------- JOB CARD ----------
def render_job_card(job):

    col1, col2 = st.columns([4,1])

    with col1:
        st.subheader(job["title"])
        st.write(f"{job['company']} • {job['location']}")
        st.caption(f"{job['source']} | Posted {format_posted(job.get('posted'))}")

    with col2:
        if job.get("apply_url"):
            st.link_button("Apply", job["apply_url"])

    if st.button("Check ATS Score", key=f"ats{job['id']}"):

        res = requests.get(
            f"{BACKEND_BASE}/ats/score/job/{job['id']}"
        )

        if res.status_code == 200:

            data = res.json()

            st.metric("ATS Score", f"{data['score']}%")

            if data.get("strengths"):
                st.success("Strengths")
                for s in data["strengths"]:
                    st.write(f"• {s}")

            if data.get("gaps"):
                st.warning("Skill Gaps")
                for g in data["gaps"]:
                    st.write(f"• {g}")

    st.divider()

# ---------- JOBS PAGE ----------
if page == "Jobs":

    fresh_jobs = fetch_jobs("/jobs/fresh")
    older_jobs = fetch_jobs("/jobs/older")

    st.header("Fresh Jobs")

    for job in fresh_jobs:
        render_job_card(job)

    st.header("Older Jobs")

    for job in older_jobs:
        render_job_card(job)

# ---------- ATS PAGE ----------
if page == "ATS Checker":

    st.subheader("Manual Job Description")

    job_text = st.text_area("Paste Job Description", height=250)

    if st.button("Run ATS Analysis"):

        res = requests.post(
            f"{BACKEND_BASE}/ats/score",
            json={"job_description": job_text}
        )

        if res.status_code == 200:

            data = res.json()

            st.metric("ATS Score", f"{data['score']}%")

            if data.get("strengths"):
                st.success("Strengths")
                for s in data["strengths"]:
                    st.write(f"• {s}")

            if data.get("gaps"):
                st.warning("Skill Gaps")
                for g in data["gaps"]:
                    st.write(f"• {g}")