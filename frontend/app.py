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

.stApp{
background:#f8fafc;
color:#1f2937;
}

/* NAVBAR BUTTONS */

.stButton > button{
background:white;
border:1px solid #e5e7eb;
padding:8px 18px;
border-radius:8px;
font-weight:500;
color:#374151;
}

.stButton > button:hover{
background:#f3f4f6;
}

/* HERO */

.hero-title{
font-size:48px;
font-weight:700;
text-align:center;
margin-top:120px;
}

.hero-sub{
text-align:center;
font-size:20px;
color:#6b7280;
margin-bottom:40px;
}

/* JOB CARD */

.job-card{
background:white;
padding:20px;
border-radius:12px;
margin-bottom:20px;
border:1px solid #e5e7eb;
box-shadow:0 4px 10px rgba(0,0,0,0.04);
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

/* UPLOAD BOX */

.upload-box{
border:2px dashed #e5e7eb;
padding:40px;
border-radius:12px;
background:white;
text-align:center;
}

</style>
""", unsafe_allow_html=True)

# ---------------- NAVBAR ----------------

col1,col2,col3,col4,col5 = st.columns([3,1,1,1,1])

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

    cA,cB = st.columns(2)

    with cA:
        if st.button("Login"):
            st.info("Login coming soon")

    with cB:
        if st.button("Sign Up"):
            st.info("Signup coming soon")

st.divider()

# ---------------- HELPERS ----------------

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

    filtered=[]
    now=datetime.utcnow()

    for job in jobs:

        posted=format_posted(job.get("posted"))

        if posted:

            diff=now-posted

            if diff <= timedelta(days=days):
                filtered.append(job)

        else:
            filtered.append(job)

    return filtered


def search_jobs(jobs, query):

    if not query:
        return jobs

    query=query.lower()

    results=[]

    for job in jobs:

        text=f"{job.get('title','')} {job.get('company','')} {job.get('location','')}"

        if query in text.lower():
            results.append(job)

    return results


# ---------------- JOB CARD ----------------

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

        res=requests.get(
            f"{BACKEND_BASE}/ats/score/job/{job['id']}"
        )

        if res.status_code==200:

            data=res.json()

            st.metric("ATS Score",f"{data['score']}%")

            if data.get("strengths"):
                st.success("Strengths")
                for s in data["strengths"]:
                    st.write(f"• {s}")

            if data.get("gaps"):
                st.warning("Skill Gaps")
                for g in data["gaps"]:
                    st.write(f"• {g}")

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------- RESUME PARSING ----------------

def parse_docx(file):
    doc=Document(file)
    return "\n".join([p.text for p in doc.paragraphs])


def parse_pdf(file):

    text=""

    with pdfplumber.open(file) as pdf:

        for page in pdf.pages:

            if page.extract_text():
                text+=page.extract_text()

    return text


def parse_txt(file):
    return file.read().decode()


# ---------------- HOME PAGE ----------------

if st.session_state.page=="home":

    st.markdown("""
    <div class="hero-title">
    Find Your Next Data Analytics Role
    </div>

    <div class="hero-sub">
    AI-powered job aggregator with ATS match scoring
    </div>
    """, unsafe_allow_html=True)

    col1,col2,col3=st.columns([2,1,2])

    with col2:

        if st.button("Browse Jobs"):
            st.session_state.page="jobs"
            st.rerun()


# ---------------- JOBS PAGE ----------------

elif st.session_state.page=="jobs":

    st.title("Data Analytics Jobs")

    c1,c2,c3,c4,c5,c6=st.columns(6)

    if c1.button("24 Hours"):
        st.session_state.filter_days=2

    if c2.button("3 Days"):
        st.session_state.filter_days=3

    if c3.button("5 Days"):
        st.session_state.filter_days=5

    if c4.button("7 Days"):
        st.session_state.filter_days=7

    if c5.button("10 Days"):
        st.session_state.filter_days=10

    if c6.button("30 Days"):
        st.session_state.filter_days=30

    st.divider()

    # SEARCH BAR
    st.session_state.search_query = st.text_input(
        "Search Jobs",
        placeholder="Search Data Analyst, SQL, Python..."
    )

    st.write("")

    jobs=fetch_jobs()

    filtered_jobs=filter_jobs(
        jobs,
        st.session_state.filter_days
    )

    filtered_jobs=search_jobs(
        filtered_jobs,
        st.session_state.search_query
    )

    for job in filtered_jobs:
        render_job_card(job)

    if st.button("← Back to Home"):
        st.session_state.page="home"
        st.rerun()


# ---------------- RESUME PAGE ----------------

elif st.session_state.page=="resume":

    st.title("Upload Your Resume")

    st.markdown('<div class="upload-box">', unsafe_allow_html=True)

    uploaded_file=st.file_uploader(
        "Upload resume",
        type=["pdf","docx","txt"]
    )

    if uploaded_file:

        if uploaded_file.name.endswith(".docx"):
            resume_text=parse_docx(uploaded_file)

        elif uploaded_file.name.endswith(".pdf"):
            resume_text=parse_pdf(uploaded_file)

        else:
            resume_text=parse_txt(uploaded_file)

        if st.button("Save Resume"):

            requests.post(
                f"{BACKEND_BASE}/resume",
                json={"resume_text":resume_text}
            )

            st.success("Resume saved successfully")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("← Back to Home"):
        st.session_state.page="home"
        st.rerun()