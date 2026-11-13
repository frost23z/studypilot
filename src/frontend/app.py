"""StudyPilot chat page. It only talks to the API, it never imports the agent.

Start the API first, then:  uv run streamlit run src/frontend/app.py
"""

import uuid

import streamlit as st

from frontend.client import call, source_label, source_url

st.set_page_config(page_title="StudyPilot", page_icon="📚")
st.title("StudyPilot")


def show_sources(sources: list[dict]) -> None:
    if sources:
        links = " · ".join(f"[{source_label(s)}]({source_url(s)})" for s in sources)
        st.caption(f"📄 Sources: {links}")


def show_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        show_sources(message.get("sources", []))


def add_reply(result: dict) -> None:
    if result["reply"]:
        st.session_state.messages.append(
            {"role": "assistant", "text": result["reply"], "sources": result["sources"]}
        )


def open_chat(thread_id: str) -> None:
    """Show one chat. A thread_id nobody used yet is a new, empty chat."""
    st.session_state.thread_id = thread_id
    st.session_state.messages = []
    st.session_state.pending_note = None
    st.session_state.loaded_thread = None  # load this thread's saved messages
    st.query_params["thread"] = thread_id  # a page refresh keeps the same chat


with st.sidebar:
    name = st.text_input("Your name", value=st.query_params.get("user", "")).strip().lower()
    if name:
        st.query_params["user"] = name
        st.session_state.user = name  # the Memories page starts from this name

if not name:
    st.info("Enter your name in the sidebar to start. It keeps your memory separate.")
    st.stop()

if "thread_id" not in st.session_state:
    open_chat(st.query_params.get("thread") or uuid.uuid4().hex)
    st.session_state.chat_user = name
elif st.session_state.chat_user != name:
    open_chat(uuid.uuid4().hex)  # another person's chat must not stay open
    st.session_state.chat_user = name

with st.sidebar:
    if st.button("New chat", icon=":material/add:", width="stretch"):
        open_chat(uuid.uuid4().hex)
        st.rerun()

    st.subheader("Chats")
    current = st.session_state.thread_id
    threads = call("GET", f"/threads/{name}") or []
    if current not in {thread["thread_id"] for thread in threads}:
        # A new chat has no message yet, so the server does not list it. Show it anyway.
        threads = [{"thread_id": current, "title": "New chat"}, *threads]
    for thread in threads:
        is_open = thread["thread_id"] == current
        clicked = st.button(
            thread["title"],
            key=f"thread-{thread['thread_id']}",
            type="primary" if is_open else "secondary",
            width="stretch",
        )
        if clicked and not is_open:
            open_chat(thread["thread_id"])
            st.rerun()

# load the saved messages the first time this chat is shown
if st.session_state.loaded_thread != st.session_state.thread_id:
    saved = call("GET", f"/chat/{st.session_state.thread_id}")
    if saved is None:
        st.stop()
    st.session_state.messages = saved["messages"]
    st.session_state.pending_note = saved["pending_note"]
    st.session_state.loaded_thread = st.session_state.thread_id

for message in st.session_state.messages:
    show_message(message)

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
            add_reply(result)
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
        add_reply(result)
        st.rerun()
