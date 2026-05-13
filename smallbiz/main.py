import streamlit as st
import time
from dotenv import load_dotenv

from chat_history import ensure_chat_sessions, get_chat, summarize_prompt

# Load .env so pages and services can read API keys / SMTP creds
load_dotenv()

# --- Page Config ---
st.set_page_config(page_title="SmallBiz", page_icon="✨", layout="wide")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_agent" not in st.session_state:
    st.session_state.active_agent = "Genel Asistan"

ensure_chat_sessions()

if not st.session_state.chat_sessions:
    initial_chat = {
        "id": f"chat_{int(time.time())}",
        "title": "Genel Asistan",
        "messages": st.session_state.messages,
        "agent": st.session_state.active_agent,
        "source": "main",
        "updated_at": time.time(),
    }
    st.session_state.chat_sessions = [initial_chat]

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]
elif get_chat(st.session_state.active_chat_id) is None:
    st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]


def _get_chat(chat_id: str):
    return get_chat(chat_id)


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
    return summarize_prompt(prompt)


_sync_active_chat(st.session_state.active_chat_id)

agents = [
    "Genel Asistan",
    "Stok Yöneticisi",
    "Sipariş Takipçisi",
    "İş Akışı Yöneticisi",
    "Veri Analisti",
    "Analitik Asistanı",
    "Metin Yazarı",
]

# --- Sidebar (Gemini Style) ---
with st.sidebar:

    if st.button("＋ Yeni Sohbet", use_container_width=True):
        _create_chat(st.session_state.active_agent, title="Yeni Sohbet")
        st.rerun()

    # Redirect to dashboard page
    if st.button("📊 Kontrol Paneli", use_container_width=True, type="primary"):
        st.switch_page("pages/dashboard.py")

    # Redirect to order tracking page
    if st.button("📦 Siparişler", use_container_width=True, type="primary"):
        st.switch_page("pages/order_inventory.py")

    if st.button("📦 Stoklar", use_container_width=True, type="primary"):
        st.switch_page("pages/stock_agent.py")

    if st.button("🧭 Görevler", use_container_width=True, type="primary"):
        st.switch_page("pages/workflow_manager.py")

    st.divider()

    # 2. Chat History
    st.caption("Eski Sohbetler")
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

# --- Main Chat Area ---

# Empty State Greeting
if not st.session_state.messages:
    st.markdown(
        f"<h1 style='text-align: center; color: #888;'>Merhaba, ben {st.session_state.active_agent}</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h3 style='text-align: center; color: #bbb;'>Bugün size nasıl yardımcı olabilirim?</h3>",
        unsafe_allow_html=True
    )

    st.write("")

# Display Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.write("")

# Chat Input
if prompt := st.chat_input(f"{st.session_state.active_agent}'a mesaj gönder..."):

    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})

    current_chat = _get_chat(st.session_state.active_chat_id)
    if current_chat is not None:
        if current_chat["title"] in {"Yeni Sohbet", current_chat["agent"]}:
            current_chat["title"] = _summarize_prompt(prompt)
        current_chat["updated_at"] = time.time()

    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):

        message_placeholder = st.empty()

        mock_response = (
            f"**[{st.session_state.active_agent}]** "
            f"Talebinizi işliyorum: *'{prompt}'*. "
            f"Uzmanlık alanıma dayanarak size yardımcı olmaya hazırım!"
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