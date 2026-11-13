"""StudyPilot chat page. It only talks to the API, it never imports the agent.

Start the API first, then:  uv run streamlit run src/frontend/app.py
"""

import uuid

import streamlit as st

from frontend.client import call

st.set_page_config(page_title="StudyPilot", page_icon="📚")
st.title("StudyPilot")


def new_chat(thread_id: str) -> None:
    st.session_state.thread_id = thread_id
    st.session_state.messages = []
    st.session_state.pending_note = None
    st.session_state.loaded_thread = None  # load this thread's saved messages
    st.query_params["thread"] = thread_id  # a page refresh keeps the same chat


# ---- Sidebar: who is chatting, new chat, remembered facts, saved notes ----

with st.sidebar:
    name = st.text_input("Your name", value=st.query_params.get("user", "")).strip().lower()
    if name:
        st.query_params["user"] = name
    if st.button("New chat", disabled=not name):
        new_chat(uuid.uuid4().hex)
        st.rerun()

if not name:
    st.info("Enter your name in the sidebar to start. It keeps your memory separate.")
    st.stop()

if "thread_id" not in st.session_state:
    new_chat(st.query_params.get("thread") or uuid.uuid4().hex)

with st.sidebar:
    st.subheader("What StudyPilot remembers")
    facts = call("GET", f"/memories/{name}")
    for fact in facts or []:
        text_column, delete_column = st.columns([5, 1])
        text_column.write(fact["text"])
        if delete_column.button("✕", key=f"delete-{fact['id']}", help="Forget this"):
            call("DELETE", f"/memories/{name}/{fact['id']}")
            st.rerun()
    if facts == []:
        st.caption("Nothing yet. Tell it your level or what you are learning.")

    with st.expander("Saved notes"):
        for note in call("GET", "/notes") or []:
            st.markdown(f"**{note['title']}**")
            st.text(note["content"])

# load the saved messages the first time this chat is shown
if st.session_state.loaded_thread != st.session_state.thread_id:
    saved = call("GET", f"/chat/{st.session_state.thread_id}")
    if saved is None:
        st.stop()
    st.session_state.messages = saved["messages"]
    st.session_state.pending_note = saved["pending_note"]
    st.session_state.loaded_thread = st.session_state.thread_id

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

note = st.session_state.pending_note
if note:
    with st.chat_message("assistant"):
        st.markdown(f"Save this note?\n\n**{note['title']}**")
        st.text(note["content"])
        save_column, skip_column, _ = st.columns([1, 1, 3])
        answer = None
        if save_column.button("Save", type="primary"):
            answer = True
        if skip_column.button("Don't save"):
            answer = False
    if answer is not None:
        body = {"thread_id": st.session_state.thread_id, "approved": answer}
        with st.spinner("Working..."):
            result = call("POST", "/chat/approve", json=body)
        if result:
            st.session_state.pending_note = None
            if result["reply"]:
                st.session_state.messages.append({"role": "assistant", "text": result["reply"]})
            st.rerun()

question = st.chat_input("Ask about your course", disabled=note is not None)
if question:
    st.session_state.messages.append({"role": "user", "text": question})
    st.chat_message("user").markdown(question)
    body = {"thread_id": st.session_state.thread_id, "user_id": name, "message": question}
    with st.spinner("Thinking..."):
        result = call("POST", "/chat", json=body)
    if result is None:
        st.session_state.messages.pop()  # the question was not answered, so ask again
    else:
        st.session_state.pending_note = result["pending_note"]
        if result["reply"]:
            st.session_state.messages.append({"role": "assistant", "text": result["reply"]})
        st.rerun()
