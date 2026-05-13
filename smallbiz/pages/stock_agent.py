import json
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import database
from agents.stock_manager_agent import create_stock_manager_agent, run_stock_manager_agent
from chat_history import record_chat_exchange
import auth

load_dotenv()

# Require login
auth.require_login()

st.set_page_config(
    page_title="Stok Yöneticisi",
    page_icon="📦",
    layout="wide",
)

if "stock_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    st.session_state.stock_agent = create_stock_manager_agent(api_key) if api_key else create_stock_manager_agent("")

if "stock_messages" not in st.session_state:
    st.session_state.stock_messages = []
if "stock_agent_chat_id" not in st.session_state:
    st.session_state.stock_agent_chat_id = None
if "stock_real_email" not in st.session_state:
    st.session_state.stock_real_email = False


def _run_stock_prompt(prompt: str) -> str:
    st.session_state.stock_agent["use_real_email"] = bool(st.session_state.stock_real_email)
    st.session_state.stock_messages.append({"role": "user", "content": prompt})
    response = run_stock_manager_agent(st.session_state.stock_agent, prompt)
    st.session_state.stock_messages.append({"role": "assistant", "content": response})
    record_chat_exchange(
        session_key="stock_agent_chat_id",
        agent_name="Stok Yöneticisi Asistanı",
        prompt=prompt,
        response=response,
        title="Stok Yöneticisi Asistanı",
        source="stock_agent",
    )
    return response


with st.sidebar:
    st.title("Navigasyon")

    if st.button("💬 Sohbete Dön", use_container_width=True):
        st.switch_page("main.py")
    if st.button("📊 Kontrol Paneli", use_container_width=True):
        st.switch_page("pages/dashboard.py")
    if st.button("📦 Siparişler", use_container_width=True):
        st.switch_page("pages/order_inventory.py")
    if st.button("🧭 İş Akışı", use_container_width=True):
        st.switch_page("pages/workflow_manager.py")
    if st.button("💬 WhatsApp Destek", use_container_width=True):
        st.switch_page("pages/customer_support.py")

    st.divider()
    st.session_state.stock_real_email = st.checkbox(
        "Gerçek e-posta gönderimini etkinleştir",
        value=st.session_state.stock_real_email,
    )
    st.caption("Stok asistanı, envanter ve satış geçmişini birlikte kullanır.")

    st.divider()
    view_options_map = {
        "Stok Paneli": "dashboard",
        "Envanter": "inventory",
        "Uyarı Geçmişi": "alerts",
        "Öneriler": "recommendations",
        "Stok Asistanı": "assistant",
    }
    selected_view = st.radio("Görünüm", list(view_options_map.keys()))
    view_option = view_options_map[selected_view]

st.title("📦 Stok Yöneticisi")
st.caption("Envanteri izleyin, düşük stokları yönetin ve en çok talep gören ürünleri önceliklendirin.")

inventory = database.get_inventory()
low_stock_items = database.get_low_stock_items()
health = database.get_inventory_health()
recommendations = database.get_stock_recommendations(limit=5)
alert_history = database.get_system_email_logs("low_stock_alert")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Toplam Ürün", health["total_items"])
col2.metric("Düşük Stok", health["low_stock_items"])
col3.metric("Sıfır Stok", health["out_of_stock_items"])
col4.metric("Sağlıklı Ürün", health["healthy_items"])

st.divider()

