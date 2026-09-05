"""Small learning status page through STEP 5.

The operational dashboard remains intentionally deferred until STEP 11.
"""

from __future__ import annotations

import streamlit as st

from jboss_agent.config import get_settings


settings = get_settings()

st.set_page_config(page_title="LangGraph JBoss Agent", page_icon="🧭", layout="centered")
st.title("LangGraph JBoss Incident Response Agent")
st.subheader("STEP 0–5 — Core / Routing / Cursor / Local Tool / MCP")
st.success("Learning implementation is complete through STEP 5.")

st.markdown(
    """
The operational dashboard is intentionally deferred until STEP 11.
For now, run each learning step from the terminal:

```bash
make step1
make step2
make step3
make step4
make step5
```

- `docs/STEP1_STEP2_GUIDE.md`
- `docs/STEP3_STEP4_STEP5_GUIDE.md`
"""
)

st.write("**Server ID:**", settings.server_id)
st.write("**JBoss mode:**", settings.jboss_mode)
st.write("**Fake JBoss data dir:**", settings.fake_jboss_data_dir)
st.write("**Gemini model:**", settings.gemini_model)
st.write("**GOOGLE_API_KEY configured:**", "Yes" if settings.has_google_api_key else "No")
st.write("**Teams dry-run:**", settings.teams_dry_run)
