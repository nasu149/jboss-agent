"""STEP 0 Streamlit hello page.

The operational dashboard is intentionally deferred until STEP 11.
"""

from __future__ import annotations

import streamlit as st

from jboss_agent.config import get_settings


settings = get_settings()

st.set_page_config(page_title="LangGraph JBoss Agent", page_icon="🧭", layout="centered")
st.title("LangGraph JBoss Incident Response Agent")
st.subheader("STEP 0 — Environment")
st.success("Streamlit is running inside the development environment.")

st.markdown(
    """
This page is intentionally small. LangGraph state, nodes, edges, tools, MCP,
and human approval are introduced in later steps.
"""
)

st.write("**Server ID:**", settings.server_id)
st.write("**JBoss mode:**", settings.jboss_mode)
st.write("**Gemini model:**", settings.gemini_model)
st.write("**GOOGLE_API_KEY configured:**", "Yes" if settings.has_google_api_key else "No")
st.write("**Teams dry-run:**", settings.teams_dry_run)
