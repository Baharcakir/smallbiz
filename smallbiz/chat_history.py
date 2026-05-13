import time

import streamlit as st


DEFAULT_CHAT_TITLE = "New Chat"


def summarize_prompt(prompt: str, max_length: int = 36) -> str:
    cleaned = " ".join((prompt or "").strip().split())
    if not cleaned:
        return DEFAULT_CHAT_TITLE
    if len(cleaned) > max_length:
        return cleaned[:max_length].rstrip() + "..."
    return cleaned


def ensure_chat_sessions():
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    return st.session_state.chat_sessions


def get_chat(chat_id: str | None):
    if not chat_id:
        return None

    ensure_chat_sessions()
    for chat in st.session_state.chat_sessions:
        if chat["id"] == chat_id:
            return chat
    return None


def _create_chat(agent_name: str, title: str | None = None, source: str | None = None):
    ensure_chat_sessions()
    chat = {
        "id": f"chat_{len(st.session_state.chat_sessions) + 1}_{int(time.time())}",
        "title": title or agent_name,
        "messages": [],
        "agent": agent_name,
        "source": source or agent_name,
        "updated_at": time.time(),
    }
    st.session_state.chat_sessions.insert(0, chat)
    return chat


def ensure_chat_thread(session_key: str, agent_name: str, title: str | None = None, source: str | None = None):
    ensure_chat_sessions()
    chat = get_chat(st.session_state.get(session_key))
    if chat is None:
        chat = _create_chat(agent_name=agent_name, title=title or agent_name, source=source)
        st.session_state[session_key] = chat["id"]
    return chat


def record_chat_exchange(
    session_key: str,
    agent_name: str,
    prompt: str,
    response: str,
    *,
    title: str | None = None,
    source: str | None = None,
):
    chat = ensure_chat_thread(session_key=session_key, agent_name=agent_name, title=title, source=source)

    if chat["title"] in {agent_name, DEFAULT_CHAT_TITLE} or chat["title"] == (title or ""):
        chat["title"] = summarize_prompt(prompt)

    chat["messages"].append({"role": "user", "content": prompt})
    chat["messages"].append({"role": "assistant", "content": response})
    chat["updated_at"] = time.time()
    return chat


def get_recent_chats(limit: int = 5):
    ensure_chat_sessions()
    return sorted(
        st.session_state.chat_sessions,
        key=lambda item: item["updated_at"],
        reverse=True,
    )[:limit]
