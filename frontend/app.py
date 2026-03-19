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

if "source_refresh_results" not in st.session_state:
    st.session_state.source_refresh_results = {}

if "action_result" not in st.session_state:
    st.session_state.action_result = None

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
    padding-left: 2.2rem !important;
    padding-right: 2.2rem !important;
    max-width: 1400px;
}

.stButton > button {
    width: 100%;
    background: white;
    border: 1px solid #e5e7eb;
    padding: 10px 14px;
    border-radius: 12px;
    font-weight: 600;
    color: #374151;
    height: 46px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.stButton > button:hover {
    background: #f3f4f6;
    border-color: #cbd5e1;
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
    grid-template-columns: repeat(5, minmax(0, 1fr));
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

.source-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.source-title {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 6px;
}

.source-muted {
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 10px;
}

.source-metric {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 10px 12px;
    margin-top: 8px;
}

.source-metric-label {
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.source-metric-value {
    font-size: 18px;
    font-weight: 800;
    color: #111827;
    margin-top: 2px;
}

.result-ok {
    margin-top: 10px;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 13px;
}

.result-bad {
    margin-top: 10px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 13px;
}

.result-neutral {
    margin-top: 10px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1e40af;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 13px;
}

.summary-box {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.summary-label {
    font-size: 13px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.summary-value {
    font-size: 28px;
    font-weight: 800;
    color: #111827;
    margin-top: 6px;
}

.source-counts-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 10px;
}

.source-count-box {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.source-count-name {
    font-size: 14px;
    font-weight: 700;
    color: #374151;
}

.source-count-value {
    font-size: 24px;
    font-weight: 800;
    color: #111827;
    margin-top: 4px;
}

hr {
    margin-top: 1rem !important;
    margin-bottom: 1.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def wait_for_backend_ready(max_wait_seconds=180):
    start = time.time()

    while time.time() - start < max_wait_seconds:
        try:
            res = requests.get(f"{BACKEND_BASE}/", timeout=20)
            if res.status_code == 200:
                return True
        except Exception:
            pass

        time.sleep(4)

    return False


@st.cache_data(ttl=15, show_spinner=False)
def fetch_jobs(days=1, search="", status=None):
    try:
        ready = wait_for_backend_ready(max_wait_seconds=180)
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

        res = requests.get(f"{BACKEND_BASE}/jobs", params=params, timeout=40)

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
        ready = wait_for_backend_ready(max_wait_seconds=180)
        if not ready:
            return {
                "status_counts": {
                    "jobs": 0,
                    "saved": 0,
                    "applied": 0,
                    "skipped": 0,
                    "auto_ready": 0,
                    "manual_required": 0,
                    "auto_applied": 0,
                    "auto_failed": 0,
                },
                "day_counts": {"1": 0, "3": 0, "5": 0, "7": 0, "10": 0, "30": 0},
            }

        params = {}
        if search and search.strip():
            params["search"] = search.strip()

        res = requests.get(f"{BACKEND_BASE}/jobs/summary", params=params, timeout=40)
        if res.status_code == 200:
            return res.json()

        return {
            "status_counts": {
                "jobs": 0,
                "saved": 0,
                "applied": 0,
                "skipped": 0,
                "auto_ready": 0,
                "manual_required": 0,
                "auto_applied": 0,
                "auto_failed": 0,
            },
            "day_counts": {"1": 0, "3": 0, "5": 0, "7": 0, "10": 0, "30": 0},
        }
    except Exception:
        return {
            "status_counts": {
                "jobs": 0,
                "saved": 0,
                "applied": 0,
                "skipped": 0,
                "auto_ready": 0,
                "manual_required": 0,
                "auto_applied": 0,
                "auto_failed": 0,
            },
            "day_counts": {"1": 0, "3": 0, "5": 0, "7": 0, "10": 0, "30": 0},
        }


@st.cache_data(ttl=15, show_spinner=False)
def fetch_debug_counts():
    try:
        ready = wait_for_backend_ready(max_wait_seconds=180)
        if not ready:
            return {}

        res = requests.get(f"{BACKEND_BASE}/jobs/debug-counts", timeout=40)
        if res.status_code == 200:
            return res.json()

        return {}
    except Exception:
        return {}


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
        ready = wait_for_backend_ready(max_wait_seconds=180)
        if not ready:
            return {
                "ok": False,
                "status_code": None,
                "headers": {},
                "data": {"error": "Backend did not wake up in time"},
            }

        res = requests.post(f"{BACKEND_BASE}{endpoint_path}", timeout=240)

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


def run_auto_apply_classification():
    try:
        ready = wait_for_backend_ready(max_wait_seconds=180)
        if not ready:
            return {
                "ok": False,
                "data": {"error": "Backend did not wake up in time"}
            }

        res = requests.post(f"{BACKEND_BASE}/jobs/classify-auto-apply", timeout=120)

        try:
            data = res.json()
        except Exception:
            data = {"raw_text": res.text}

        return {"ok": res.status_code == 200, "data": data}
    except Exception as e:
        return {"ok": False, "data": {"error": str(e)}}


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
    mapping = {
        "saved": "saved",
        "applied": "applied",
        "skipped": "skipped",
        "auto_ready": "auto_ready",
        "manual_required": "manual_required",
        "auto_applied": "auto_applied",
        "auto_failed": "auto_failed",
    }
    return mapping.get(st.session_state.job_view, None)


def current_view_label():
    mapping = {
        "jobs": "Jobs",
        "saved": "Saved",
        "applied": "Applied",
        "skipped": "Skipped",
        "auto_ready": "Auto Apply Ready",
        "manual_required": "Manual Apply Required",
        "auto_applied": "Auto Applied",
        "auto_failed": "Auto Failed",
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
    apply_type_value = job.get("apply_type") or "Unknown"

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
            <div class="info-box">
                <div class="info-label">Apply Type</div>
                <div class="info-value">{apply_type_value}</div>
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
    current_view = st.session_state.job_view

    if current_view == "auto_ready":
        b1, b2 = st.columns([1, 1])

        with b1:
            if st.button("Move To Manual", key=f"manual_{job_id}"):
                if update_job_status(job_id, "manual_required"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

        with b2:
            if st.button("Save", key=f"save_auto_{job_id}"):
                if update_job_status(job_id, "saved"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

    elif current_view == "manual_required":
        b1, b2, b3 = st.columns([1, 1, 1])

        with b1:
            if st.button("Applied", key=f"applied_manual_{job_id}"):
                if update_job_status(job_id, "applied"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

        with b2:
            if st.button("Skip", key=f"skip_manual_{job_id}"):
                if update_job_status(job_id, "skipped"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

        with b3:
            if st.button("Save", key=f"save_manual_{job_id}"):
                if update_job_status(job_id, "saved"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

    elif current_view in {"auto_applied", "auto_failed"}:
        b1, b2 = st.columns([1, 1])

        with b1:
            if st.button("Mark Applied", key=f"mark_applied_{job_id}"):
                if update_job_status(job_id, "applied"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

        with b2:
            if st.button("Move To Manual", key=f"manual_failed_{job_id}"):
                if update_job_status(job_id, "manual_required"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Could not update status")

    else:
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


def render_refresh_result(source_key):
    result = st.session_state.source_refresh_results.get(source_key)

    if not result:
        st.markdown(
            '<div class="result-neutral">No refresh run yet for this source.</div>',
            unsafe_allow_html=True
        )
        return

    data = result.get("data", {})

    if result.get("ok"):
        st.markdown(
            f"""
            <div class="result-ok">
                <strong>Last refresh OK</strong><br>
                fetched={data.get('fetched', 0)} |
                inserted={data.get('inserted', 0)} |
                updated={data.get('updated', 0)} |
                skipped={data.get('skipped', 0)}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="result-bad">
                <strong>Last refresh failed</strong><br>
                status={result.get('status_code')} |
                error={data.get('error') or data.get('detail') or data.get('raw_text') or data}
            </div>
            """,
            unsafe_allow_html=True
        )


def run_source_refresh(source_key, endpoint_path, spinner_text):
    with st.spinner(spinner_text):
        result = refresh_source_jobs(endpoint_path)

    st.session_state.source_refresh_results[source_key] = result
    st.cache_data.clear()
    st.rerun()


def render_source_card(title, source_key, endpoint_path, db_count, spinner_text):
    st.markdown('<div class="source-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="source-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="source-muted">Jobs currently stored from this API</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="source-metric">
            <div class="source-metric-label">Current DB Count</div>
            <div class="source-metric-value">{db_count}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(f"Refresh {title}", key=f"refresh_{source_key}"):
        run_source_refresh(source_key, endpoint_path, spinner_text)

    render_refresh_result(source_key)
    st.markdown('</div>', unsafe_allow_html=True)


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

    debug_counts = fetch_debug_counts()

    st.subheader("Source Dashboard")

    top1, top2, top3, top4 = st.columns(4)

    with top1:
        st.markdown(
            f"""
            <div class="summary-box">
                <div class="summary-label">Total Jobs in DB</div>
                <div class="summary-value">{debug_counts.get('all_jobs', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with top2:
        st.markdown(
            f"""
            <div class="summary-box">
                <div class="summary-label">Fresh Jobs</div>
                <div class="summary-value">{debug_counts.get('fresh_jobs_active_sources', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with top3:
        st.markdown(
            f"""
            <div class="summary-box">
                <div class="summary-label">Auto Ready</div>
                <div class="summary-value">{debug_counts.get('auto_ready', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with top4:
        st.markdown(
            f"""
            <div class="summary-box">
                <div class="summary-label">Manual Required</div>
                <div class="summary-value">{debug_counts.get('manual_required', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    st.markdown("### Jobs from each API")

    st.markdown(
        f"""
        <div class="source-counts-grid">
            <div class="source-count-box">
                <div class="source-count-name">JSearch</div>
                <div class="source-count-value">{debug_counts.get('jsearch', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">LinkedIn</div>
                <div class="source-count-value">{debug_counts.get('linkedin', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">USAJobs</div>
                <div class="source-count-value">{debug_counts.get('usajobs', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">Adzuna</div>
                <div class="source-count-value">{debug_counts.get('adzuna', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">Greenhouse</div>
                <div class="source-count-value">{debug_counts.get('greenhouse', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">Lever</div>
                <div class="source-count-value">{debug_counts.get('lever', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">Remotive</div>
                <div class="source-count-value">{debug_counts.get('remotive', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">Arbeitnow</div>
                <div class="source-count-value">{debug_counts.get('arbeitnow', 0)}</div>
            </div>
            <div class="source-count-box">
                <div class="source-count-name">Jobicy</div>
                <div class="source-count-value">{debug_counts.get('jobicy', 0)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    st.subheader("Refresh Sources")

    a1, a2, a3 = st.columns([1.2, 1.5, 4])

    with a1:
        if st.button("Wake Backend"):
            with st.spinner("Waking backend... this can take 1-3 minutes on Render cold start"):
                if wait_for_backend_ready(max_wait_seconds=180):
                    st.success("Backend is awake")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Backend did not wake up in time")

    with a2:
        if st.button("Refresh Counts"):
            st.cache_data.clear()
            st.rerun()

    with a3:
        if st.button("Classify Non-LinkedIn Auto Apply"):
            with st.spinner("Classifying non-LinkedIn jobs into auto/manual buckets..."):
                result = run_auto_apply_classification()
                st.session_state.action_result = result
                st.cache_data.clear()
                st.rerun()

    if st.session_state.action_result:
        result = st.session_state.action_result
        data = result.get("data", {})
        if result.get("ok"):
            st.success(
                f"Classification complete | scanned={data.get('scanned', 0)} | "
                f"auto_ready={data.get('auto_ready', 0)} | "
                f"manual_required={data.get('manual_required', 0)} | "
                f"unchanged={data.get('unchanged', 0)}"
            )
        else:
            st.error(f"Classification failed: {data.get('error') or data}")

    row1 = st.columns(3)
    row2 = st.columns(3)
    row3 = st.columns(3)

    with row1[0]:
        render_source_card(
            title="JSearch Jobs",
            source_key="jsearch",
            endpoint_path="/refresh-jsearch",
            db_count=debug_counts.get("jsearch", 0),
            spinner_text="Refreshing JSearch jobs..."
        )

    with row1[1]:
        render_source_card(
            title="LinkedIn Jobs",
            source_key="linkedin",
            endpoint_path="/refresh-linkedin",
            db_count=debug_counts.get("linkedin", 0),
            spinner_text="Refreshing LinkedIn jobs..."
        )

    with row1[2]:
        render_source_card(
            title="USAJobs Jobs",
            source_key="usajobs",
            endpoint_path="/refresh-usajobs",
            db_count=debug_counts.get("usajobs", 0),
            spinner_text="Refreshing USAJobs jobs..."
        )

    with row2[0]:
        render_source_card(
            title="Adzuna Jobs",
            source_key="adzuna",
            endpoint_path="/refresh-adzuna",
            db_count=debug_counts.get("adzuna", 0),
            spinner_text="Refreshing Adzuna jobs..."
        )

    with row2[1]:
        render_source_card(
            title="Greenhouse Jobs",
            source_key="greenhouse",
            endpoint_path="/refresh-greenhouse",
            db_count=debug_counts.get("greenhouse", 0),
            spinner_text="Refreshing Greenhouse jobs..."
        )

    with row2[2]:
        render_source_card(
            title="Lever Jobs",
            source_key="lever",
            endpoint_path="/refresh-lever",
            db_count=debug_counts.get("lever", 0),
            spinner_text="Refreshing Lever jobs..."
        )

    with row3[0]:
        render_source_card(
            title="Remotive Jobs",
            source_key="remotive",
            endpoint_path="/refresh-remotive",
            db_count=debug_counts.get("remotive", 0),
            spinner_text="Refreshing Remotive jobs..."
        )

    with row3[1]:
        render_source_card(
            title="Arbeitnow Jobs",
            source_key="arbeitnow",
            endpoint_path="/refresh-arbeitnow",
            db_count=debug_counts.get("arbeitnow", 0),
            spinner_text="Refreshing Arbeitnow jobs..."
        )

    with row3[2]:
        render_source_card(
            title="Jobicy Jobs",
            source_key="jobicy",
            endpoint_path="/refresh-jobicy",
            db_count=debug_counts.get("jobicy", 0),
            spinner_text="Refreshing Jobicy jobs..."
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

    s5, s6, s7, s8 = st.columns([1, 1, 1, 1])

    with s5:
        if st.button(f"Auto Ready ({status_counts.get('auto_ready', 0)})"):
            st.session_state.job_view = "auto_ready"
            st.rerun()

    with s6:
        if st.button(f"Manual Apply ({status_counts.get('manual_required', 0)})"):
            st.session_state.job_view = "manual_required"
            st.rerun()

    with s7:
        if st.button(f"Auto Applied ({status_counts.get('auto_applied', 0)})"):
            st.session_state.job_view = "auto_applied"
            st.rerun()

    with s8:
        if st.button(f"Auto Failed ({status_counts.get('auto_failed', 0)})"):
            st.session_state.job_view = "auto_failed"
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

    if st.session_state.job_view == "auto_ready":
        caption_text += " | LinkedIn excluded"
    if st.session_state.job_view == "manual_required":
        caption_text += " | non-LinkedIn manual fallback bucket"
    if st.session_state.job_view == "auto_applied":
        caption_text += " | only real auto-applied jobs should appear here"

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