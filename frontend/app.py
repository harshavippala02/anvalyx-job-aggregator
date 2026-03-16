import os
from datetime import datetime

import pdfplumber
import requests
import streamlit as st
from docx import Document

BACKEND_BASE = os.getenv(
    "BACKEND_BASE",
    "https://anvalyx-backend.onrender.com"
)

st.set_page_config(
    page_title="Anvalyx",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- SESSION STATE ----------------

if "page" not in st.session_state:
    st.session_state.page = "home"

if "filter_days" not in st.session_state:
    st.session_state.filter_days = 1

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>

/* Hide Streamlit top-right menu / toolbar / footer / header */
[data-testid="stToolbar"] {
    display: none !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}

header {
    display: none !important;
}

footer {
    display: none !important;
}

#MainMenu {
    visibility: hidden;
}

/* Main app */
.stApp {
    background: #f8fafc;
    color: #1f2937;
}

/* Reduce default top padding */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
}

/* Buttons */
.stButton > button {
    background: white;
    border: 1px solid #e5e7eb;
    padding: 10px 18px;
    border-radius: 10px;
    font-weight: 500;
    color: #374151;
    white-space: nowrap;
    min-width: 110px;
    height: 48px;
}

.stButton > button:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
    color: #111827;
}

/* Link button */
.stLinkButton > a {
    background: #2563eb;
    color: white;
    padding: 10px 16px;
    border-radius: 10px;
    text-decoration: none;
    font-weight: 600;
    display: inline-block;
    text-align: center;
}

.stLinkButton > a:hover {
    background: #1d4ed8;
    color: white;
}

/* Navbar brand */
.brand {
    font-size: 34px;
    font-weight: 700;
    color: #1f2937;
    margin-top: 4px;
}

/* Hero section */
.hero-wrap {
    min-height: 62vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.hero-inner {
    text-align: center;
    margin-top: -50px;
}

.hero-title {
    font-size: 72px;
    font-weight: 800;
    line-height: 1.05;
    color: #1f2937;
    margin-bottom: 18px;
}

.hero-sub {
    font-size: 22px;
    color: #6b7280;
    margin-bottom: 34px;
}

/* Job card */
.job-card {
    background: white;
    padding: 22px;
    border-radius: 14px;
    margin-bottom: 18px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

/* Resume upload box */
.upload-box {
    border: 2px dashed #d1d5db;
    padding: 42px;
    border-radius: 14px;
    background: white;
    text-align: center;
    margin-top: 18px;
}

/* Search box spacing */
[data-testid="stTextInput"] {
    margin-top: 0.3rem;
}

/* Cleaner divider spacing */
hr {
    margin-top: 1rem !important;
    margin-bottom: 1.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def fetch_jobs(days=1, search=""):
    try:
        params = {
            "days": days,
            "limit": 100
        }

        if search and search.strip():
            params["search"] = search.strip()

        res = requests.get(f"{BACKEND_BASE}/jobs", params=params, timeout=20)

        if res.status_code == 200:
            return res.json()

        st.warning(f"Jobs API returned {res.status_code}")
        return []
    except Exception:
        st.error("Backend not reachable")
        return []


def format_posted_display(raw):
    if not raw:
        return "Unknown"

    try:
        raw = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(raw)


def parse_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])


def parse_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text


def parse_txt(file):
    return file.read().decode("utf-8", errors="ignore")


def render_job_card(job):
    st.markdown('<div class="job-card">', unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])

    with col1:
        st.subheader(job.get("title", "Untitled Role"))
        st.write(f"{job.get('company', 'Unknown Company')} • {job.get('location', 'Unknown Location')}")
        st.caption(
            f"{job.get('source', 'Unknown Source')} | Posted {format_posted_display(job.get('posted'))}"
        )

    with col2:
        apply_url = job.get("apply_url")
        if apply_url:
            st.link_button("Apply", apply_url)

    job_id = job.get("id", job.get("title", "job"))

    if st.button("Check ATS Score", key=f"ats_{job_id}"):
        try:
            res = requests.get(f"{BACKEND_BASE}/ats/score/job/{job_id}", timeout=20)

            if res.status_code == 200:
                data = res.json()
                st.metric("ATS Score", f"{data.get('score', 0)}%")

                if data.get("strengths"):
                    st.success("Strengths")
                    for s in data["strengths"]:
                        st.write(f"• {s}")

                if data.get("gaps"):
                    st.warning("Skill Gaps")
                    for g in data["gaps"]:
                        st.write(f"• {g}")
            else:
                st.warning("Could not fetch ATS score.")
        except Exception:
            st.warning("ATS service is not reachable right now.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- NAVBAR ----------------

nav1, nav2, nav3, nav4, nav5, nav6, nav7 = st.columns([2.6, 1, 1.1, 1, 1.4, 1, 1])

with nav1:
    st.markdown('<div class="brand">Anvalyx</div>', unsafe_allow_html=True)

with nav2:
    if st.button("Jobs"):
        st.session_state.page = "jobs"
        st.rerun()

with nav3:
    if st.button("Companies"):
        st.info("Companies page coming soon")

with nav4:
    if st.button("Resume"):
        st.session_state.page = "resume"
        st.rerun()

with nav5:
    st.write("")

with nav6:
    if st.button("Login"):
        st.info("Login coming soon")

with nav7:
    if st.button("Sign Up"):
        st.info("Signup coming soon")

st.divider()

# ---------------- HOME PAGE ----------------

if st.session_state.page == "home":
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-inner">
            <div class="hero-title">Find Your Next Data Analytics Role</div>
            <div class="hero-sub">AI-powered job aggregator with ATS match scoring</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.2, 1, 2.2])
    with c2:
        if st.button("Browse Jobs"):
            st.session_state.page = "jobs"
            st.rerun()

