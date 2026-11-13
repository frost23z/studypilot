"""Helpers for calling the StudyPilot API from the Streamlit pages."""

import os
from typing import Any
from urllib.parse import quote

import httpx
import streamlit as st

API_URL = os.environ.get("STUDYPILOT_API_URL", "http://localhost:8000")
# Links are opened by the browser, which may reach the API at another address than this server.
PUBLIC_API_URL = os.environ.get("STUDYPILOT_PUBLIC_API_URL", API_URL)


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


def source_label(source: dict) -> str:
    """How a cited file is named on the page, for example 'AI Agents.pdf, p. 4'."""
    return f"{source['file']}, p. {source['page']}" if source.get("page") else source["file"]


def source_url(source: dict) -> str:
    """The address that shows the cited file. A PDF opens at the cited page."""
    url = f"{PUBLIC_API_URL}/documents/{quote(source['file'], safe='')}"
    return f"{url}#page={source['page']}" if source.get("page") else url
