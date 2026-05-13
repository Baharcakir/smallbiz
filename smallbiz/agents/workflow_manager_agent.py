import json
import re
from datetime import datetime, timedelta
from langchain_core.tools import tool
import database
from agents.order_agent import run_order_agent
from agents.stock_manager_agent import run_stock_manager_agent


def _call_order_agent(order_agent, prompt: str) -> str:
    if not order_agent:
        return "Sipariş asistanı kullanılamıyor."
    try:
        return run_order_agent(order_agent, prompt)
    except Exception:
        return "Sipariş asistanından sipariş bağlamı alınamadı."


def _call_stock_agent(stock_agent, prompt: str) -> str:
    if not stock_agent:
        return "Stok asistanı kullanılamıyor."
    try:
        return run_stock_manager_agent(stock_agent, prompt)
    except Exception:
        return "Stok asistanından bağlam alınamadı."


def _parse_natural_due_date(text: str) -> str:
    """Parse due date from natural language into YYYY-MM-DD HH:MM:SS."""
    lower = text.lower()
    now = datetime.now()

    # Explicit date first
    explicit = re.search(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?", text)
    if explicit:
        date_part = explicit.group(1)
        time_part = explicit.group(2) or "17:00:00"
        if len(time_part) == 5:
            time_part += ":00"
        return f"{date_part} {time_part}"

    if "tomorrow" in lower or "yarın" in lower:
        target = now + timedelta(days=1)
        return target.replace(hour=17, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    weekdays = {
        "monday": 0, "pazartesi": 0,
        "tuesday": 1, "salı": 1,
        "wednesday": 2, "çarşamba": 2,
        "thursday": 3, "perşembe": 3,
        "friday": 4, "cuma": 4,
        "saturday": 5, "cumartesi": 5,
        "sunday": 6, "pazar": 6,
    }

    next_match = re.search(r"(?:next|haftaya)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)", lower)
    if next_match:
        target_day = weekdays[next_match.group(1)]
        current_day = now.weekday()
        days_ahead = (target_day - current_day + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        target = now + timedelta(days=days_ahead)
        return target.replace(hour=17, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    weekday_match = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)\b", lower)
    if weekday_match:
        target_day = weekdays[weekday_match.group(1)]
        current_day = now.weekday()
        days_ahead = (target_day - current_day + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        target = now + timedelta(days=days_ahead)
        return target.replace(hour=17, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    return ""


@tool
def add_worker_tool(full_name: str, email: str, role: str) -> str:
    """Add a new worker (employee) to the system."""
    employee = database.add_employee(full_name=full_name, email=email, role=role)
    if not employee:
        return "Çalışan eklenemedi. E-posta adresi zaten mevcut olabilir."

    return json.dumps(
        {
            "employee_id": employee["employee_id"],
            "full_name": employee["full_name"],
            "email": employee["email"],
            "role": employee["role"],
        }
    )


@tool
def get_employees_tool() -> str:
    """Get all active employees."""
    employees = database.get_employees(active_only=True)
    return json.dumps(employees)


@tool
def assign_task_tool(
    title: str,
    description: str,
    employee_email: str,
    priority: str = "medium",
    due_date: str = "",
    assigned_by: str = "Business Owner",
    order_context: str = "",
) -> str:
    """Assign a task to an employee using their email address."""
    employee = database.get_employee_by_email(employee_email)
    if not employee:
        return f"{employee_email} e-posta adresine sahip çalışan bulunamadı."

    notes = order_context.strip() if order_context else ""
    task = database.assign_task(
        title=title,
        description=description,
        assigned_to_employee_id=employee["employee_id"],
        assigned_by=assigned_by,
        priority=priority.lower(),
        due_date=due_date,
        notes=notes,
    )
    if not task:
        return "Görev atanamadı."

    return json.dumps(task)


@tool
def update_task_status_tool(task_id: str, status: str, notes: str = "") -> str:
    """Update a task status. Valid statuses: todo, in_progress, blocked, done."""
    updated = database.update_task_status(task_id=task_id, status=status.lower(), notes=notes)
    if not updated:
        return "Görev güncellenemedi. Görev ID'sinin ve durumunun geçerli olduğundan emin olun."
    return json.dumps(updated)


@tool
def edit_task_tool(
    task_id: str,
    title: str = "",
    description: str = "",
    employee_id: str = "",
    status: str = "",
    priority: str = "",
    due_date: str = "",
    notes: str = "",
) -> str:
    """Edit a task fields by task ID."""
    updated = database.update_task(
        task_id=task_id,
        title=title or None,
        description=description or None,
        assigned_to_employee_id=employee_id or None,
        status=status.lower() if status else None,
        priority=priority.lower() if priority else None,
        due_date=due_date if due_date else None,
        notes=notes or None,
    )
    if not updated:
        return "Görev düzenlenemedi. Görev ID, durum, öncelik ve çalışan ID değerlerini kontrol edin."
    return json.dumps({"edited_task": updated})


@tool
def delete_task_tool(task_id: str) -> str:
    """Delete a task by task ID."""
    deleted = database.delete_task(task_id=task_id)
    if not deleted:
        return f"Görev {task_id} bulunamadı."
    return json.dumps({"deleted_task_id": task_id})


@tool
def get_tasks_tool(status: str = "", employee_id: str = "") -> str:
    """Get tasks, optionally filtered by status and employee ID."""
    tasks = database.get_tasks(status=status or None, employee_id=employee_id or None)
    return json.dumps(tasks)


@tool
def get_overdue_tasks_tool() -> str:
    """Get tasks that are overdue and not done."""
    overdue = database.get_overdue_tasks()
    return json.dumps(overdue)


@tool
def get_employee_workload_tool(employee_id: str = "") -> str:
    """Get workload summary by employee or for all employees."""
    workload = database.get_employee_workload(employee_id=employee_id or None)
    return json.dumps(workload)


tools_list = [
    add_worker_tool,
    get_employees_tool,
    assign_task_tool,
    update_task_status_tool,
    edit_task_tool,
    delete_task_tool,
    get_tasks_tool,
    get_overdue_tasks_tool,
    get_employee_workload_tool,
]


def create_workflow_manager_agent(api_key: str, order_agent=None, stock_agent=None):
    """Create a workflow manager agent object."""
    return {
        "api_key": api_key,
        "order_agent": order_agent,
        "stock_agent": stock_agent,
        "tools": tools_list,
        "name": "Workflow Manager Agent",
    }


def _format_response(raw_response: str) -> str:
    if not raw_response:
        return raw_response

    if not raw_response.startswith("{") and not raw_response.startswith("["):
        return raw_response

    try:
        data = json.loads(raw_response)
    except Exception:
        return raw_response

    if isinstance(data, dict) and "employee_id" in data and "full_name" in data:
        return (
            f"Çalışan eklendi: **{data['full_name']}** ({data['employee_id']}), "
            f"Rol: **{data.get('role', 'Bilinmiyor')}**."
        )

    if isinstance(data, dict) and "task_id" in data and "title" in data:
        return (
            f"Görev **{data['task_id']}** atandı: **{data['title']}**\n"
            f"Atanan kişi: **{data.get('assigned_to_employee_id', 'Bilinmiyor')}**\n"
            f"Durum: **{data.get('status', 'todo')}**."
        )

    if isinstance(data, dict) and "edited_task" in data:
        task = data["edited_task"]
        return (
            f"Görev **{task['task_id']}** güncellendi: **{task['title']}**\n"
            f"Durum: **{task.get('status', 'todo')}** | Atanan kişi: **{task.get('assigned_to_employee_id', 'Bilinmiyor')}**."
        )

    if isinstance(data, dict) and "deleted_task_id" in data:
        return f"Görev başarıyla silindi: **{data['deleted_task_id']}**."

    if isinstance(data, list) and data and "task_id" in data[0]:
        lines = ["Görevler:"]
        for task in data:
            lines.append(
                f"- {task['task_id']} | {task['title']} | Durum: {task['status']} | Atanan: {task['assigned_to_employee_id']}"
            )
        return "\n".join(lines)

    if isinstance(data, list) and data and "total_tasks" in data[0]:
        lines = ["Çalışan iş yükü:"]
        for row in data:
            lines.append(
                f"- {row['employee_id']} ({row['full_name']}): Toplam={row['total_tasks']}, "
                f"Yapılacak={row['todo_tasks']}, Devam eden={row['in_progress_tasks']}, "
                f"Engellenen={row['blocked_tasks']}, Tamamlanan={row['done_tasks']}"
            )
        return "\n".join(lines)

    if isinstance(data, list) and data and "employee_id" in data[0] and "full_name" in data[0]:
        lines = ["Çalışanlar:"]
        for emp in data:
            lines.append(
                f"- {emp['employee_id']}: {emp['full_name']} ({emp['role']}) - {emp['email']}"
            )
        return "\n".join(lines)

    return raw_response


def run_workflow_manager_agent(agent, user_input: str) -> str:
    """Run workflow manager with intent-based routing and optional order-agent collaboration."""
    text = user_input.strip()
    lower = text.lower()

    if any(k in lower for k in ["stock", "inventory", "envanter", "stok", "low stock", "restock", "reorder"]):
        return _call_stock_agent(agent.get("stock_agent"), text)

    # 1) Add worker
    if any(k in lower for k in ["add worker", "new worker", "add employee", "new employee", "çalışan ekle", "yeni çalışan"]):
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", text)
        if not email_match:
            return "Lütfen çalışan eklemek için kişinin e-posta adresini belirtin."
        email = email_match.group(0)

        role = "Personel"
        role_match = re.search(r"role[:\s]+([A-Za-z ]+)|rol[:\s]+([A-Za-z ]+)", text, re.IGNORECASE)
        if role_match:
            role = (role_match.group(1) or role_match.group(2)).strip()

        name_part = text.split(email)[0].replace("add worker", "").replace("add employee", "").replace("çalışan ekle", "").strip(" ,:-")
        full_name = name_part if name_part else "Yeni Çalışan"

        return _format_response(add_worker_tool.func(full_name, email, role))

    # 2) Get employees
    if any(k in lower for k in ["get employees", "get emplloyees", "list employees", "show employees", "workers", "çalışanları getir", "çalışanları listele"]):
        return _format_response(get_employees_tool.func())

    # 3) Assign task
    if any(k in lower for k in ["assign task", "new task", "create task", "görev ata", "yeni görev"]):
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", text)
        if not email_match:
            return "Lütfen talebinize görevin atanacağı kişinin e-posta adresini ekleyin."

        employee_email = email_match.group(0)
        title = "Yeni Görev"
        title_match = re.search(r"title[:\s]+(.+?)(?:\s+to\s+[\w\.-]+@[\w\.-]+|$)|başlık[:\s]+(.+?)(?:\s+to\s+[\w\.-]+@[\w\.-]+|$)", text, re.IGNORECASE)
        if title_match:
            title = (title_match.group(1) or title_match.group(2)).strip()

        due_date = _parse_natural_due_date(text)

        priority = "medium"
        for p in ["low", "medium", "high", "düşük", "orta", "yüksek"]:
            if p in lower:
                # Eşleşen Türkçe ise İngilizceye çevir
                tr_to_en = {"düşük": "low", "orta": "medium", "yüksek": "high"}
                priority = tr_to_en.get(p, p)
                break

        description = text
        order_context = ""
        order_match = re.search(r"ORD-\d+", text, re.IGNORECASE)
        if order_match:
            order_id = order_match.group(0).upper()
            order_context = _call_order_agent(agent.get("order_agent"), f"{order_id} numaralı siparişin durumu nedir?")
            if title == "Yeni Görev":
                title = f"{order_id} için takip süreci"

        raw = assign_task_tool.func(
            title=title,
            description=description,
            employee_email=employee_email,
            priority=priority,
            due_date=due_date,
            order_context=order_context,
        )
        return _format_response(raw)

    # 3b) Edit task
    if any(k in lower for k in ["edit task", "update task details", "change task", "görevi düzenle", "görevi değiştir"]):
        task_match = re.search(r"TASK-\d+", text, re.IGNORECASE)
        if not task_match:
            return "Lütfen TASK-001 formatında bir görev ID'si belirtin."
        task_id = task_match.group(0).upper()

        title = ""
        title_match = re.search(r"title[:\s]+(.+?)(?:\s+(?:description|status|priority|due|assign|employee|notes)\b|$)|başlık[:\s]+(.+?)(?:\s+(?:açıklama|durum|öncelik|bitiş|ata|çalışan|notlar)\b|$)", text, re.IGNORECASE)
        if title_match:
            title = (title_match.group(1) or title_match.group(2)).strip()

        description = ""
        desc_match = re.search(r"description[:\s]+(.+?)(?:\s+(?:title|status|priority|due|assign|employee|notes)\b|$)|açıklama[:\s]+(.+?)(?:\s+(?:başlık|durum|öncelik|bitiş|ata|çalışan|notlar)\b|$)", text, re.IGNORECASE)
        if desc_match:
            description = (desc_match.group(1) or desc_match.group(2)).strip()

        status = ""
        for s in ["todo", "in_progress", "blocked", "done", "yapılacak", "devam_ediyor", "engellendi", "tamamlandı"]:
            if s in lower:
                tr_to_en_stat = {"yapılacak": "todo", "devam_ediyor": "in_progress", "engellendi": "blocked", "tamamlandı": "done"}
                status = tr_to_en_stat.get(s, s)
                break

        priority = ""
        for p in ["low", "medium", "high", "düşük", "orta", "yüksek"]:
            if p in lower:
                tr_to_en_pri = {"düşük": "low", "orta": "medium", "yüksek": "high"}
                priority = tr_to_en_pri.get(p, p)
                break

        due_date = _parse_natural_due_date(text)

        employee_id = ""
        emp_match = re.search(r"EMP-\d+", text, re.IGNORECASE)
        if emp_match:
            employee_id = emp_match.group(0).upper()
        else:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+", text)
            if email_match:
                employee = database.get_employee_by_email(email_match.group(0))
                if employee:
                    employee_id = employee["employee_id"]

        notes = ""
        notes_match = re.search(r"notes[:\s]+(.+)$|notlar[:\s]+(.+)$", text, re.IGNORECASE)
        if notes_match:
            notes = (notes_match.group(1) or notes_match.group(2)).strip()

        return _format_response(
            edit_task_tool.func(
                task_id=task_id,
                title=title,
                description=description,
                employee_id=employee_id,
                status=status,
                priority=priority,
                due_date=due_date,
                notes=notes,
            )
        )

    # 3c) Delete task
    if any(k in lower for k in ["delete task", "remove task", "görevi sil", "görevi kaldır"]):
        task_match = re.search(r"TASK-\d+", text, re.IGNORECASE)
        if not task_match:
            return "Lütfen TASK-001 formatında bir görev ID'si belirtin."
        task_id = task_match.group(0).upper()
        return _format_response(delete_task_tool.func(task_id=task_id))

    # 4) Update task status
    if any(k in lower for k in ["update task", "task status", "mark task", "görev durumu", "görevi güncelle"]):
        task_match = re.search(r"TASK-\d+", text, re.IGNORECASE)
        if not task_match:
            return "Lütfen TASK-001 formatında bir görev ID'si belirtin."

        task_id = task_match.group(0).upper()
        status = ""
        for s in ["todo", "in_progress", "blocked", "done", "yapılacak", "devam_ediyor", "engellendi", "tamamlandı"]:
            if s in lower:
                tr_to_en_stat = {"yapılacak": "todo", "devam_ediyor": "in_progress", "engellendi": "blocked", "tamamlandı": "done"}
                status = tr_to_en_stat.get(s, s)
                break

        if not status:
            return "Lütfen geçerli bir durum belirtin: todo (yapılacak), in_progress (devam ediyor), blocked (engellendi), done (tamamlandı)."

        return _format_response(update_task_status_tool.func(task_id, status, text))

    # 5) Get overdue tasks
    if any(k in lower for k in ["overdue", "gecikmiş"]):
        return _format_response(get_overdue_tasks_tool.func())

    # 6) Get tasks
    if any(k in lower for k in ["get tasks", "list tasks", "show tasks", "görevleri getir", "görevleri listele"]):
        status = ""
        for s in ["todo", "in_progress", "blocked", "done", "yapılacak", "devam_ediyor", "engellendi", "tamamlandı"]:
            if s in lower:
                tr_to_en_stat = {"yapılacak": "todo", "devam_ediyor": "in_progress", "engellendi": "blocked", "tamamlandı": "done"}
                status = tr_to_en_stat.get(s, s)
                break
        employee_id = ""
        emp_match = re.search(r"EMP-\d+", text, re.IGNORECASE)
        if emp_match:
            employee_id = emp_match.group(0).upper()
        return _format_response(get_tasks_tool.func(status=status, employee_id=employee_id))

    # 7) Workload
    if any(k in lower for k in ["workload", "employee workload", "who is busy", "capacity", "iş yükü", "kim meşgul", "kapasite"]):
        emp_match = re.search(r"EMP-\d+", text, re.IGNORECASE)
        employee_id = emp_match.group(0).upper() if emp_match else ""
        return _format_response(get_employee_workload_tool.func(employee_id=employee_id))

    # General business owner questions: return guided summary
    employees = database.get_employees(active_only=True)
    open_tasks = database.get_tasks()
    overdue = database.get_overdue_tasks()

    return (
        "Ekip operasyonlarında size yardımcı olabilirim. Bana çalışan ekleme, görev atama, "
        "görev durumu güncelleme, görev düzenleme/silme, görevleri veya gecikmiş olanları listeleme "
        "ve iş yükünü gösterme gibi komutlar verebilirsiniz.\n\n"
        f"Mevcut durum özeti: {datetime.now().strftime('%Y-%m-%d %H:%M')} itibarıyla "
        f"{len(employees)} aktif çalışanımız, {len(open_tasks)} açık görevimiz ve "
        f"{len(overdue)} gecikmiş görevimiz bulunmaktadır."
    )