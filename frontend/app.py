import os
import time
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

if "job_view" not in st.session_state:
    st.session_state.job_view = "jobs"

if "ats_cache" not in st.session_state:
    st.session_state.ats_cache = {}

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
header { display: none !important; }
footer { display: none !important; }
#MainMenu { visibility: hidden; }

.stApp {
    background: #f8fafc;
    color: #1f2937;
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
}

.stButton > button {
    background: white;
    border: 1px solid #e5e7eb;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 500;
    color: #374151;
    white-space: nowrap;
    min-width: 90px;
    height: 46px;
}

.stButton > button:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
    color: #111827;
}

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

.brand {
    font-size: 34px;
    font-weight: 700;
    color: #1f2937;
    margin-top: 4px;
}

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

.job-card {
    background: white;
    padding: 22px;
    border-radius: 14px;
    margin-bottom: 18px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-top: 14px;
    margin-bottom: 16px;
}

.info-box {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px 10px;
}

.info-label {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 4px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.info-value {
    font-size: 14px;
    color: #111827;
    font-weight: 700;
    line-height: 1.35;
    word-break: break-word;
}

.upload-box {
    border: 2px dashed #d1d5db;
    padding: 42px;
    border-radius: 14px;
    background: white;
    text-align: center;
    margin-top: 18px;
}

[data-testid="stTextInput"] {
    margin-top: 0.3rem;
}

hr {
    margin-top: 1rem !important;
    margin-bottom: 1.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def wait_for_backend_ready(max_wait_seconds=75):
    start = time.time()

    while time.time() - start < max_wait_seconds:
        try:
            res = requests.get(f"{BACKEND_BASE}/", timeout=10)
            if res.status_code == 200:
                return True
        except Exception:
            pass

        time.sleep(3)

    return False


@st.cache_data(ttl=15, show_spinner=False)
def fetch_jobs(days=1, search="", status=None):
    try:
        ready = wait_for_backend_ready(max_wait_seconds=75)
        if not ready:
            return []

        params = {
            "days": days,
            "limit": 100
        }

        if search and search.strip():
            params["search"] = search.strip()

        if status:
            params["status"] = status

        res = requests.get(f"{BACKEND_BASE}/jobs", params=params, timeout=30)

        if res.status_code == 200:
            return res.json()

        try:
            error_body = res.json()
        except Exception:
            error_body = res.text

        st.warning(f"Jobs API returned {res.status_code}: {error_body}")
        return []
    except Exception as e:
        st.error(f"Backend not reachable: {e}")
        return []


@st.cache_data(ttl=15, show_spinner=False)
def fetch_summary(search=""):
    try:
        ready = wait_for_backend_ready(max_wait_seconds=75)
        if not ready:
            return {
                "status_counts": {"jobs": 0, "saved": 0, "applied": 0, "skipped": 0},
                "day_counts": {"1": 0, "3": 0, "5": 0, "7": 0, "10": 0, "30": 0},
            }

        params = {}
        if search and search.strip():
            params["search"] = search.strip()

        res = requests.get(f"{BACKEND_BASE}/jobs/summary", params=params, timeout=30)
        if res.status_code == 200:
            return res.json()

        return {
            "status_counts": {"jobs": 0, "saved": 0, "applied": 0, "skipped": 0},
            "day_counts": {"1": 0, "3": 0, "5": 0, "7": 0, "10": 0, "30": 0},
        }
    except Exception:
        return {
            "status_counts": {"jobs": 0, "saved": 0, "applied": 0, "skipped": 0},
            "day_counts": {"1": 0, "3": 0, "5": 0, "7": 0, "10": 0, "30": 0},
        }


def update_job_status(job_id, status_value):
    try:
        res = requests.post(
            f"{BACKEND_BASE}/jobs/{job_id}/status",
            params={"status": status_value},
            timeout=20
        )
        return res.status_code == 200
    except Exception:
        return False


def refresh_source_jobs(endpoint_path):
    try:
        ready = wait_for_backend_ready(max_wait_seconds=75)
        if not ready:
            return {
                "ok": False,
                "status_code": None,
                "headers": {},
                "data": {"error": "Backend did not wake up in time"},
            }

        res = requests.post(f"{BACKEND_BASE}{endpoint_path}", timeout=180)

        try:
            data = res.json()
        except Exception:
            data = {"raw_text": res.text}

        return {
            "ok": res.status_code == 200,
            "status_code": res.status_code,
            "headers": dict(res.headers),
            "data": data,
        }
    except Exception as e:
        return {
            "ok": False,
            "status_code": None,
            "headers": {},
            "data": {"error": str(e)},
        }


def fetch_ats_score(job_id):
    cache = st.session_state.ats_cache

    if job_id in cache:
        return cache[job_id]

    try:
        res = requests.get(f"{BACKEND_BASE}/ats/score/job/{job_id}", timeout=12)
        if res.status_code == 200:
            data = res.json()
            score = data.get("score", None)
            cache[job_id] = score
            return score
    except Exception:
        pass

    cache[job_id] = None
    return None


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


def current_status_filter():
    if st.session_state.job_view == "saved":
        return "saved"
    if st.session_state.job_view == "applied":
        return "applied"
    if st.session_state.job_view == "skipped":
        return "skipped"
    return None


def current_view_label():
    mapping = {
        "jobs": "Jobs",
        "saved": "Saved",
        "applied": "Applied",
        "skipped": "Skipped"
    }
    return mapping.get(st.session_state.job_view, "Jobs")


def build_location_display(job):
    work_mode = job.get("work_mode") or "Unknown"
    location = job.get("location") or "Unknown"
    return f"{work_mode} • {location}"


def render_info_boxes(job, ats_score):
    experience_value = job.get("experience_display") or "Unknown"
    location_value = build_location_display(job)
    job_type_value = job.get("job_type") or "Unknown"
    ats_value = f"{ats_score}%" if ats_score is not None else "--"

    st.markdown(
        f"""
        <div class="info-grid">
            <div class="info-box">
                <div class="info-label">Experience</div>
                <div class="info-value">{experience_value}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Location</div>
                <div class="info-value">{location_value}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Job Type</div>
                <div class="info-value">{job_type_value}</div>
            </div>
            <div class="info-box">
                <div class="info-label">ATS Score</div>
                <div class="info-value">{ats_value}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_job_card(job):
    st.markdown('<div class="job-card">', unsafe_allow_html=True)

    top_left, top_right = st.columns([6, 1])

    with top_left:
        st.subheader(job.get("title", "Untitled Role"))
        st.write(f"{job.get('company', 'Unknown Company')} • {job.get('location', 'Unknown Location')}")
        st.caption(
            f"{job.get('source', 'Unknown Source')} | Posted {format_posted_display(job.get('posted'))} | Status: {job.get('status', 'new')}"
        )

    with top_right:
        apply_url = job.get("apply_url")
        if apply_url:
            st.link_button("Apply", apply_url)

    ats_score = fetch_ats_score(job.get("id"))
    render_info_boxes(job, ats_score)

    job_id = job.get("id", job.get("title", "job"))

    b1, b2, b3 = st.columns([1, 1, 1])

    with b1:
        if st.button("Applied", key=f"applied_{job_id}"):
            if update_job_status(job_id, "applied"):
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Could not update status")

    with b2:
        if st.button("Skip", key=f"skip_{job_id}"):
            if update_job_status(job_id, "skipped"):
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Could not update status")

    with b3:
        if st.button("Save", key=f"save_{job_id}"):
            if update_job_status(job_id, "saved"):
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Could not update status")

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
    st.caption(f"Backend: {BACKEND_BASE}")

    st.subheader("Refresh Sources")
    wake_col, r1c1, r1c2, r1c3, r1c4 = st.columns(5)

    with wake_col:
        if st.button("Wake Backend"):
            with st.spinner("Waking backend..."):
                if wait_for_backend_ready():
                    st.success("Backend is awake")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Backend did not wake up in time")

    with r1c1:
        if st.button("Refresh JSearch Jobs"):
            with st.spinner("Refreshing JSearch jobs..."):
                result = refresh_source_jobs("/refresh-jsearch")

            if result["ok"]:
                data = result["data"]
                st.success(
                    f"JSearch refreshed: fetched={data.get('fetched', 0)}, "
                    f"inserted={data.get('inserted', 0)}, updated={data.get('updated', 0)}, "
                    f"skipped={data.get('skipped', 0)}"
                )
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(
                    f"JSearch refresh failed | status={result.get('status_code')} | "
                    f"data={result.get('data')}"
                )

    with r1c2:
        if st.button("Refresh LinkedIn Jobs"):
            with st.spinner("Refreshing LinkedIn jobs..."):
                result = refresh_source_jobs("/refresh-linkedin")

            if result["ok"]:
                data = result["data"]
                st.success(
                    f"LinkedIn refreshed: fetched={data.get('fetched', 0)}, "
                    f"inserted={data.get('inserted', 0)}, updated={data.get('updated', 0)}, "
                    f"skipped={data.get('skipped', 0)}"
                )
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(
                    f"LinkedIn refresh failed | status={result.get('status_code')} | "
                    f"data={result.get('data')}"
                )

    with r1c3:
        if st.button("Refresh USAJobs Jobs"):
            with st.spinner("Refreshing USAJobs jobs..."):
                result = refresh_source_jobs("/refresh-usajobs")

            if result["ok"]:
                data = result["data"]
                st.success(
                    f"USAJobs refreshed: fetched={data.get('fetched', 0)}, "
                    f"inserted={data.get('inserted', 0)}, updated={data.get('updated', 0)}, "
                    f"skipped={data.get('skipped', 0)}"
                )
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(
                    f"USAJobs refresh failed | status={result.get('status_code')} | "
                    f"data={result.get('data')}"
                )

    with r1c4:
        if st.button("Refresh Adzuna Jobs"):
            with st.spinner("Refreshing Adzuna jobs..."):
                result = refresh_source_jobs("/refresh-adzuna")

            if result["ok"]:
                data = result["data"]
                st.success(
                    f"Adzuna refreshed: fetched={data.get('fetched', 0)}, "
                    f"inserted={data.get('inserted', 0)}, updated={data.get('updated', 0)}, "
                    f"skipped={data.get('skipped', 0)}"
                )
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(
                    f"Adzuna refresh failed | status={result.get('status_code')} | "
                    f"data={result.get('data')}"
                )

    st.write("")

    summary = fetch_summary(st.session_state.search_query)
    status_counts = summary.get("status_counts", {})
    day_counts = summary.get("day_counts", {})

    s1, s2, s3, s4 = st.columns([1, 1, 1, 1])

    with s1:
        if st.button(f"Jobs ({status_counts.get('jobs', 0)})"):
            st.session_state.job_view = "jobs"
            st.rerun()

    with s2:
        if st.button(f"Saved ({status_counts.get('saved', 0)})"):
            st.session_state.job_view = "saved"
            st.rerun()

    with s3:
        if st.button(f"Applied ({status_counts.get('applied', 0)})"):
            st.session_state.job_view = "applied"
            st.rerun()

    with s4:
        if st.button(f"Skipped ({status_counts.get('skipped', 0)})"):
            st.session_state.job_view = "skipped"
            st.rerun()

    st.caption(f"Current view: {current_view_label()}")

    d1, d2, d3, d4, d5, d6, d7 = st.columns([1, 1, 1, 1, 1, 1, 5])

    with d1:
        if st.button(f"24 Hours ({day_counts.get('1', 0)})"):
            st.session_state.filter_days = 1
            st.rerun()

    with d2:
        if st.button(f"3 Days ({day_counts.get('3', 0)})"):
            st.session_state.filter_days = 3
            st.rerun()

    with d3:
        if st.button(f"5 Days ({day_counts.get('5', 0)})"):
            st.session_state.filter_days = 5
            st.rerun()

    with d4:
        if st.button(f"7 Days ({day_counts.get('7', 0)})"):
            st.session_state.filter_days = 7
            st.rerun()

    with d5:
        if st.button(f"10 Days ({day_counts.get('10', 0)})"):
            st.session_state.filter_days = 10
            st.rerun()

    with d6:
        if st.button(f"30 Days ({day_counts.get('30', 0)})"):
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
        st.rerun()

    jobs = fetch_jobs(
        days=st.session_state.filter_days,
        search=st.session_state.search_query,
        status=current_status_filter()
    )

    bucket_labels = {
        1: "last 24 hours",
        3: "1 to 3 days ago",
        5: "3 to 5 days ago",
        7: "5 to 7 days ago",
        10: "7 to 10 days ago",
        30: "10 to 30 days ago",
    }

    label = bucket_labels.get(
        st.session_state.filter_days,
        f"last {st.session_state.filter_days} days"
    )

    if st.session_state.job_view == "jobs":
        caption_text = f"Showing active jobs posted {label} with 6+ years hidden"
    else:
        caption_text = f"Showing {current_view_label().lower()} jobs posted {label}"

    if st.session_state.search_query.strip():
        caption_text += f" matching '{st.session_state.search_query}'"

    st.caption(caption_text)

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
                    st.session_state.ats_cache = {}
                    st.cache_data.clear()
                    st.success("Resume saved successfully")
                else:
                    st.warning("Resume upload failed.")
            except Exception:
                st.warning("Resume service is not reachable right now.")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()