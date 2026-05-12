import streamlit as st
import time
from dotenv import load_dotenv

# Load .env so pages and services can read API keys / SMTP creds
load_dotenv()

# --- Page Config ---
st.set_page_config(page_title="Gemini-Style Interface", page_icon="✨", layout="wide")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_agent" not in st.session_state:
    st.session_state.active_agent = "General Assistant"

if "chat_sessions" not in st.session_state:
    initial_chat = {
        "id": f"chat_{int(time.time())}",
        "title": "General Assistant",
        "messages": st.session_state.messages,
        "agent": st.session_state.active_agent,
        "updated_at": time.time(),
    }
    st.session_state.chat_sessions = [initial_chat]

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]


def _get_chat(chat_id: str):
    for chat in st.session_state.chat_sessions:
        if chat["id"] == chat_id:
            return chat
    return None


def _sync_active_chat(chat_id: str):
    chat = _get_chat(chat_id)
    if chat is None:
        return

    st.session_state.active_chat_id = chat_id
    st.session_state.active_agent = chat["agent"]
    st.session_state.messages = chat["messages"]


def _create_chat(agent_name: str, title: str | None = None):
    chat = {
        "id": f"chat_{len(st.session_state.chat_sessions) + 1}_{int(time.time())}",
        "title": title or agent_name,
        "messages": [],
        "agent": agent_name,
        "updated_at": time.time(),
    }
    st.session_state.chat_sessions.insert(0, chat)
    _sync_active_chat(chat["id"])


def _summarize_prompt(prompt: str) -> str:
    cleaned = " ".join(prompt.strip().split())
    if not cleaned:
        return "New Chat"
    if len(cleaned) > 36:
        return cleaned[:36].rstrip() + "..."
    return cleaned


_sync_active_chat(st.session_state.active_chat_id)

agents = [
    "General Assistant",
    "Stock Manager",
    "Order Tracker",
    "Workflow Manager",
    "Data Analyst",
    "Analytics Agent",
    "Copywriter",
]

# --- Sidebar (Gemini Style) ---
with st.sidebar:

    if st.button("＋ New Chat", use_container_width=True):
        _create_chat(st.session_state.active_agent, title="New Chat")
        st.rerun()

    # Redirect to dashboard page
    if st.button("📊 Dashboard", use_container_width=True, type="primary"):
        st.switch_page("pages/dashboard.py")

    # Redirect to order tracking page
    if st.button("📦 Orders", use_container_width=True, type="primary"):
        st.switch_page("pages/order_inventory.py")

    if st.button("🧭 Workflow", use_container_width=True, type="primary"):
        st.switch_page("pages/workflow_manager.py")

    st.divider()

    # 2. Chat History
    st.caption("Recent")
    recent_sessions = sorted(
        st.session_state.chat_sessions,
        key=lambda item: item["updated_at"],
        reverse=True,
    )

    for chat in recent_sessions[:5]:
        is_active = chat["id"] == st.session_state.active_chat_id
        button_type = "primary" if is_active else "secondary"
        if st.button(
            f"💬 {chat['title']}",
            use_container_width=True,
            key=f"hist_{chat['id']}",
            type=button_type,
        ):
            _sync_active_chat(chat["id"])
            st.rerun()

    st.divider()

    # 3. Agents
    st.caption("Agents")
    for agent in agents:
        icon = "✨" if agent == st.session_state.active_agent else "🤖"

        if st.button(f"{icon} {agent}", use_container_width=True, key=f"sidebar_{agent}"):
            _create_chat(agent)
            st.rerun()

# --- Main Chat Area ---

# Empty State Greeting
if not st.session_state.messages:
    st.markdown(
        f"<h1 style='text-align: center; color: #888;'>Hello, I'm your {st.session_state.active_agent}</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h3 style='text-align: center; color: #bbb;'>How can I help you today?</h3>",
        unsafe_allow_html=True
    )

    st.write("")

# Display Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.write("")

# Chat Input
if prompt := st.chat_input(f"Message {st.session_state.active_agent}..."):

    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})

    current_chat = _get_chat(st.session_state.active_chat_id)
    if current_chat is not None:
        if current_chat["title"] in {"New Chat", current_chat["agent"]}:
            current_chat["title"] = _summarize_prompt(prompt)
        current_chat["updated_at"] = time.time()

    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):

        message_placeholder = st.empty()

        mock_response = (
            f"**[{st.session_state.active_agent}]** "
            f"I'm processing your request: *'{prompt}'*. "
            f"I am ready to assist you based on my specialized training!"
        )

        full_response = ""

        for chunk in mock_response.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")

        message_placeholder.markdown(full_response)

    # Save response
    st.session_state.messages.append(
        {"role": "assistant", "content": full_response}
    )

    if current_chat is not None:
        current_chat["updated_at"] = time.time()