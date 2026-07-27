"""
Session-state-backed auth helpers. Streamlit re-runs the whole script on
every interaction, so login state has to live in st.session_state rather
than component state — this keeps that logic in one place instead of
duplicated across every page.
"""
from __future__ import annotations

import streamlit as st

from lib import api_client
from lib.api_client import ApiError


def is_logged_in() -> bool:
    return "token" in st.session_state and "user" in st.session_state


def do_login(email: str, password: str) -> tuple[bool, str | None]:
    try:
        api_client.login(email, password)
        user = api_client.get_current_user()
        st.session_state["user"] = user
        return True, None
    except ApiError as e:
        return False, e.detail


def do_logout():
    for key in ("token", "user"):
        st.session_state.pop(key, None)


def require_login():
    """Call at the top of every page. Stops execution with a friendly
    message if the user isn't logged in, instead of letting API calls
    fail with confusing errors further down the page."""
    if not is_logged_in():
        st.warning("Please log in from the main **AirGuard AI** page first.")
        st.stop()


def current_user() -> dict:
    return st.session_state.get("user", {})
