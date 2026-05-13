import streamlit as st
import pandas as pd
import json
from datetime import datetime
import database
import email_service
from agents.order_agent import create_order_agent, run_order_agent
from chat_history import record_chat_exchange
import os
from dotenv import load_dotenv

# Load .env for API keys and SMTP credentials
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Sipariş Takibi",
    page_icon="📦",
    layout="wide"
)

# Durum çevirileri (Arka plan işleyişini bozmamak için UI gösteriminde kullanılır)
STATUS_MAP = {
    "pending": "Bekleyen",
    "processing": "İşleniyor",
    "shipped": "Kargolandı",
    "delivered": "Teslim Edildi"
}

# --- Initialize Session State ---
if "order_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            st.session_state.order_agent = create_order_agent(api_key)
        except Exception as e:
            st.session_state.order_agent = None
            st.warning(f"⚠️ Sipariş Asistanı başlatılamadı: {str(e)}")
    else:
        st.session_state.order_agent = None
        st.warning("⚠️ GOOGLE_API_KEY ayarlanmamış. Asistan özellikleri devre dışı bırakılacak.")

# --- Sidebar ---
with st.sidebar:
    st.title("Navigasyon")
    
    if st.button("💬 Sohbete Dön", use_container_width=True):
        st.switch_page("main.py")
    
    st.divider()
    
    # View options
    view_option = st.radio(
        "Görünüm Seç",
        ["Kontrol Paneli", "Tüm Siparişler", "Sipariş Detayları", "Sipariş Asistanı"]
    )
    
    # Email sending mode
    if "real_email" not in st.session_state:
        st.session_state.real_email = False

    st.session_state.real_email = st.checkbox(
        "Gerçek e-posta gönderimini etkinleştir (.env dosyasında SENDER_EMAIL ve SENDER_PASSWORD gerektirir)",
        value=st.session_state.real_email
    )

# --- Main Content ---
st.title("📦 Sipariş Takip Sistemi")

if view_option == "Kontrol Paneli":
    st.header("Kontrol Paneli")
    
    # Get statistics
    all_orders = database.get_all_orders()
    
    if all_orders:
        col1, col2, col3, col4 = st.columns(4)
        
        total_orders = len(all_orders)
        total_revenue = sum(order["total_amount"] for order in all_orders)
        delivered_count = len([o for o in all_orders if o["status"] == "delivered"])
        pending_count = len([o for o in all_orders if o["status"] == "pending"])
        
        col1.metric("Toplam Sipariş", total_orders)
        col2.metric("Toplam Gelir", f"${total_revenue:.2f}")
        col3.metric("Teslim Edilen", delivered_count)
        col4.metric("Bekleyen", pending_count)
        
        st.divider()
        
        # Status breakdown
        status_breakdown = {}
        for order in all_orders:
            # Durumları Türkçeye çevirerek grupla
            status = STATUS_MAP.get(order["status"], order["status"])
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Duruma Göre Siparişler")
            status_df = pd.DataFrame(
                list(status_breakdown.items()),
                columns=["Durum", "Sayı"]
            )
            st.bar_chart(status_df.set_index("Durum"))
        
        with col2:
            st.subheader("Son Siparişler")
            recent_orders = all_orders[:5]
            recent_df = pd.DataFrame([
                {
                    "Sipariş ID": o["order_id"],
                    "Müşteri": o["customer_name"],
                    "Tutar": f"${o['total_amount']:.2f}",
                    "Durum": STATUS_MAP.get(o["status"], o["status"]),
                    "Tarih": o["created_at"]
                }
                for o in recent_orders
            ])
            st.dataframe(recent_df, use_container_width=True)
    else:
        st.info("Sistemde sipariş bulunamadı")

