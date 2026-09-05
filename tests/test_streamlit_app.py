import importlib


def test_streamlit_app_imports() -> None:
    module = importlib.import_module("jboss_agent.ui.streamlit_app")
    assert module.settings.server_id
