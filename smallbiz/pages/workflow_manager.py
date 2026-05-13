import streamlit as st
import pandas as pd
import database
from dotenv import load_dotenv
import os

from agents.order_agent import create_order_agent
from agents.stock_manager_agent import create_stock_manager_agent
from agents.workflow_manager_agent import (
    create_workflow_manager_agent,
    run_workflow_manager_agent,
)
from chat_history import record_chat_exchange

load_dotenv()

st.set_page_config(
    page_title="İş Akışı Yöneticisi",
    page_icon="🧭",
    layout="wide",
)

# Arka plan işleyişini bozmamak için çeviri sözlükleri
STATUS_MAP = {"": "", "Yapılacak": "todo", "Devam Ediyor": "in_progress", "Engellendi": "blocked", "Tamamlandı": "done"}
PRIORITY_MAP = {"": "", "Düşük": "low", "Orta": "medium", "Yüksek": "high"}

if "order_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    st.session_state.order_agent = create_order_agent(api_key) if api_key else None

if "stock_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    st.session_state.stock_agent = create_stock_manager_agent(api_key) if api_key else None

if "workflow_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    st.session_state.workflow_agent = create_workflow_manager_agent(
        api_key=api_key,
        order_agent=st.session_state.order_agent,
        stock_agent=st.session_state.stock_agent,
    )

if "workflow_messages" not in st.session_state:
    st.session_state.workflow_messages = []
if "workflow_agent_chat_id" not in st.session_state:
    st.session_state.workflow_agent_chat_id = None


