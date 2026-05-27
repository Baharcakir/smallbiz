import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import auth
from agents.customer_support_agent import (
    add_whatsapp_message,
    create_customer_support_agent,
    delete_support_document,
    get_support_snapshot,
    list_support_documents,
    load_whatsapp_conversations,
    run_customer_support_agent,
    save_support_document,
    save_uploaded_support_document,
)
from chat_history import record_chat_exchange


load_dotenv()

st.set_page_config(
    page_title="WhatsApp Destek",
    page_icon="💬",
    layout="wide",
)
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)
auth.require_login()


if "customer_support_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    st.session_state.customer_support_agent = create_customer_support_agent(api_key)

if "support_messages" not in st.session_state:
    st.session_state.support_messages = []

if "support_agent_chat_id" not in st.session_state:
    st.session_state.support_agent_chat_id = None


def _run_support_prompt(prompt: str) -> dict:
    st.session_state.support_messages.append({"role": "user", "content": prompt})
    result = run_customer_support_agent(st.session_state.customer_support_agent, prompt)
    st.session_state.support_messages.append({"role": "assistant", "content": result["answer"]})
    record_chat_exchange(
        session_key="support_agent_chat_id",
        agent_name="WhatsApp Destek Asistanı",
        prompt=prompt,
        response=result["answer"],
        title="WhatsApp Destek Asistanı",
        source="customer_support",
    )
    return result


def _conversation_rows(conversations: list[dict]) -> list[dict]:
    rows = []
    for conversation in conversations:
        messages = conversation.get("messages", [])
        last_message = messages[-1]["message"] if messages else ""
        rows.append(
            {
                "Konusma": conversation.get("conversation_id", ""),
                "Musteri": conversation.get("customer_name", ""),
                "Telefon": conversation.get("customer_phone", ""),
                "Durum": conversation.get("status", ""),
                "Son Mesaj": last_message,
                "Son Aktivite": conversation.get("last_message_at", ""),
            }
        )
    return rows


with st.sidebar:
    st.title("Navigasyon")

    if st.button("💬 Sohbete Dön", use_container_width=True):
        st.switch_page("main.py")
    if st.button("📊 Kontrol Paneli", use_container_width=True):
        st.switch_page("pages/dashboard.py")
    if st.button("📦 Sipariş Yönetimi", use_container_width=True):
        st.switch_page("pages/order_inventory.py")
    if st.button("📦 Stok Yönetimi", use_container_width=True):
        st.switch_page("pages/stock_agent.py")
    if st.button("📈 Analizler", use_container_width=True):
        st.switch_page("pages/analytics.py")
    if st.button("🧭 İş Akışı", use_container_width=True):
        st.switch_page("pages/workflow_manager.py")

    st.divider()
    selected_view = st.radio(
        "Gorunum",
        ["Agent Test", "Bilgi Kaynaklari", "WhatsApp Messages", "Entegrasyon"],
    )


st.title("💬 WhatsApp Müşteri Destek")
st.caption("Şirket dosyalarına dayalı destek ajanını test edin ve WhatsApp konuşmalarını izleyin.")

snapshot = get_support_snapshot()
metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Bilgi Dosyası", snapshot["documents"])
metric2.metric("RAG Parçası", snapshot["chunks"])
metric3.metric("Konuşma", snapshot["conversations"])
metric4.metric("İnsan Bekleyen", snapshot["needs_human"])

st.divider()

if selected_view == "Agent Test":
    st.subheader("Agent Test")
    st.write("Müşteri mesajını simüle edin. Ajan yalnızca yüklenen şirket dosyalarındaki bilgiyle cevap verir.")

    quick1, quick2, quick3 = st.columns(3)
    if quick1.button("İade süresi kaç gün?", use_container_width=True):
        _run_support_prompt("İade süresi kaç gün?")
    if quick2.button("Kargo ne zaman gelir?", use_container_width=True):
        _run_support_prompt("Kargo ne zaman gelir?")
    if quick3.button("Yanlış ürün geldi", use_container_width=True):
        _run_support_prompt("Yanlış ürün geldi, ne yapmalıyım?")

    for message in st.session_state.support_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Destek ajanına test mesajı yazın...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.spinner("Destek ajanı yanıt hazırlıyor..."):
            result = _run_support_prompt(user_input)
        with st.chat_message("assistant"):
            st.write(result["answer"])
            if result["sources"]:
                with st.expander("Kullanılan kaynaklar"):
                    st.dataframe(pd.DataFrame(result["sources"]), use_container_width=True, hide_index=True)

