"""
Koop-AI — Streamlit Dashboard
5 sekmeli, canlıya alıma hazır kooperatif yönetim paneli.
Çalıştır: streamlit run dashboard/app.py
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ── Konfigürasyon ─────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Koop-AI | Hatay Kadınlar Kooperatifi",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Özelleştirme ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Ana renk paleti — Hatay teması */
    :root {
        --primary: #2E7D32;
        --secondary: #F57F17;
        --danger: #C62828;
        --bg: #F9F6F0;
    }
    .main { background-color: var(--bg); }
    .stMetric { background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .status-badge {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600; text-align: center;
    }
    .badge-pending    { background: #FFF3E0; color: #E65100; }
    .badge-confirmed  { background: #E3F2FD; color: #1565C0; }
    .badge-shipped    { background: #E8F5E9; color: #2E7D32; }
    .badge-delivered  { background: #F3E5F5; color: #6A1B9A; }
    .low-stock-alert {
        background: #FFEBEE; border-left: 4px solid #C62828;
        padding: 0.6rem 1rem; border-radius: 4px; margin: 0.3rem 0;
    }
    .chat-user   { background: #E3F2FD; padding: 0.8rem; border-radius: 12px 12px 4px 12px; margin: 0.4rem 0; }
    .chat-bot    { background: #F1F8E9; padding: 0.8rem; border-radius: 12px 12px 12px 4px; margin: 0.4rem 0; }
    .overdue-row { background: #FFEBEE !important; }
    .timeline-step { display: flex; align-items: center; margin: 0.5rem 0; }
    .step-completed { color: #2E7D32; font-weight: 600; }
    .step-active    { color: #F57F17; font-weight: 700; font-size: 1.05rem; }
    .step-pending   { color: #BDBDBD; }
</style>
""", unsafe_allow_html=True)


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────
def api_get(endpoint: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ API'ye bağlanılamıyor. `uvicorn main:app --reload` komutunu çalıştırdığınızdan emin olun.")
        return None
    except Exception as e:
        st.error(f"API hatası: {e}")
        return None


def api_post(endpoint: str, data: dict):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ API'ye bağlanılamıyor.")
        return None
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e))
        st.error(f"Hata: {detail}")
        return None


