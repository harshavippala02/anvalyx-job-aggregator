import streamlit as st
import requests
import os
from datetime import datetime, timedelta
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

# ---------- PAGE STATE ----------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "filter_days" not in st.session_state:
    st.session_state.filter_days = 1


# ---------- CUSTOM CSS ----------
st.markdown("""
<style>

/* MAIN APP */
.stApp{
background:#020617;
color:white;
}

/* FIX SIDEBAR POSITION */
section[data-testid="stSidebar"]{
margin-top:70px;
}

/* NAVBAR BUTTON STYLE */
.stButton > button{
background:#0f172a;
color:white;
border:1px solid #1e293b;
padding:8px 18px;
border-radius:8px;
font-weight:500;
transition:0.2s;
}

.stButton > button:hover{
background:#1e293b;
border:1px solid #334155;
}

/* HERO TITLE */
.hero-title{
font-size:56px;
font-weight:700;
text-align:center;
margin-top:140px;
}

/* HERO SUBTITLE */
.hero-sub{
text-align:center;
font-size:20px;
color:#94a3b8;
margin-bottom:40px;
}

/* JOB CARD */
.job-card{
background:#0f172a;
padding:20px;
border-radius:12px;
margin-bottom:20px;
border:1px solid #1e293b;
}

/* APPLY BUTTON */
.stLinkButton > a{
background:#2563eb;
color:white;
padding:8px 14px;
border-radius:8px;
text-decoration:none;
font-weight:500;
}

.stLinkButton > a:hover{
background:#1d4ed8;
}

</style>
""", unsafe_allow_html=True)


# ---------- NAVBAR ----------
col1,col2,col3,col4,col5,col6 = st.columns([2,1,1,1,1,1])

with col1:
    st.markdown("### Anvalyx")

with col2:
    if st.button("Jobs"):
        st.session_state.page = "jobs"
        st.rerun()

with col3:
    if st.button("Companies"):
        st.info("Companies page coming soon")

with col4:
    if st.button("Resume"):
        st.session_state.page = "resume"
        st.rerun()

with col5:
    if st.button("Login"):
        st.info("Login coming soon")

with col6:
    if st.button("Sign Up"):
        st.info("Signup coming soon")

st.divider()


# ---------- HELPERS ----------
def fetch_jobs():
    try:
        res = requests.get(f"{BACKEND_BASE}/jobs/fresh", timeout=20)
        if res.status_code == 200:
            return res.json()
    except:
        st.error("Backend not reachable")
    return []

def format_posted(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except:
        return None

def filter_jobs(jobs, days):
    filtered = []
    now = datetime.utcnow()

    for job in jobs:
        posted = format_posted(job.get("posted"))
        if posted:
            diff = now - posted
            if diff <= timedelta(days=days):
                filtered.append(job)

    return filtered


# ---------- JOB CARD ----------
def render_job_card(job):

    st.markdown('<div class="job-card">', unsafe_allow_html=True)

    col1,col2 = st.columns([5,1])

    with col1:
        st.subheader(job["title"])
        st.write(f"{job['company']} • {job['location']}")
        st.caption(f"{job['source']} | Posted {job.get('posted','Unknown')}")

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

    st.markdown("</div>", unsafe_allow_html=True)


# ---------- SIDEBAR RESUME ----------
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


# ---------- LANDING PAGE ----------
if st.session_state.page == "home":

    st.markdown("""
    <div class="hero-title">
    Find Your Next Data Analytics Role
    </div>

    <div class="hero-sub">
    AI-powered job aggregator with ATS match scoring
    </div>
    """, unsafe_allow_html=True)

    col1,col2,col3 = st.columns([2,1,2])

    with col2:
        if st.button("Browse Jobs"):
            st.session_state.page = "jobs"
            st.rerun()


# ---------- JOBS PAGE ----------
if st.session_state.page == "jobs":

    st.title("Data Analytics Jobs")

    c1,c2,c3,c4,c5,c6 = st.columns(6)

    if c1.button("24 Hours"):
        st.session_state.filter_days = 1

    if c2.button("3 Days"):
        st.session_state.filter_days = 3

    if c3.button("5 Days"):
        st.session_state.filter_days = 5

    if c4.button("7 Days"):
        st.session_state.filter_days = 7

    if c5.button("10 Days"):
        st.session_state.filter_days = 10

    if c6.button("30 Days"):
        st.session_state.filter_days = 30

    st.divider()

    jobs = fetch_jobs()

    filtered_jobs = filter_jobs(
        jobs,
        st.session_state.filter_days
    )

    for job in filtered_jobs:
        render_job_card(job)

    st.write("")

    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()