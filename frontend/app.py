import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/jobs"

st.set_page_config(page_title="Anvalyx", layout="wide")

st.title("🔎 Anvalyx")
st.caption("Real-time US Data Analyst jobs • Powered by Adzuna")

# Sidebar filters
st.sidebar.header("Filters")
keyword = st.sidebar.text_input("Keyword", "data analyst")
location = st.sidebar.text_input("Location", "")
min_salary = st.sidebar.number_input("Minimum Salary", min_value=0, step=1000)

if st.sidebar.button("Refresh Jobs"):
    st.experimental_rerun()

params = {
    "keyword": keyword,
    "location": location,
    "min_salary": min_salary
}

response = requests.get(API_URL, params=params)

if response.status_code != 200:
    st.error("Failed to load jobs from backend")
else:
    jobs = response.json()
    st.subheader(f"Showing {len(jobs)} jobs")

    for job in jobs:
        with st.container():
            st.markdown(f"### {job['title']}")
            st.write(f"**Company:** {job['company']}")
            st.write(f"**Location:** {job['location']}")
            st.write(f"**Category:** {job['category']}")

            if job["salary_min"] or job["salary_max"]:
                st.write(
                    f"💰 ${int(job['salary_min']):,} – ${int(job['salary_max']):,}"
                )

            st.markdown(f"[Apply here]({job['url']})")
            st.caption(f"Posted: {job['created']}")
            st.divider()
