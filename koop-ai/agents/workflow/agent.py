"""
Agent 5 — İş Akışı & Çalışan Takibi
"""
from datetime import date, datetime
from sqlalchemy.orm import Session

from database.models import Employee, Task


def add_employee(
    db: Session,
    name: str,
    role: str,
    department: str,
) -> dict:
    """Yeni çalışan ekle."""
    employee = Employee(name=name, role=role, department=department)
    db.add(employee)
    db.commit()
    return {"success": True, "employee": employee.to_dict()}


def get_employees(db: Session) -> list:
    """Tüm çalışanları getir."""
    employees = db.query(Employee).all()
    result = []
    for emp in employees:
        emp_dict = emp.to_dict()
        tasks = db.query(Task).filter(Task.employee_id == emp.id).all()
        emp_dict["task_count"] = len(tasks)
        emp_dict["pending_tasks"] = sum(1 for t in tasks if t.status == "pending")
        emp_dict["in_progress_tasks"] = sum(1 for t in tasks if t.status == "in_progress")
        emp_dict["done_tasks"] = sum(1 for t in tasks if t.status == "done")
        result.append(emp_dict)
    return result


def assign_task(
    db: Session,
    employee_id: int,
    title: str,
    description: str,
    due_date: date,
) -> dict:
    """Çalışana görev ata."""
    employee = db.get(Employee, employee_id)
    if not employee:
        return {"success": False, "error": "Çalışan bulunamadı."}

    task = Task(
        employee_id=employee_id,
        title=title,
        description=description,
        due_date=due_date,
        status="pending",
    )
    db.add(task)
    db.commit()
    return {"success": True, "task": task.to_dict()}


def update_task_status(db: Session, task_id: int, new_status: str) -> dict:
    """Görev durumunu güncelle."""
    task = db.get(Task, task_id)
    if not task:
        return {"success": False, "error": "Görev bulunamadı."}

    valid_statuses = ["pending", "in_progress", "done"]
    if new_status not in valid_statuses:
        return {"success": False, "error": f"Geçersiz durum. Olası değerler: {valid_statuses}"}

    task.status = new_status
    db.commit()
    return {"success": True, "task": task.to_dict()}


def get_tasks(db: Session, employee_id: int = None, status: str = None) -> list:
    """Görevleri filtreli getir."""
    query = db.query(Task)
    if employee_id:
        query = query.filter(Task.employee_id == employee_id)
    if status:
        query = query.filter(Task.status == status)
    tasks = query.order_by(Task.due_date.asc()).all()
    return [t.to_dict() for t in tasks]


def get_overdue_tasks(db: Session) -> list:
    """Gecikmiş görevleri getir (due_date < bugün ve tamamlanmamış)."""
    today = date.today()
    tasks = (
        db.query(Task)
        .filter(Task.due_date < today, Task.status != "done")
        .order_by(Task.due_date.asc())
        .all()
    )
    return [t.to_dict() for t in tasks]


def get_employee_workload(db: Session) -> list:
    """Her çalışanın görev yükünü hesapla."""
    employees = db.query(Employee).all()
    workload = []
    for emp in employees:
        tasks = db.query(Task).filter(Task.employee_id == emp.id).all()
        workload.append({
            "employee_id": emp.id,
            "employee_name": emp.name,
            "department": emp.department,
            "total_tasks": len(tasks),
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
            "done": sum(1 for t in tasks if t.status == "done"),
            "overdue": sum(
                1 for t in tasks
                if t.due_date and t.due_date < date.today() and t.status != "done"
            ),
        })
    return sorted(workload, key=lambda x: x["total_tasks"], reverse=True)
