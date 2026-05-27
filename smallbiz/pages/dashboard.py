import streamlit as st
import pandas as pd
import database
from dotenv import load_dotenv

from chat_history import get_recent_chats
import auth

# Load .env so pages can access API keys / SMTP creds when opened directly
load_dotenv()

# Require login
auth.require_login()

# --- Page Config ---
st.set_page_config(
    page_title="Kontrol Paneli",
    page_icon="📊",
    layout="wide"
)
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


def _build_activity_table(orders: list[dict], tasks: list[dict]) -> pd.DataFrame:
    activity_rows = []

    for order in orders[:5]:
        activity_rows.append(
            {
                "Tür": "Sipariş",
                "Öğe": order["order_id"],
                "Sahip": order["customer_name"],
                "Detaylar": f"{_format_currency(order['total_amount'])} · {order['status']}",
                "Zaman Damgası": order["created_at"],
            }
        )

    for task in tasks[:5]:
        activity_rows.append(
            {
                "Tür": "Görev",
                "Öğe": task["task_id"],
                "Sahip": task["assigned_to_employee_id"],
                "Detaylar": f"{task['title']} · {task['status']}",
                "Zaman Damgası": task["created_at"],
            }
        )

    if not activity_rows:
        return pd.DataFrame(columns=["Tür", "Öğe", "Sahip", "Detaylar", "Zaman Damgası"])

    activity_df = pd.DataFrame(activity_rows)
    activity_df["Zaman Damgası"] = pd.to_datetime(activity_df["Zaman Damgası"], errors="coerce")
    return activity_df.sort_values("Zaman Damgası", ascending=False)

# --- Sidebar ---
with st.sidebar:

    st.title("Navigasyon")

    if st.button("💬 Sohbete Dön", use_container_width=True):
        st.switch_page("main.py")
    
    if st.button("📦 Sipariş Takibi", use_container_width=True):
        st.switch_page("pages/order_inventory.py")

    if st.button("🧱 Stok Yönetimi", use_container_width=True):
        st.switch_page("pages/order_inventory.py")

    if st.button("🧭 Görev Yöneticisi", use_container_width=True):
        st.switch_page("pages/workflow_manager.py")

    if st.button("📈 Analizler", use_container_width=True):
        st.switch_page("pages/analytics.py")

    if st.button("💬 WhatsApp Destek", use_container_width=True):
        st.switch_page("pages/customer_support.py")

# --- Dashboard Header ---
st.title("📊 Kontrol Paneli")
st.caption("Yüklediğiniz verilerden içgörüler elde edin ve işinizi büyütün.")

orders = database.get_all_orders()
employees = database.get_employees(active_only=True)
tasks = database.get_tasks()
overdue_tasks = database.get_overdue_tasks()
workload = database.get_employee_workload()

orders_df = pd.DataFrame(orders)
tasks_df = pd.DataFrame(tasks)

# --- Top Metrics ---
col1, col2, col3, col4 = st.columns(4)

total_orders = len(orders)
total_revenue = sum(order["total_amount"] for order in orders)
delivered_orders = len([order for order in orders if order["status"] == "delivered"])
open_tasks = len([task for task in tasks if task["status"] != "done"])

col1.metric("Toplam Sipariş", f"{total_orders}")
col2.metric("Toplam Gelir", _format_currency(total_revenue))
col3.metric("Aktif Çalışanlar", f"{len(employees)}")
col4.metric("Açık Görevler", f"{open_tasks}", f"{len(overdue_tasks)} gecikmiş")

st.divider()

# --- Charts Section ---
chart_col1, chart_col2 = st.columns(2)

if not orders_df.empty:
    orders_df["created_at"] = pd.to_datetime(orders_df["created_at"], errors="coerce")
    daily_orders = (
        orders_df.dropna(subset=["created_at"])
        .assign(Tarih=lambda frame: frame["created_at"].dt.date)
        .groupby("Tarih")
        .agg(Siparişler=("order_id", "count"), Gelir=("total_amount", "sum"))
        .reset_index()
        .sort_values("Tarih")
    )
else:
    daily_orders = pd.DataFrame(columns=["Tarih", "Siparişler", "Gelir"])

if not tasks_df.empty:
    task_status_df = (
        tasks_df.groupby("status")
        .agg(Görevler=("task_id", "count"))
        .reset_index()
        .rename(columns={"status": "Durum"})
    )
else:
    task_status_df = pd.DataFrame(columns=["Durum", "Görevler"])

with chart_col1:
    st.subheader("Zaman İçindeki Siparişler")
    if not daily_orders.empty:
        st.line_chart(daily_orders.set_index("Tarih")["Siparişler"])
    else:
        st.info("Henüz sipariş bulunmuyor.")

with chart_col2:
    st.subheader("Görev Durumu Dağılımı")
    if not task_status_df.empty:
        st.bar_chart(task_status_df.set_index("Durum"))
    else:
        st.info("Henüz görev bulunmuyor.")

st.divider()

# --- Recent Activity Table ---
st.subheader("Son Etkinlikler")

activity_df = _build_activity_table(orders, tasks)

if not activity_df.empty:
    display_df = activity_df.copy()
    display_df["Zaman Damgası"] = display_df["Zaman Damgası"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("Veritabanında son etkinlik bulunamadı.")

st.divider()


summary_col1, summary_col2 = st.columns(2)

with summary_col1:
    st.subheader("Ekip İş Yükü")
    if workload:
        workload_df = pd.DataFrame(workload)
        # Grafik etiketlerinin (legend) de Türkçe görünmesi için sütunları yeniden adlandırıyoruz
        workload_df = workload_df.rename(columns={
            "todo_tasks": "Yapılacak",
            "in_progress_tasks": "Devam Eden",
            "blocked_tasks": "Engellenen",
            "done_tasks": "Tamamlanan"
        })
        st.bar_chart(workload_df.set_index("full_name")[["Yapılacak", "Devam Eden", "Engellenen", "Tamamlanan"]])
    else:
        st.info("Aktif çalışan bulunamadı.")

with summary_col2:
    st.subheader("Veritabanı Özeti")
    snapshot_df = pd.DataFrame(
        [
            {"Metrik": "Siparişler", "Değer": len(orders)},
            {"Metrik": "Çalışanlar", "Değer": len(employees)},
            {"Metrik": "Görevler", "Değer": len(tasks)},
            {"Metrik": "Gecikmiş Görevler", "Değer": len(overdue_tasks)},
            {"Metrik": "Teslim Edilen Siparişler", "Değer": delivered_orders},
        ]
    )
    st.dataframe(snapshot_df, use_container_width=True, hide_index=True)

st.divider()

# --- Footer ---
st.caption("Kontrol paneli değerleri, veritabanından canlı olarak alınmaktadır.")