if view_option == "dashboard":
    left, right = st.columns(2)

    with left:
        st.subheader("Düşük Stok Ürünleri")
        if low_stock_items:
            low_stock_df = pd.DataFrame(low_stock_items)[["product_name", "current_stock", "reorder_level", "notes"]]
            st.dataframe(low_stock_df, use_container_width=True, hide_index=True)
        else:
            st.success("Düşük stok ürünü yok.")

        if st.button("📧 Düşük stok uyarısı gönder", use_container_width=True, type="primary"):
            if low_stock_items:
                alert_response = _run_stock_prompt("send low stock alert")
                try:
                    alert_data = json.loads(alert_response)
                    if alert_data.get("sent"):
                        st.success(
                            f"Düşük stok uyarısı gönderildi ve {alert_data.get('created_tasks', 0)} restok görevi oluşturuldu."
                        )
                    else:
                        st.error("Düşük stok uyarısı gönderilemedi.")
                except Exception:
                    st.success("Düşük stok uyarısı işlendi.")
            else:
                st.info("Gönderilecek düşük stok ürünü yok.")

    with right:
        st.subheader("En Çok Talep Görenler")
        if recommendations:
            rec_df = pd.DataFrame(recommendations)[["product_name", "total_quantity_sold", "current_stock", "needs_restock"]]
            st.dataframe(rec_df, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz öneri yok.")

        st.subheader("Hızlı İçgörü")
        if recommendations:
            top_item = recommendations[0]
            st.info(f"En çok talep gören ürün: {top_item['product_name']} ({top_item['total_quantity_sold']} satış).")

elif view_option == "inventory":
    st.subheader("Envanter Yönetimi")

    with st.form("inventory_adjust_form"):
        product_options = [item["product_name"] for item in inventory]
        selected_product = st.selectbox("Ürün", product_options if product_options else ["Ürün yok"])
        delta = st.number_input("Stok Değişimi", value=1, step=1)
        notes = st.text_input("Not", placeholder="Restok, düzeltme, iade vb.")
        submitted = st.form_submit_button("Stoğu Güncelle", type="primary")

        if submitted and product_options:
            updated_item = database.adjust_inventory_stock(selected_product, int(delta), notes)
            if updated_item:
                st.success(f"{selected_product} stoğu güncellendi: {updated_item['current_stock']}")
            else:
                st.error("Stok güncellenemedi.")

    st.divider()

    if inventory:
        inventory_df = pd.DataFrame(inventory)[["sku", "product_name", "current_stock", "reorder_level", "unit_cost", "notes"]]
        st.dataframe(inventory_df, use_container_width=True, hide_index=True)
    else:
        st.info("Envanter bulunamadı.")

elif view_option == "alerts":
    st.subheader("Düşük Stok Uyarı Geçmişi")
    st.write("Bu görünüm, sistem e-posta log tablosundaki düşük stok bildirimlerini gösterir.")

    if alert_history:
        alerts_df = pd.DataFrame(alert_history)[["alert_type", "recipient_email", "subject", "status", "details", "sent_at"]]
        alerts_df = alerts_df.rename(
            columns={
                "alert_type": "Uyarı Türü",
                "recipient_email": "Alıcı",
                "subject": "Konu",
                "status": "Durum",
                "details": "Detay",
                "sent_at": "Gönderim Zamanı",
            }
        )
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz düşük stok uyarısı kaydı yok.")

elif view_option == "recommendations":
    st.subheader("En Çok Talep Gören Ürünler")
    st.write("Öneriler, mevcut sipariş geçmişindeki satış hacmine göre oluşturulur.")

    if recommendations:
        for item in recommendations:
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 1])
                cols[0].markdown(f"**{item['product_name']}**")
                cols[1].metric("Satış", item["total_quantity_sold"])
                cols[2].metric("Stok", item["current_stock"] if item["current_stock"] is not None else "-")
                cols[3].metric("Restok", "Evet" if item["needs_restock"] else "Hayır")
    else:
        st.info("Öneri üretilemedi.")

elif view_option == "assistant":
    st.subheader("Stok Yöneticisi Asistanı")
    st.info(
        "Envanter, düşük stok uyarıları, restok görevleri ve en çok talep gören ürünler hakkında soru sorabilirsiniz. "
        "Örnek: 'low stock items', 'most wanted products', 'Laptop +5'"
    )

    quick_col1, quick_col2, quick_col3 = st.columns(3)
    if quick_col1.button("Düşük Stoğu Göster", use_container_width=True):
        _run_stock_prompt("low stock items")
    if quick_col2.button("En Çok Talep Görenleri Göster", use_container_width=True):
        _run_stock_prompt("most wanted products")
    if quick_col3.button("Düşük Stok Uyarısı Gönder", use_container_width=True):
        _run_stock_prompt("send low stock alert")

    for message in st.session_state.stock_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Stok asistanına sorun...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)

        with st.spinner("Stok asistanı düşünüyor..."):
            response = _run_stock_prompt(user_input)

        with st.chat_message("assistant"):
            st.write(response)