def _send_workflow_prompt(prompt: str):
    st.session_state.workflow_messages.append({"role": "user", "content": prompt})
    response = run_workflow_manager_agent(st.session_state.workflow_agent, prompt)
    st.session_state.workflow_messages.append({"role": "assistant", "content": response})
    record_chat_exchange(
        session_key="workflow_agent_chat_id",
        agent_name="İş Akışı Yöneticisi Asistanı",
        prompt=prompt,
        response=response,
        title="İş Akışı Yöneticisi Asistanı",
        source="workflow_manager",
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
    if st.button("📦 Stoklar", use_container_width=True):
        st.switch_page("pages/stock_agent.py")

    st.divider()
    
    view_options_map = {
        "İş Akışı Paneli": "Workflow Dashboard", 
        "Çalışanlar": "Employees", 
        "Görevler": "Tasks", 
        "İş Akışı Asistanı": "Workflow Agent"
    }
    selected_view = st.radio(
        "İş Akışı Görünümü",
        list(view_options_map.keys()),
    )
    view_option = view_options_map[selected_view]

st.title("🧭 İş Akışı Yöneticisi")

if view_option == "Workflow Dashboard":
    employees = database.get_employees(active_only=True)
    tasks = database.get_tasks()
    overdue = database.get_overdue_tasks()
    workload = database.get_employee_workload()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aktif Çalışanlar", len(employees))
    col2.metric("Toplam Görev", len(tasks))
    col3.metric("Gecikmiş Görevler", len(overdue))
    col4.metric("Devam Eden Görevler", len([t for t in tasks if t["status"] == "in_progress"]))

    st.divider()

    if workload:
        chart_df = pd.DataFrame(
            [
                {
                    "Çalışan": item["full_name"],
                    "Toplam": item["total_tasks"],
                    "Devam Eden": item["in_progress_tasks"],
                    "Engellenen": item["blocked_tasks"],
                }
                for item in workload
            ]
        )
        st.subheader("Ekip İş Yükü")
        st.bar_chart(chart_df.set_index("Çalışan")[["Toplam", "Devam Eden", "Engellenen"]])

if view_option == "Employees":
    st.subheader("Çalışanlar")

    with st.form("add_worker_form"):
        col1, col2, col3 = st.columns(3)
        full_name = col1.text_input("Ad Soyad")
        email = col2.text_input("E-posta")
        role = col3.text_input("Rol", value="Personel")
        submitted = st.form_submit_button("Çalışan Ekle", type="primary")

        if submitted:
            worker = database.add_employee(full_name=full_name, email=email, role=role)
            if worker:
                st.success(f"Eklendi: {worker['full_name']} ({worker['employee_id']})")
            else:
                st.error("Çalışan eklenemedi. E-posta adresi zaten mevcut olabilir.")

    employees = database.get_employees(active_only=True)
    if employees:
        st.dataframe(pd.DataFrame(employees), use_container_width=True)
    else:
        st.info("Çalışan bulunamadı.")

if view_option == "Tasks":
    st.subheader("Görev Yönetimi")

    employees = database.get_employees(active_only=True)
    employee_options = {f"{e['full_name']} ({e['email']})": e for e in employees}

    with st.form("assign_task_form"):
        title = st.text_input("Görev Başlığı")
        description = st.text_area("Açıklama")
        selected_label = st.selectbox("Ata", options=list(employee_options.keys()) if employee_options else ["Çalışan yok"]) 
        selected_priority_tr = st.selectbox("Öncelik", ["Düşük", "Orta", "Yüksek"])
        due_date = st.text_input("Bitiş Tarihi (YYYY-AA-GG veya YYYY-AA-GG SS:DD:SS)")
        submitted = st.form_submit_button("Görev Ata", type="primary")

        if submitted and employee_options:
            emp = employee_options[selected_label]
            task = database.assign_task(
                title=title,
                description=description,
                assigned_to_employee_id=emp["employee_id"],
                assigned_by="Business Owner",
                priority=PRIORITY_MAP[selected_priority_tr],
                due_date=due_date,
            )
            if task:
                st.success(f"Görev {task['task_id']}, {emp['full_name']} kişisine atandı.")
            else:
                st.error("Görev ataması başarısız oldu.")

    st.divider()

    tasks = database.get_tasks()
    if tasks:
        st.dataframe(pd.DataFrame(tasks), use_container_width=True)

        st.subheader("Görev Durumunu Güncelle")
        col1, col2, col3 = st.columns(3)
        task_id = col1.text_input("Görev ID", placeholder="TASK-001")
        selected_status_tr = col2.selectbox("Yeni Durum", ["Yapılacak", "Devam Ediyor", "Engellendi", "Tamamlandı"])
        notes = col3.text_input("Notlar")

        if st.button("Görevi Güncelle", type="primary"):
            new_status = STATUS_MAP[selected_status_tr]
            updated = database.update_task_status(task_id=task_id, status=new_status, notes=notes)
            if updated:
                st.success(f"Güncellendi: {task_id} durumu '{selected_status_tr}' oldu.")
            else:
                st.error("Görev güncellenemedi.")

        st.subheader("Görevi Düzenle")
        task_ids = [t["task_id"] for t in tasks]
        with st.form("edit_task_form"):
            edit_col1, edit_col2 = st.columns(2)
            edit_task_id = edit_col1.selectbox("Düzenlenecek Görev", options=task_ids)
            edit_status_tr = edit_col2.selectbox(
                "Durumu Düzenle",
                ["", "Yapılacak", "Devam Ediyor", "Engellendi", "Tamamlandı"],
                help="Mevcut durumu korumak için boş bırakın.",
            )

            edit_col3, edit_col4 = st.columns(2)
            edit_priority_tr = edit_col3.selectbox(
                "Önceliği Düzenle",
                ["", "Düşük", "Orta", "Yüksek"],
                help="Mevcut önceliği korumak için boş bırakın.",
            )
            edit_due_date = edit_col4.text_input("Bitiş Tarihini Düzenle (YYYY-AA-GG SS:DD:SS)")

            edit_title = st.text_input("Başlığı Düzenle")
            edit_description = st.text_area("Açıklamayı Düzenle")
            edit_notes = st.text_area("Notları Düzenle")

            assignee_options = {f"{e['employee_id']} - {e['full_name']}": e["employee_id"] for e in employees}
            selected_assignee = st.selectbox(
                "Yeniden Ata",
                options=["Mevcudu Koru"] + list(assignee_options.keys()),
            )

            edit_submitted = st.form_submit_button("Görev Değişikliklerini Kaydet", type="primary")
            if edit_submitted:
                reassigned_employee_id = ""
                if selected_assignee != "Mevcudu Koru":
                    reassigned_employee_id = assignee_options[selected_assignee]

                updated_task = database.update_task(
                    task_id=edit_task_id,
                    title=edit_title or None,
                    description=edit_description or None,
                    assigned_to_employee_id=reassigned_employee_id or None,
                    status=STATUS_MAP[edit_status_tr] if edit_status_tr else None,
                    priority=PRIORITY_MAP[edit_priority_tr] if edit_priority_tr else None,
                    due_date=edit_due_date if edit_due_date else None,
                    notes=edit_notes or None,
                )
                if updated_task:
                    st.success(f"{edit_task_id} güncellendi.")
                else:
                    st.error("Görev düzenlenemedi. Girdiğiniz değerleri kontrol edin.")

        st.subheader("Görevi Sil")
        del_col1, del_col2 = st.columns([2, 1])
        delete_task_id = del_col1.selectbox("Silinecek Görev", options=task_ids, key="delete_task_select")
        if del_col2.button("Seçili Görevi Sil", type="secondary"):
            deleted = database.delete_task(delete_task_id)
            if deleted:
                st.success(f"{delete_task_id} silindi.")
            else:
                st.error("Görev bulunamadı.")
    else:
        st.info("Görev bulunamadı.")

    overdue = database.get_overdue_tasks()
    st.subheader("Gecikmiş Görevler")
    if overdue:
        st.dataframe(pd.DataFrame(overdue), use_container_width=True)
    else:
        st.success("Gecikmiş görev yok.")

    st.subheader("Çalışan İş Yükü")
    workload = database.get_employee_workload()
    if workload:
        st.dataframe(pd.DataFrame(workload), use_container_width=True)

if view_option == "Workflow Agent":
    st.subheader("İş Akışı Yöneticisi Asistanı")
    st.info(
        "İş akışı asistanına çalışan ekleme, görev atama, durum güncelleme, görevleri ve iş yükünü getirme gibi komutlar verebilirsiniz."
    )

    st.caption(
        "Örnek: ORD-003 numaralı siparişi takip et başlıklı, yüksek öncelikli bir görevi selin.aras@smallbiz.com adresine ata, bitiş tarihi haftaya cuma olsun."
    )

    st.subheader("Hızlı İşlemler")
    qa_col1, qa_col2, qa_col3 = st.columns(3)
    if qa_col1.button("Çalışanları Listele", use_container_width=True):
        # Burası değişti
        _send_workflow_prompt("çalışanları listele")
    if qa_col2.button("Gecikmiş Görevleri Göster", use_container_width=True):
        # Burası değişti
        _send_workflow_prompt("gecikmiş görevleri göster")
    if qa_col3.button("Ekip İş Yükünü Göster", use_container_width=True):
        # Burası değişti
        _send_workflow_prompt("ekip iş yükünü göster")

    employees = database.get_employees(active_only=True)
    if employees:
        st.subheader("Çalışana Özel Komutlar")
        emp_lookup = {
            f"{e['full_name']} ({e['employee_id']})": e
            for e in employees
        }
        selected_emp_label = st.selectbox("Çalışan Seç", options=list(emp_lookup.keys()))
        selected_emp = emp_lookup[selected_emp_label]

        emp_col1, emp_col2, emp_col3 = st.columns(3)
        if emp_col1.button("Çalışan İş Yükünü Getir", use_container_width=True):
            # Burası değişti
            _send_workflow_prompt(f"{selected_emp['employee_id']} ID'li çalışanın iş yükünü getir")

        if emp_col2.button("Çalışanın Görevlerini Getir", use_container_width=True):
            # Burası değişti
            _send_workflow_prompt(f"{selected_emp['employee_id']} ID'li çalışanın görevlerini getir")

        if emp_col3.button("Yarına Takip Görevi Ata", use_container_width=True):
            # Burası değişti (Agent'ın parse edebilmesi için özel formatlandı)
            _send_workflow_prompt(
                f"görev ata başlık Müşteri biletlerini takip et to {selected_emp['email']} orta bitiş yarın"
            )

        st.caption(
            f"Komut hedefi: {selected_emp['full_name']} | {selected_emp['email']}"
        )

    for message in st.session_state.workflow_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("İş akışı yöneticisine sorun...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)

        with st.spinner("İş akışı asistanı düşünüyor..."):
            response = _send_workflow_prompt(user_input)

        with st.chat_message("assistant"):
            st.write(response)