# ---------------- JOBS PAGE ----------------

elif st.session_state.page == "jobs":
    st.title("Data Analytics Jobs")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        if st.button("24 Hours"):
            st.session_state.filter_days = 1
            st.rerun()

    with c2:
        if st.button("3 Days"):
            st.session_state.filter_days = 3
            st.rerun()

    with c3:
        if st.button("5 Days"):
            st.session_state.filter_days = 5
            st.rerun()

    with c4:
        if st.button("7 Days"):
            st.session_state.filter_days = 7
            st.rerun()

    with c5:
        if st.button("10 Days"):
            st.session_state.filter_days = 10
            st.rerun()

    with c6:
        if st.button("30 Days"):
            st.session_state.filter_days = 30
            st.rerun()

    st.divider()

    search_value = st.text_input(
        "Search Jobs",
        value=st.session_state.search_query,
        placeholder="Search Data Analyst, SQL, Python..."
    )

    if search_value != st.session_state.search_query:
        st.session_state.search_query = search_value

    jobs = fetch_jobs(
        days=st.session_state.filter_days,
        search=st.session_state.search_query
    )

    st.caption(
        f"Showing jobs from the last {st.session_state.filter_days} day(s)"
        + (f" matching '{st.session_state.search_query}'" if st.session_state.search_query.strip() else "")
    )

    if not jobs:
        st.info("No jobs found for this filter/search.")

    for job in jobs:
        render_job_card(job)

    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()

# ---------------- RESUME PAGE ----------------

elif st.session_state.page == "resume":
    st.title("Upload Your Resume")

    st.markdown('<div class="upload-box">', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload resume",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_file:
        if uploaded_file.name.endswith(".docx"):
            resume_text = parse_docx(uploaded_file)
        elif uploaded_file.name.endswith(".pdf"):
            resume_text = parse_pdf(uploaded_file)
        else:
            resume_text = parse_txt(uploaded_file)

        if st.button("Save Resume"):
            try:
                res = requests.post(
                    f"{BACKEND_BASE}/resume",
                    json={"resume_text": resume_text},
                    timeout=30
                )

                if res.status_code in (200, 201):
                    st.success("Resume saved successfully")
                else:
                    st.warning("Resume upload failed.")
            except Exception:
                st.warning("Resume service is not reachable right now.")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()