def api_patch(endpoint: str, data: dict):
    try:
        r = requests.patch(f"{API_BASE}{endpoint}", json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Güncelleme hatası: {e}")
        return None


def status_badge(status: str) -> str:
    labels = {
        "pending": "⏳ Bekliyor",
        "confirmed": "✅ Onaylandı",
        "shipped": "🚚 Kargoda",
        "delivered": "🎉 Teslim",
    }
    css_map = {
        "pending": "badge-pending",
        "confirmed": "badge-confirmed",
        "shipped": "badge-shipped",
        "delivered": "badge-delivered",
    }
    label = labels.get(status, status)
    css = css_map.get(status, "badge-pending")
    return f'<span class="status-badge {css}">{label}</span>'


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/basil.png", width=60)
    st.title("🌿 Koop-AI")
    st.caption("Hatay Kadınlar Kooperatifi")
    st.divider()

    # API durum göstergesi
    health = api_get("/health")
    if health:
        st.success("🟢 API Bağlı", icon="✅")
    else:
        st.error("🔴 API Bağlantı Yok")

    st.divider()
    st.markdown("**Hızlı Erişim**")
    st.markdown("📦 `localhost:8000/docs` — API")
    st.markdown("🌐 `localhost:8501` — Dashboard")
    st.divider()
    st.caption("Google AI Hackathon 2024")
    st.caption("Koop-AI Team")


# ── Sekmeler ──────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Siparişler",
    "📊 Satış Analizi",
    "💬 Müşteri Destek",
    "👥 Çalışanlar",
    "🚚 Kargo",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SİPARİŞLER & STOK
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("📦 Sipariş & Stok Yönetimi")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Düşük stok uyarıları
        inventory = api_get("/api/inventory/stock")
        if inventory:
            low_stock = [p for p in inventory["inventory"] if p["low_stock_warning"]]
            if low_stock:
                st.markdown("### ⚠️ Düşük Stok Uyarısı")
                for p in low_stock:
                    st.markdown(
                        f'<div class="low-stock-alert">🔴 <b>{p["name"]}</b> — '
                        f'Kalan: <b>{p["stock_quantity"]} {p["unit"]}</b></div>',
                        unsafe_allow_html=True,
                    )
                st.divider()

        # Sipariş listesi
        st.markdown("### 🗂️ Siparişler")
        status_filter = st.selectbox(
            "Duruma göre filtrele",
            ["Tümü", "pending", "confirmed", "shipped", "delivered"],
            format_func=lambda x: {
                "Tümü": "📋 Tümü",
                "pending": "⏳ Bekliyor",
                "confirmed": "✅ Onaylandı",
                "shipped": "🚚 Kargoda",
                "delivered": "🎉 Teslim",
            }.get(x, x),
        )
        params = {} if status_filter == "Tümü" else {"status": status_filter}
        orders_data = api_get("/api/orders/list", params)
        if orders_data:
            orders = orders_data["orders"]
            if orders:
                # Özet metrikler
                m1, m2, m3, m4 = st.columns(4)
                all_orders = api_get("/api/orders/list")["orders"] if status_filter != "Tümü" else orders
                m1.metric("Toplam", len(all_orders))
                m2.metric("Bekleyen", sum(1 for o in all_orders if o["status"] == "pending"))
                m3.metric("Kargoda", sum(1 for o in all_orders if o["status"] == "shipped"))
                m4.metric("Teslim", sum(1 for o in all_orders if o["status"] == "delivered"))

                st.divider()

                for o in orders:
                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 2, 1, 2])
                        c1.markdown(
                            f"**{o['customer_name']}**  \n"
                            f"🛒 {o['product_name']} × {o['quantity']}  \n"
                            f"📅 {o['created_at'][:10] if o['created_at'] else '-'}"
                        )
                        c2.markdown(f"💰 **{o['total_price']:.0f} TL**  \n🔖 #{o['id']}")
                        c3.markdown(status_badge(o["status"]), unsafe_allow_html=True)
                        with c4:
                            new_status = st.selectbox(
                                "Durum",
                                ["pending", "confirmed", "shipped", "delivered"],
                                index=["pending", "confirmed", "shipped", "delivered"].index(o["status"]),
                                key=f"status_{o['id']}",
                                label_visibility="collapsed",
                            )
                            if new_status != o["status"]:
                                if st.button("💾", key=f"save_{o['id']}", help="Kaydet"):
                                    result = api_patch(f"/api/orders/{o['id']}/status", {"status": new_status})
                                    if result:
                                        st.success("✅ Güncellendi!")
                                        st.rerun()
                        st.divider()
            else:
                st.info("Bu kriterde sipariş bulunamadı.")

    with col_right:
        st.markdown("### ➕ Yeni Sipariş")

        inventory_for_form = api_get("/api/inventory/stock")
        if inventory_for_form:
            products = inventory_for_form["inventory"]
            product_options = {f"{p['name']} ({p['stock_quantity']} adet)": p["id"] for p in products}

            with st.form("new_order_form", clear_on_submit=True):
                sel = st.selectbox("Ürün", options=list(product_options.keys()))
                qty = st.number_input("Adet", min_value=1, max_value=999, value=1)
                cname = st.text_input("Müşteri Adı *")
                cemail = st.text_input("E-posta")
                cphone = st.text_input("Telefon")
                cnotes = st.text_area("Notlar", height=60)

                submitted = st.form_submit_button("🛒 Sipariş Oluştur", use_container_width=True, type="primary")
                if submitted:
                    if not cname:
                        st.error("Müşteri adı zorunludur.")
                    else:
                        result = api_post("/api/orders/create", {
                            "customer_name": cname,
                            "customer_email": cemail,
                            "customer_phone": cphone,
                            "product_id": product_options[sel],
                            "quantity": qty,
                            "notes": cnotes,
                        })
                        if result:
                            st.success(f"✅ Sipariş #{result['order_id']} oluşturuldu!")
                            st.info(f"🚚 Takip No: **{result['tracking_no']}**")
                            if result.get("low_stock_warning"):
                                st.warning(f"⚠️ Bu üründe stok azalıyor! Kalan: {result['remaining_stock']}")
                            st.rerun()

        # Stok tablosu
        st.divider()
        st.markdown("### 📊 Stok Durumu")
        if inventory_for_form:
            df_stock = pd.DataFrame(inventory_for_form["inventory"])
            if not df_stock.empty:
                df_display = df_stock[["name", "stock_quantity", "unit", "price"]].copy()
                df_display.columns = ["Ürün", "Stok", "Birim", "Fiyat (TL)"]
                df_display["Stok"] = df_display["Stok"].apply(
                    lambda x: f"🔴 {x}" if x < 10 else f"🟢 {x}"
                )
                st.dataframe(df_display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SATIŞ ANALİZİ
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📊 Satış Analizi & Yapay Zeka Özetleme")

    col_reload, _ = st.columns([1, 4])
    with col_reload:
        refresh = st.button("🔄 Yenile", key="refresh_analytics")

    analytics = api_get("/api/analytics/summary")

    if analytics:
        metrics = analytics["metrics"]
        charts = analytics["charts"]

        # KPI kartları
        st.markdown("### 📈 Temel Metrikler")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Toplam Ciro", f"{metrics['total_revenue']:,.0f} TL")
        k2.metric("🛒 Toplam Sipariş", metrics["total_orders"])
        k3.metric("💵 Ortalama Sepet", f"{metrics['avg_order_value']:.0f} TL")
        k4.metric("🏆 En İyi Hafta", f"{metrics['best_week_revenue']:,.0f} TL")

        st.divider()

        chart_col, summary_col = st.columns([3, 2])

        with chart_col:
            # Aylık gelir çizgi grafiği
            if charts.get("monthly_revenue"):
                df_monthly = pd.DataFrame(charts["monthly_revenue"])
                fig_monthly = px.bar(
                    df_monthly,
                    x="month",
                    y="revenue",
                    title="📅 Aylık Ciro (TL)",
                    color="revenue",
                    color_continuous_scale="Greens",
                    labels={"month": "Ay", "revenue": "Ciro (TL)"},
                )
                fig_monthly.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_monthly, use_container_width=True)

            # Ürün gelir pasta grafiği
            if charts.get("product_revenue"):
                df_prod = pd.DataFrame(charts["product_revenue"])
                fig_pie = px.pie(
                    df_prod,
                    values="revenue",
                    names="product",
                    title="🛍️ Ürün Bazlı Ciro Dağılımı",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.35,
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # Bölge gelir grafiği
            if charts.get("region_revenue"):
                df_region = pd.DataFrame(charts["region_revenue"])
                fig_region = px.bar(
                    df_region.sort_values("revenue", ascending=True),
                    x="revenue",
                    y="region",
                    orientation="h",
                    title="🗺️ Bölge Bazlı Ciro",
                    color="revenue",
                    color_continuous_scale="Blues",
                    labels={"region": "Bölge", "revenue": "Ciro (TL)"},
                )
                fig_region.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_region, use_container_width=True)

        with summary_col:
            st.markdown("### 🤖 Gemini AI Özeti")
            st.markdown("*Gemini 1.5 Flash tarafından üretildi*")
            st.divider()

            summary_text = analytics.get("summary", "Özet bulunamadı.")
            for line in summary_text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("✅"):
                    st.success(line)
                elif line.startswith("⚠️"):
                    st.warning(line)
                elif line.startswith("💡"):
                    st.info(line)
                else:
                    st.markdown(line)

            st.divider()
            st.markdown("### 🏆 En Çok Satan Ürünler")
            for prod, qty in metrics.get("top_products_by_quantity", {}).items():
                st.markdown(f"**{prod}** — {qty} adet")

        # CSV yükleme
        st.divider()
        st.markdown("### 📤 Kendi Satış Verinizi Yükleyin")
        uploaded = st.file_uploader(
            "CSV dosyası (sütunlar: date, product_name, quantity, unit_price, total, customer_region)",
            type=["csv"],
        )
        if uploaded:
            files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
            try:
                r = requests.post(f"{API_BASE}/api/analytics/upload", files=files, timeout=30)
                if r.status_code == 200:
                    st.success("✅ Analiz tamamlandı!")
                    custom_analytics = r.json()
                    st.markdown("**Gemini Özeti:**")
                    st.markdown(custom_analytics.get("summary", ""))
                else:
                    st.error(r.json().get("detail", "Hata"))
            except Exception as e:
                st.error(f"Yükleme hatası: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MÜŞTERİ DESTEK (RAG)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("💬 Müşteri Destek Asistanı")
    st.caption("Gemini 1.5 Flash + ChromaDB RAG sistemi — Türkçe soru-cevap")

    # Örnek sorular
    st.markdown("**💡 Örnek sorular:**")
    example_questions = [
        "Biber salçanızda koruyucu madde var mı, fiyatı ne kadar?",
        "Kargom ne zaman gelir?",
        "İade koşullarınız neler?",
        "Hangi ödeme yöntemlerini kabul ediyorsunuz?",
        "Antep Fıstıklı Sucukta alerjen var mı?",
    ]
    eq_cols = st.columns(len(example_questions))
    for i, eq in enumerate(example_questions):
        if eq_cols[i].button(f"💬 {eq[:25]}…", key=f"eq_{i}", help=eq):
            st.session_state["support_question"] = eq

    st.divider()

    # Chat geçmişi
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Soru inputu
    question = st.text_input(
        "Sorunuzu yazın:",
        value=st.session_state.get("support_question", ""),
        placeholder="Ürünlerinizde gluten var mı?",
        key="support_input",
    )
    if "support_question" in st.session_state:
        del st.session_state["support_question"]

    ask_col, clear_col = st.columns([3, 1])
    ask_btn = ask_col.button("🔍 Sor", type="primary", use_container_width=True)
    clear_btn = clear_col.button("🗑️ Temizle", use_container_width=True)

    if clear_btn:
        st.session_state["chat_history"] = []
        st.rerun()

    if ask_btn and question.strip():
        with st.spinner("🤖 Gemini yanıt üretiyor..."):
            result = api_post("/api/support/query", {"question": question})
            if result:
                st.session_state["chat_history"].append({
                    "question": question,
                    "answer": result.get("answer", ""),
                    "sources": result.get("sources", []),
                })

    # Chat geçmişini göster
    for chat in reversed(st.session_state["chat_history"]):
        st.markdown(
            f'<div class="chat-user">👤 <b>Müşteri:</b><br>{chat["question"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="chat-bot">🤖 <b>Koop-AI:</b><br>{chat["answer"]}</div>',
            unsafe_allow_html=True,
        )
        if chat["sources"]:
            st.caption(f"📄 Kaynaklar: {', '.join(chat['sources'])}")
        st.markdown("")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ÇALIŞANLAR & GÖREVLER
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("👥 Çalışan & Görev Yönetimi")

    emp_col, task_col = st.columns([2, 3])

    with emp_col:
        st.markdown("### 👤 Çalışanlar")
        employees_data = api_get("/api/workflow/employees")
        if employees_data:
            for emp in employees_data["employees"]:
                status_icon = "🟢" if emp["status"] == "active" else "🟡"
                with st.expander(f"{status_icon} {emp['name']} — {emp['role']}"):
                    st.markdown(f"**Departman:** {emp['department']}")
                    st.markdown(f"**Durum:** {emp['status']}")
                    st.markdown(
                        f"📋 Bekleyen: **{emp['pending_tasks']}** | "
                        f"🔄 Devam Eden: **{emp['in_progress_tasks']}** | "
                        f"✅ Tamamlanan: **{emp['done_tasks']}**"
                    )

        st.divider()

        # Görev yükü grafiği
        workload_data = api_get("/api/workflow/workload")
        if workload_data and workload_data["workload"]:
            st.markdown("### ⚖️ Görev Yükü")
            df_wl = pd.DataFrame(workload_data["workload"])
            fig_wl = px.bar(
                df_wl,
                x="employee_name",
                y=["pending", "in_progress", "done"],
                title="Çalışan Başına Görev Dağılımı",
                barmode="stack",
                color_discrete_map={
                    "pending": "#FFB74D",
                    "in_progress": "#42A5F5",
                    "done": "#66BB6A",
                },
                labels={"employee_name": "Çalışan", "value": "Görev Sayısı"},
            )
            fig_wl.update_layout(legend_title_text="Durum", xaxis_tickangle=-30)
            st.plotly_chart(fig_wl, use_container_width=True)

    with task_col:
        # Gecikmiş görevler
        overdue_data = api_get("/api/workflow/overdue")
        if overdue_data and overdue_data["overdue_tasks"]:
            st.markdown("### 🔴 Gecikmiş Görevler")
            for task in overdue_data["overdue_tasks"]:
                st.markdown(
                    f'<div class="low-stock-alert">'
                    f'⏰ <b>{task["title"]}</b> — {task["employee_name"]}<br>'
                    f'Bitiş: {task["due_date"]} | Durum: {task["status"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.divider()

        st.markdown("### 📋 Tüm Görevler")
        task_status_filter = st.selectbox(
            "Duruma göre filtrele",
            ["Tümü", "pending", "in_progress", "done"],
            format_func=lambda x: {
                "Tümü": "📋 Tümü",
                "pending": "⏳ Bekliyor",
                "in_progress": "🔄 Devam Ediyor",
                "done": "✅ Tamamlandı",
            }.get(x, x),
            key="task_filter",
        )
        task_params = {} if task_status_filter == "Tümü" else {"status": task_status_filter}
        tasks_data = api_get("/api/workflow/tasks", task_params)
        if tasks_data:
            for task in tasks_data["tasks"]:
                is_overdue = (
                    task["due_date"]
                    and task["due_date"] < date.today().isoformat()
                    and task["status"] != "done"
                )
                border = "border-left: 3px solid #C62828;" if is_overdue else ""
                status_icons = {"pending": "⏳", "in_progress": "🔄", "done": "✅"}
                icon = status_icons.get(task["status"], "📋")

                with st.container():
                    t1, t2, t3 = st.columns([4, 2, 2])
                    t1.markdown(
                        f"{icon} **{task['title']}**  \n"
                        f"👤 {task['employee_name']} | 📅 {task['due_date'] or '-'}"
                    )
                    t2.markdown(f"_{task['description'][:40]}..._" if task.get("description") and len(task.get("description", "")) > 40 else f"_{task.get('description', '')}_")
                    with t3:
                        new_task_status = st.selectbox(
                            "Durum",
                            ["pending", "in_progress", "done"],
                            index=["pending", "in_progress", "done"].index(task["status"]),
                            key=f"task_status_{task['id']}",
                            label_visibility="collapsed",
                        )
                        if new_task_status != task["status"]:
                            if st.button("💾", key=f"save_task_{task['id']}"):
                                result = api_patch(f"/api/workflow/tasks/{task['id']}", {"status": new_task_status})
                                if result:
                                    st.rerun()
                    st.divider()

        # Yeni görev formu
        st.markdown("### ➕ Görev Ata")
        with st.form("new_task_form", clear_on_submit=True):
            emp_data = api_get("/api/workflow/employees")
            emp_options = {}
            if emp_data:
                emp_options = {e["name"]: e["id"] for e in emp_data["employees"]}

            task_emp = st.selectbox("Çalışan", options=list(emp_options.keys()))
            task_title = st.text_input("Görev Başlığı *")
            task_desc = st.text_area("Açıklama", height=60)
            task_due = st.date_input("Bitiş Tarihi", value=date.today())

            if st.form_submit_button("📌 Görev Ata", type="primary", use_container_width=True):
                if task_title and emp_options:
                    result = api_post("/api/workflow/tasks", {
                        "employee_id": emp_options[task_emp],
                        "title": task_title,
                        "description": task_desc,
                        "due_date": task_due.isoformat(),
                    })
                    if result and result.get("success"):
                        st.success("✅ Görev atandı!")
                        st.rerun()
                else:
                    st.error("Görev başlığı zorunludur.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — KARGO TAKİP
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("🚚 Kargo Takip")

    search_col, _ = st.columns([2, 3])

    with search_col:
        st.markdown("### 🔍 Kargo Sorgula")
        tracking_input = st.text_input(
            "Takip numarası",
            placeholder="KOOP100001",
            key="tracking_input",
        )
        search_btn = st.button("🔍 Sorgula", type="primary", use_container_width=True)

        if search_btn and tracking_input.strip():
            with st.spinner("Kargo bilgileri alınıyor..."):
                cargo = api_get(f"/api/cargo/{tracking_input.strip().upper()}")
                if cargo and cargo["success"]:
                    st.markdown("---")
                    st.markdown(f"### {cargo['status_label']}")

                    # Durum zaman çizelgesi
                    st.markdown("**📍 Teslimat Zaman Çizelgesi**")
                    for step in cargo["timeline"]:
                        if step["completed"] and step["active"]:
                            st.markdown(f"🟠 **{step['icon']} {step['label']}** ← *Şu anki konum*")
                        elif step["completed"]:
                            st.markdown(f"✅ {step['icon']} ~~{step['label']}~~")
                        else:
                            st.markdown(f"⬜ {step['icon']} {step['label']}")

                    st.divider()
                    st.markdown(f"📦 **Son Konum:** {cargo['last_location']}")
                    st.markdown(f"🚛 **Kargo Firması:** {cargo['carrier']}")
                    if cargo.get("estimated_delivery"):
                        st.markdown(f"📅 **Tahmini Teslimat:** {cargo['estimated_delivery']}")

                    if cargo.get("order"):
                        st.divider()
                        st.markdown("**🛒 Sipariş Bilgisi**")
                        st.markdown(f"👤 Müşteri: {cargo['order']['customer_name']}")
                        st.markdown(f"📦 Ürün: {cargo['order']['product_name']} × {cargo['order']['quantity']}")

    # Tüm kargolar tablosu
    st.divider()
    st.markdown("### 📋 Tüm Kargo Kayıtları")

    # Kargo tablosunu siparişlerden oluştur
    orders_for_cargo = api_get("/api/orders/list")
    if orders_for_cargo:
        cargo_rows = []
        for o in orders_for_cargo["orders"]:
            if o["cargo_tracking_no"]:
                cargo_rows.append({
                    "Takip No": o["cargo_tracking_no"],
                    "Müşteri": o["customer_name"],
                    "Ürün": o["product_name"],
                    "Sipariş Durumu": o["status"],
                })
        if cargo_rows:
            df_cargo = pd.DataFrame(cargo_rows)
            st.dataframe(df_cargo, use_container_width=True, hide_index=True)

    # Hızlı takip butonları
    st.divider()
    st.markdown("### 💡 Örnek Takip Numaraları")
    st.caption("Aşağıdaki numaralardan birini kopyalayıp yukarıya yapıştırabilirsiniz:")
    if orders_for_cargo:
        sample_trackings = [
            o["cargo_tracking_no"]
            for o in orders_for_cargo["orders"]
            if o["cargo_tracking_no"]
        ][:6]
        cols = st.columns(min(len(sample_trackings), 6))
        for i, tn in enumerate(sample_trackings):
            if cols[i].button(f"📦 {tn}", key=f"quick_{tn}"):
                st.session_state["tracking_input"] = tn
                st.rerun()
