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
        "allow_delete": False,
    }
    st.session_state.chat_sessions = [initial_chat]

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]
elif get_chat(st.session_state.active_chat_id) is None:
    st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]

# Varsayılan Genel Asistan sohbeti: silinemez (eski oturumlar için)
for _c in st.session_state.chat_sessions:
    if _c.get("allow_delete") is False:
        continue
    if (
        _c.get("agent") == "Genel Asistan"
        and _c.get("title") == "Genel Asistan"
        and _c.get("source") == "main"
    ):
        _c["allow_delete"] = False


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
        "allow_delete": True,
    }
    st.session_state.chat_sessions.insert(0, chat)
    _sync_active_chat(chat["id"])


def _summarize_prompt(prompt: str) -> str:
    return summarize_prompt(prompt)


def _chat_can_delete(chat: dict | None) -> bool:
    if not chat:
        return False
    if chat.get("allow_delete") is False:
        return False
    if chat.get("agent") == "Genel Asistan" and chat.get("title") == "Genel Asistan":
        return False
    return True


def _short_title(title: str, max_len: int = 20) -> str:
    t = (title or "").strip()
    if len(t) <= max_len:
        return t or "Sohbet"
    return t[: max_len - 1].rstrip() + "…"


def _delete_chats_by_ids(ids: set[str]) -> None:
    if not ids:
        return
    sessions = st.session_state.chat_sessions
    removable = {i for i in ids if _chat_can_delete(_get_chat(i))}
    if not removable:
        return
    st.session_state.chat_sessions = [c for c in sessions if c["id"] not in removable]
    if not st.session_state.chat_sessions:
        st.session_state.chat_sessions = [
            {
                "id": f"chat_{int(time.time())}",
                "title": "Genel Asistan",
                "messages": [],
                "agent": "Genel Asistan",
                "source": "main",
                "updated_at": time.time(),
                "allow_delete": False,
            }
        ]
        st.session_state.active_agent = "Genel Asistan"
    if st.session_state.active_chat_id in removable:
        st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]
        _sync_active_chat(st.session_state.active_chat_id)


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

    if st.button("💬 WhatsApp Destek", use_container_width=True, type="primary"):
        st.switch_page("pages/customer_support.py")

    st.divider()

    st.markdown(
        """
<style>
div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) button {
    color: #c62828 !important;
    border-color: #ffcdd2 !important;
    background: transparent !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    min-height: 1.35rem !important;
    padding: 0 0.28rem !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="margin:0 0 0.35rem 0;font-size:0.72rem;color:#6b6b6b;">Eski sohbetler</p>',
        unsafe_allow_html=True,
    )
    recent_sessions = sorted(
        st.session_state.chat_sessions,
        key=lambda item: item["updated_at"],
        reverse=True,
    )
    shown = recent_sessions[:5]

    for chat in shown:
        is_active = chat["id"] == st.session_state.active_chat_id
        label = ("· " if is_active else "") + _short_title(chat["title"])
        if _chat_can_delete(chat):
            col_open, col_del = st.columns([11, 1], gap="small")
            with col_open:
                if st.button(
                    label,
                    use_container_width=True,
                    key=f"hist_{chat['id']}",
                    type="secondary",
                ):
                    _sync_active_chat(chat["id"])
                    st.rerun()
            with col_del:
                if st.button(
                    "×",
                    key=f"del_{chat['id']}",
                    help="Sil",
                ):
                    _delete_chats_by_ids({chat["id"]})
                    st.rerun()
        else:
            if st.button(
                label,
                use_container_width=True,
                key=f"hist_{chat['id']}",
                type="secondary",
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
