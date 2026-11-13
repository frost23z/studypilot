"""Helpers for calling the StudyPilot API from the Streamlit pages."""

import os
from typing import Any

import httpx
import streamlit as st

API_URL = os.environ.get("STUDYPILOT_API_URL", "http://localhost:8000")


def call(method: str, path: str, **kwargs) -> Any:
    """Call the API. Returns the JSON answer, or None after showing the error."""
    try:
        response = httpx.request(method, API_URL + path, timeout=120, **kwargs)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        st.error(f"The server refused the request: {error.response.text}")
        return None
    except httpx.HTTPError as error:
        st.error(f"Could not reach the server at {API_URL}. Is it running? ({error})")
        return None
    return response.json() if response.content else {}
