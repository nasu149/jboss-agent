"""Small status page through STEP 2.

The operational dashboard remains intentionally deferred until STEP 11.
"""

from __future__ import annotations

import streamlit as st

from jboss_agent.config import get_settings


settings = get_settings()

st.set_page_config(page_title="LangGraph JBoss Agent", page_icon="🧭", layout="centered")
st.title("LangGraph JBoss Incident Response Agent")
st.subheader("STEP 0–2 — Environment / Core / LLM Routing")
st.success("Environment ready. STEP 1 and STEP 2 graphs are implemented.")

st.markdown(
    """
The operational dashboard is intentionally deferred until STEP 11.
For now, run the learning graphs from the terminal:

```bash
make step1
make step2
make step2 SCENARIO=normal
```

See `docs/STEP1_STEP2_GUIDE.md` for the State / Node / Edge comparison.
"""
)

st.write("**Server ID:**", settings.server_id)
st.write("**JBoss mode:**", settings.jboss_mode)
st.write("**Gemini model:**", settings.gemini_model)
st.write("**GOOGLE_API_KEY configured:**", "Yes" if settings.has_google_api_key else "No")
st.write("**Teams dry-run:**", settings.teams_dry_run)
