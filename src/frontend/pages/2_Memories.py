"""The facts StudyPilot remembers about one person, kept across chats."""

import streamlit as st

from frontend.client import call

st.set_page_config(page_title="Memories · StudyPilot", page_icon="🧠")
st.title("What StudyPilot remembers")

start = st.session_state.get("user") or st.query_params.get("user", "")
name = st.text_input("Your name", value=start).strip().lower()
if not name:
    st.info("Enter your name to see what is remembered. Memory is kept per name.")
    st.stop()
st.session_state.user = name

facts = call("GET", f"/memories/{name}")
if facts is None:
    st.stop()
if not facts:
    st.info("Nothing yet. Tell StudyPilot your level or what you are learning.")
    st.stop()

st.caption(f"{len(facts)} remembered")
for fact in facts:
    text_column, delete_column = st.columns([8, 1], vertical_alignment="center")
    text_column.write(fact["text"])
    if delete_column.button("✕", key=f"delete-{fact['id']}", help="Forget this"):
        call("DELETE", f"/memories/{name}/{fact['id']}")
        st.rerun()
