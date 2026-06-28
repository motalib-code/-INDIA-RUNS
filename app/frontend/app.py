import json
from pathlib import Path

import plotly.express as px
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="CortexRank", layout="wide")
st.title("CortexRank — Resume-JD Matching")

with st.sidebar:
    st.header("Index Management")
    if st.button("Build Index from sample_resumes"):
        with st.spinner("Building index..."):
            r = requests.post(f"{API_BASE}/index/build")
            if r.ok:
                st.success(f"Indexed {r.json()['count']} resumes")
            else:
                st.error(r.json().get("detail", "Build failed"))

    if st.button("Load saved index"):
        with st.spinner("Loading index..."):
            r = requests.post(f"{API_BASE}/index/load")
            if r.ok:
                st.success(f"Loaded {r.json()['count']} resumes")
            else:
                st.error(r.json().get("detail", "Load failed"))

    r = requests.get(f"{API_BASE}/health")
    if r.ok:
        built = r.json()["index_built"]
        st.caption(f"Index built: {'✅' if built else '❌'}")

st.header("Search")

tab1, tab2 = st.tabs(["Upload JD (PDF)", "Paste JD Text"])

with tab1:
    uploaded = st.file_uploader("Upload a job description PDF", type=["pdf"])
    if uploaded and st.button("Search from PDF"):
        with st.spinner("Searching..."):
            r = requests.post(
                f"{API_BASE}/search/pdf",
                files={"file": (uploaded.name, uploaded.read(), "application/pdf")},
            )
            if r.ok:
                _show_results(r.json())
            else:
                st.error(r.json().get("detail", "Search failed"))

with tab2:
    jd_text = st.text_area("Paste job description text", height=300)
    if jd_text and st.button("Search from Text"):
        with st.spinner("Searching..."):
            r = requests.post(
                f"{API_BASE}/search/text",
                params={"jd_text": jd_text},
            )
            if r.ok:
                _show_results(r.json())
            else:
                st.error(r.json().get("detail", "Search failed"))


def _show_results(results: list[dict]) -> None:
    if not results:
        st.warning("No matching resumes found")
        return

    for r in results:
        with st.container(border=True):
            cols = st.columns([3, 1])
            cols[0].markdown(f"### {r['name']}  (`{r['profile_id']}`)")
            cols[1].metric("Composite Score", f"{r['composite_score']:.1f}")

            st.markdown(f"**Skills:** {r['skills']}")

            dims = {
                "Skill": r["skill_score"],
                "Experience": r["experience_score"],
                "Education": r["education_score"],
                "Behavioral": r["behavioral_score"],
            }
            fig = px.bar(
                x=list(dims.keys()),
                y=list(dims.values()),
                labels={"x": "Dimension", "y": "Score"},
                range_y=[0, 100],
                height=200,
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

            st.caption(f"**Explanation:** {r['explanation']}")