elif view_option == "Tüm Siparişler":
    st.header("Tüm Siparişler")
    
    # Filter options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Arayüz için Türkçe, arka plan için İngilizce durumlar
        filter_options = {"Tümü": "All", "Bekleyen": "pending", "İşleniyor": "processing", "Kargolandı": "shipped", "Teslim Edildi": "delivered"}
        selected_filter_tr = st.selectbox(
            "Duruma Göre Filtrele",
            list(filter_options.keys())
        )
        status_filter = filter_options[selected_filter_tr]
    
    with col2:
        sort_option = st.selectbox(
            "Sıralama",
            ["Yeniden Eskiye", "Eskiden Yeniye", "En Yüksek Tutar", "En Düşük Tutar"]
        )
    
    # Get orders
    if status_filter == "All":
        orders = database.get_all_orders()
    else:
        orders = database.get_orders_by_status(status_filter)
    
    # Sort
    if sort_option == "Yeniden Eskiye":
        orders.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_option == "Eskiden Yeniye":
        orders.sort(key=lambda x: x["created_at"])
    elif sort_option == "En Yüksek Tutar":
        orders.sort(key=lambda x: x["total_amount"], reverse=True)
    else:  # En Düşük Tutar
        orders.sort(key=lambda x: x["total_amount"])
    
    # Display orders
    if orders:
        orders_data = []
        for order in orders:
            items = json.loads(order["items"])
            items_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in items])
            
            orders_data.append({
                "Sipariş ID": order["order_id"],
                "Müşteri": order["customer_name"],
                "E-posta": order["customer_email"],
                "Ürünler": items_str,
                "Tutar": f"${order['total_amount']:.2f}",
                "Durum": STATUS_MAP.get(order["status"], order["status"]),
                "Tarih": order["created_at"]
            })
        
        df = pd.DataFrame(orders_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sipariş bulunamadı")

elif view_option == "Sipariş Detayları":
    st.header("Sipariş Detayları")
    
    order_id = st.text_input("Sipariş ID Girin", placeholder="Örn: ORD-001")
    
    if order_id:
        order = database.get_order(order_id)
        
        if order:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(f"Sipariş {order_id}")
                
                # Order info
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.write(f"**Müşteri Adı:** {order['customer_name']}")
                    st.write(f"**Müşteri E-posta:** {order['customer_email']}")
                    st.write(f"**Oluşturulma:** {order['created_at']}")
                
                with info_col2:
                    st.write(f"**Durum:** {STATUS_MAP.get(order['status'], order['status']).upper()}")
                    st.write(f"**Güncellenme:** {order['updated_at']}")
                    st.write(f"**Toplam Tutar:** ${order['total_amount']:.2f}")
                
                if order['notes']:
                    st.write(f"**Notlar:** {order['notes']}")
                
                st.divider()
                
                # Items
                st.subheader("Ürünler")
                items = json.loads(order["items"])
                items_df = pd.DataFrame(items)
                st.dataframe(items_df, use_container_width=True)
            
            with col2:
                st.subheader("İşlemler")
                
                # Update status
                update_options = {"Bekleyen": "pending", "İşleniyor": "processing", "Kargolandı": "shipped", "Teslim Edildi": "delivered"}
                
                # Varsayılan değeri mevcut duruma ayarla (eğer sözlükte varsa)
                current_status_tr = STATUS_MAP.get(order['status'], "Bekleyen")
                index_val = list(update_options.keys()).index(current_status_tr) if current_status_tr in update_options else 0
                
                selected_update_tr = st.selectbox(
                    "Durumu Güncelle",
                    list(update_options.keys()),
                    index=index_val
                )
                new_status = update_options[selected_update_tr]
                
                notes = st.text_area("Not Ekle", height=100)
                
                if st.button("Siparişi Güncelle", use_container_width=True, type="primary"):
                    updated_order = database.update_order_status(order_id, new_status, notes)
                    if updated_order:
                        st.success(f"✅ Sipariş {order_id} durumu '{selected_update_tr}' olarak güncellendi")
                        
                        # Send email notification (use real email if enabled in sidebar)
                        if new_status == "shipped":
                            email_service.send_order_notification(
                                updated_order,
                                "shipped",
                                use_real=bool(st.session_state.get("real_email", False)),
                            )
                            st.info("📧 Kargo bildirimi gönderildi")
                        elif new_status == "delivered":
                            email_service.send_order_notification(
                                updated_order,
                                "delivered",
                                use_real=bool(st.session_state.get("real_email", False)),
                            )
                            st.info("📧 Teslimat bildirimi gönderildi")
                    else:
                        st.error("Sipariş güncellenemedi")
                
                st.divider()
                
                # Email logs
                st.subheader("E-posta Geçmişi")
                email_logs = database.get_email_logs(order_id)
                if email_logs:
                    logs_df = pd.DataFrame([
                        {
                            "Tür": log["email_type"],
                            "Durum": log["status"],
                            "Gönderildi": log["sent_at"]
                        }
                        for log in email_logs
                    ])
                    st.dataframe(logs_df, use_container_width=True)
                else:
                    st.info("Bu sipariş için gönderilen e-posta yok")
        else:
            st.error(f"{order_id} numaralı sipariş bulunamadı")


elif view_option == "Sipariş Asistanı":
    st.header("Sipariş Takip Asistanı")
    
    if st.session_state.order_agent is None:
        st.error("❌ Sipariş Asistanı başlatılamadı. Lütfen ortam değişkenlerinde GOOGLE_API_KEY ayarlayın.")
    else:
        st.info(
            "💡 **Nasıl kullanılır:** Siparişler, müşteriler veya sipariş durumları hakkında sorular sorun. "
            "Asistan bilgi bulmanıza ve siparişleri yönetmenize yardımcı olacaktır."
        )
        
        # Chat interface
        if "agent_messages" not in st.session_state:
            st.session_state.agent_messages = []
        if "order_agent_chat_id" not in st.session_state:
            st.session_state.order_agent_chat_id = None
        
        # Display chat history
        for message in st.session_state.agent_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # User input
        user_input = st.chat_input("Siparişler hakkında soru sorun...")
        
        if user_input:
            # Add user message
            st.session_state.agent_messages.append({"role": "user", "content": user_input})
            
            with st.chat_message("user"):
                st.write(user_input)
            
            # Get agent response
            with st.spinner("Asistan düşünüyor..."):
                # Asistanın yanıtını veriyoruz. (Asistanın Türkçe yanıtlamasını isterseniz, arka plandaki promptu güncellemeniz gerekebilir)
                response = run_order_agent(st.session_state.order_agent, user_input)
            
            # Add assistant message
            st.session_state.agent_messages.append({"role": "assistant", "content": response})

            record_chat_exchange(
                session_key="order_agent_chat_id",
                agent_name="Sipariş Takip Asistanı",
                prompt=user_input,
                response=response,
                title="Sipariş Takip Asistanı",
                source="order_inventory",
            )
            
            with st.chat_message("assistant"):
                st.write(response)