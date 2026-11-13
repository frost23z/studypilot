"""Every note StudyPilot has saved, newest first. Notes are saved from the chat."""

from datetime import datetime

import streamlit as st

from frontend.client import call

st.set_page_config(page_title="Notes · StudyPilot", page_icon="📝")
st.title("Saved notes")


def when(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M UTC")


notes = call("GET", "/notes")
if notes is None:
    st.stop()
if not notes:
    st.info("No notes yet. Ask StudyPilot in the chat to save one.")
    st.stop()

st.caption(f"{len(notes)} saved, newest first")
for note in notes:
    with st.container(border=True):
        st.subheader(note["title"])
        st.markdown(note["content"])
        st.caption(f"Saved {when(note['created_at'])}")