elif selected_view == "Bilgi Kaynakları":
    st.subheader("Bilgi Kaynakları")
    st.write("FAQ, politika ve ürün bilgisi dosyalarını `.md`, `.txt`, `.pdf`, `.doc` veya `.docx` olarak ekleyin.")

    uploaded_file = st.file_uploader("Dosya yükle", type=["md", "txt", "pdf", "doc", "docx"])
    if uploaded_file is not None:
        result = save_uploaded_support_document(uploaded_file.name, uploaded_file.read())
        if result["ok"]:
            st.success(f"{uploaded_file.name} eklendi ve indekslenebilir metne çevrildi.")
            st.rerun()
        else:
            st.error(result["error"])

    with st.form("manual_support_doc"):
        filename = st.text_input("Dosya adı", value="company_policy.md")
        content = st.text_area("İçerik", height=180, placeholder="Şirket iade, kargo veya ürün bilgilerini buraya yazın.")
        submitted = st.form_submit_button("Kaydet", type="primary")
        if submitted:
            if content.strip():
                save_support_document(filename, content)
                st.success(f"{filename} kaydedildi.")
                st.rerun()
            else:
                st.warning("İçerik boş olamaz.")

    documents = list_support_documents()
    if documents:
        docs_df = pd.DataFrame(documents)[["filename", "characters", "chunks", "updated_at"]]
        st.dataframe(docs_df, use_container_width=True, hide_index=True)

        delete_target = st.selectbox("Silinecek dosya", [doc["filename"] for doc in documents])
        if st.button("Seçili dosyayı sil"):
            if delete_support_document(delete_target):
                st.success(f"{delete_target} silindi.")
                st.rerun()
    else:
        st.info("Henüz bilgi kaynağı yok.")

elif selected_view == "WhatsApp Messages":
    st.subheader("WhatsApp Messages")
    st.write("Bu görünüm şimdilik lokal JSON üzerinden mock konuşmaları gösterir; gerçek WhatsApp webhook sonraki aşamada bağlanabilir.")

    conversations = load_whatsapp_conversations()
    if conversations:
        st.dataframe(pd.DataFrame(_conversation_rows(conversations)), use_container_width=True, hide_index=True)

        selected_id = st.selectbox("Konuşma seç", [item["conversation_id"] for item in conversations])
        selected_conversation = next(item for item in conversations if item["conversation_id"] == selected_id)

        st.markdown(f"**{selected_conversation.get('customer_name', '')}** · {selected_conversation.get('customer_phone', '')}")
        for message in selected_conversation.get("messages", []):
            role = "assistant" if message.get("sender") == "agent" else "user"
            with st.chat_message(role):
                st.caption(message.get("created_at", ""))
                st.write(message.get("message", ""))

        with st.form("simulate_whatsapp_message"):
            incoming_message = st.text_input("Yeni müşteri mesajı simüle et")
            submitted = st.form_submit_button("Mesajı işle", type="primary")
            if submitted and incoming_message.strip():
                add_whatsapp_message(
                    selected_id,
                    selected_conversation.get("customer_name", ""),
                    selected_conversation.get("customer_phone", ""),
                    "customer",
                    incoming_message,
                    status="bot_active",
                )
                result = run_customer_support_agent(st.session_state.customer_support_agent, incoming_message)
                add_whatsapp_message(
                    selected_id,
                    selected_conversation.get("customer_name", ""),
                    selected_conversation.get("customer_phone", ""),
                    "agent",
                    result["answer"],
                    status="bot_active",
                )
                st.success("Mesaj işlendi ve ajan yanıtı konuşmaya eklendi.")
                st.rerun()
    else:
        st.info("Henüz WhatsApp konuşması yok.")

elif selected_view == "Entegrasyon":
    st.subheader("WhatsApp Entegrasyonu")
    st.write("WhatsApp Cloud API mesajlarını canlı almak için FastAPI webhook servisini ngrok ile public hale getirin.")

    ngrok_url = st.text_input("ngrok URL", value="https://your-ngrok-url.ngrok-free.app")
    webhook_url = f"{ngrok_url.rstrip('/')}/webhook"
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "smallbiz_support_verify")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

    st.code(
        f"""Webhook URL: {webhook_url}
Verify Token: {verify_token}
Phone Number ID: {phone_number_id or '<META_PHONE_NUMBER_ID>'}
Access Token: {'set' if access_token else '<META_ACCESS_TOKEN>'}
""",
        language="text",
    )

    st.write("Lokal servis komutları:")
    st.code(
        """.venv311/bin/python -m uvicorn api.whatsapp_webhook:app --host 0.0.0.0 --port 8000
ngrok http 8000""",
        language="bash",
    )

    st.write("Lokal simülasyon testi:")
    st.code(
        """curl -X POST http://127.0.0.1:8000/simulate \\
  -H 'Content-Type: application/json' \\
  -d '{"from_phone":"+905551112233","customer_name":"Demo Musteri","message":"Iade suresi kac gun?"}'""",
        language="bash",
    )

    st.info(
        "Meta Developer Console'da Webhooks alanına URL'yi girin, Verify Token ile doğrulayın ve messages event'ine subscribe olun."
    )
