import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

DATABASE_PATH = "orders.db"

# Database schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    items TEXT NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    email_type TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    assigned_to_employee_id TEXT NOT NULL,
    assigned_by TEXT,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    due_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY(assigned_to_employee_id) REFERENCES employees(employee_id)
);
"""

# Mock data
MOCK_ORDERS = [
    {
        "order_id": "ORD-001",
        "customer_name": "John Smith",
        "customer_email": "john.smith@email.com",
        "items": json.dumps([
            {"name": "Laptop", "quantity": 1, "price": 1200},
            {"name": "Mouse", "quantity": 2, "price": 25}
        ]),
        "total_amount": 1250.00,
        "status": "delivered",
        "notes": "Delivered on time"
    },
    {
        "order_id": "ORD-002",
        "customer_name": "Sarah Johnson",
        "customer_email": "sarah.johnson@email.com",
        "items": json.dumps([
            {"name": "Monitor", "quantity": 1, "price": 350},
            {"name": "Keyboard", "quantity": 1, "price": 120}
        ]),
        "total_amount": 470.00,
        "status": "shipped",
        "notes": "In transit"
    },
    {
        "order_id": "ORD-003",
        "customer_name": "Michael Chen",
        "customer_email": "m.chen@email.com",
        "items": json.dumps([
            {"name": "USB-C Cable", "quantity": 5, "price": 15}
        ]),
        "total_amount": 75.00,
        "status": "processing",
        "notes": "Being packed"
    },
    {
        "order_id": "ORD-004",
        "customer_name": "Emma Wilson",
        "customer_email": "emma.w@email.com",
        "items": json.dumps([
            {"name": "Headphones", "quantity": 1, "price": 200},
            {"name": "Phone Case", "quantity": 3, "price": 15}
        ]),
        "total_amount": 245.00,
        "status": "pending",
        "notes": "Awaiting payment confirmation"
    },
    {
        "order_id": "ORD-005",
        "customer_name": "David Martinez",
        "customer_email": "david.m@email.com",
        "items": json.dumps([
            {"name": "Webcam", "quantity": 1, "price": 180}
        ]),
        "total_amount": 180.00,
        "status": "delivered",
        "notes": "Delivered with signature"
    }
]

MOCK_EMPLOYEES = [
    {
        "employee_id": "EMP-001",
        "full_name": "Aylin Demir",
        "email": "aylin.demir@smallbiz.com",
        "role": "Operations Lead",
    },
    {
        "employee_id": "EMP-002",
        "full_name": "Mert Kaya",
        "email": "mert.kaya@smallbiz.com",
        "role": "Warehouse Specialist",
    },
    {
        "employee_id": "EMP-003",
        "full_name": "Selin Aras",
        "email": "selin.aras@smallbiz.com",
        "role": "Customer Success",
    },
]

MOCK_TASKS = [
    {
        "task_id": "TASK-001",
        "title": "Confirm payment for ORD-004",
        "description": "Call the customer and verify payment confirmation details.",
        "assigned_to_employee_id": "EMP-003",
        "assigned_by": "Owner",
        "status": "in_progress",
        "priority": "high",
        "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "notes": "Pending callback window",
    },
    {
        "task_id": "TASK-002",
        "title": "Pack ORD-003 items",
        "description": "Prepare parcel and verify SKU counts before handoff.",
        "assigned_to_employee_id": "EMP-002",
        "assigned_by": "Owner",
        "status": "todo",
        "priority": "medium",
        "due_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "notes": "",
    },
]


def init_database():
    """Initialize the database with schema and mock data."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript(SCHEMA)
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        # Insert mock data
        for order in MOCK_ORDERS:
            cursor.execute(
                """INSERT INTO orders 
                (order_id, customer_name, customer_email, items, total_amount, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    order["order_id"],
                    order["customer_name"],
                    order["customer_email"],
                    order["items"],
                    order["total_amount"],
                    order["status"],
                    order["notes"]
                )
            )
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        for employee in MOCK_EMPLOYEES:
            cursor.execute(
                """INSERT INTO employees
                (employee_id, full_name, email, role)
                VALUES (?, ?, ?, ?)""",
                (
                    employee["employee_id"],
                    employee["full_name"],
                    employee["email"],
                    employee["role"],
                )
            )
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        for task in MOCK_TASKS:
            cursor.execute(
                """INSERT INTO tasks
                (task_id, title, description, assigned_to_employee_id, assigned_by, status, priority, due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task["task_id"],
                    task["title"],
                    task["description"],
                    task["assigned_to_employee_id"],
                    task["assigned_by"],
                    task["status"],
                    task["priority"],
                    task["due_date"],
                    task["notes"],
                )
            )
        conn.commit()
    
    conn.close()


def get_connection():
    """Get a database connection."""
    return sqlite3.connect(DATABASE_PATH)


def get_order(order_id: str) -> Optional[Dict]:
    """Get a single order by ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_all_orders() -> List[Dict]:
    """Get all orders."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_orders_by_status(status: str) -> List[Dict]:
    """Get orders filtered by status."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_orders_by_customer_email(email: str) -> List[Dict]:
    """Get orders by customer email."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE customer_email = ? ORDER BY created_at DESC", (email,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def create_order(
    order_id: str,
    customer_name: str,
    customer_email: str,
    items: List[Dict],
    total_amount: float,
    notes: str = ""
) -> Optional[Dict]:
    """Create a new order."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """INSERT INTO orders 
            (order_id, customer_name, customer_email, items, total_amount, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                order_id,
                customer_name,
                customer_email,
                json.dumps(items),
                total_amount,
                "pending",
                notes
            )
        )
        conn.commit()
        conn.close()
        return get_order(order_id)
    except sqlite3.IntegrityError:
        conn.close()
        return None


def update_order_status(order_id: str, status: str, notes: str = "") -> Optional[Dict]:
    """Update order status."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """UPDATE orders 
        SET status = ?, updated_at = CURRENT_TIMESTAMP, notes = ?
        WHERE order_id = ?""",
        (status, notes, order_id)
    )
    conn.commit()
    conn.close()
    
    return get_order(order_id)


def log_email(order_id: str, customer_email: str, email_type: str, status: str = "sent"):
    """Log an email sent for an order."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO email_logs 
        (order_id, customer_email, email_type, status)
        VALUES (?, ?, ?, ?)""",
        (order_id, customer_email, email_type, status)
    )
    conn.commit()
    conn.close()


def get_email_logs(order_id: str) -> List[Dict]:
    """Get email logs for an order."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM email_logs WHERE order_id = ? ORDER BY sent_at DESC", (order_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def _next_employee_id() -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM employees")
    max_id = cursor.fetchone()[0]
    conn.close()
    return f"EMP-{max_id + 1:03d}"


def _next_task_id() -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM tasks")
    max_id = cursor.fetchone()[0]
    conn.close()
    return f"TASK-{max_id + 1:03d}"


def add_employee(full_name: str, email: str, role: str) -> Optional[Dict]:
    """Add a new active employee."""
    conn = get_connection()
    cursor = conn.cursor()
    employee_id = _next_employee_id()

    try:
        cursor.execute(
            """INSERT INTO employees
            (employee_id, full_name, email, role, is_active)
            VALUES (?, ?, ?, ?, 1)""",
            (employee_id, full_name, email, role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return None

    conn.close()
    return get_employee(employee_id)


def get_employee(employee_id: str) -> Optional[Dict]:
    """Get one employee by employee ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_employee_by_email(email: str) -> Optional[Dict]:
    """Get one employee by email."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employees WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_employees(active_only: bool = True) -> List[Dict]:
    """Get all employees."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if active_only:
        cursor.execute("SELECT * FROM employees WHERE is_active = 1 ORDER BY created_at DESC")
    else:
        cursor.execute("SELECT * FROM employees ORDER BY created_at DESC")

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def assign_task(
    title: str,
    description: str,
    assigned_to_employee_id: str,
    assigned_by: str = "Owner",
    priority: str = "medium",
    due_date: str = "",
    notes: str = "",
) -> Optional[Dict]:
    """Assign a task to an employee."""
    valid_priorities = ["low", "medium", "high"]
    if priority not in valid_priorities:
        priority = "medium"

    if not get_employee(assigned_to_employee_id):
        return None

    conn = get_connection()
    cursor = conn.cursor()
    task_id = _next_task_id()

    cursor.execute(
        """INSERT INTO tasks
        (task_id, title, description, assigned_to_employee_id, assigned_by, status, priority, due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_id,
            title,
            description,
            assigned_to_employee_id,
            assigned_by,
            "todo",
            priority,
            due_date if due_date else None,
            notes,
        )
    )
    conn.commit()
    conn.close()

    return get_task(task_id)


def get_task(task_id: str) -> Optional[Dict]:
    """Get one task by task ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_task_status(task_id: str, status: str, notes: str = "") -> Optional[Dict]:
    """Update task status and notes."""
    valid_statuses = ["todo", "in_progress", "blocked", "done"]
    if status not in valid_statuses:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE tasks
        SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE task_id = ?""",
        (status, notes, task_id)
    )
    conn.commit()
    conn.close()

    return get_task(task_id)


def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    assigned_to_employee_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Dict]:
    """Edit task fields. Only provided fields are updated."""
    task = get_task(task_id)
    if not task:
        return None

    valid_statuses = ["todo", "in_progress", "blocked", "done"]
    valid_priorities = ["low", "medium", "high"]

    if assigned_to_employee_id and not get_employee(assigned_to_employee_id):
        return None

    if status and status not in valid_statuses:
        return None

    if priority and priority not in valid_priorities:
        return None

    update_fields = []
    params = []

    if title is not None:
        update_fields.append("title = ?")
        params.append(title)
    if description is not None:
        update_fields.append("description = ?")
        params.append(description)
    if assigned_to_employee_id is not None:
        update_fields.append("assigned_to_employee_id = ?")
        params.append(assigned_to_employee_id)
    if status is not None:
        update_fields.append("status = ?")
        params.append(status)
    if priority is not None:
        update_fields.append("priority = ?")
        params.append(priority)
    if due_date is not None:
        update_fields.append("due_date = ?")
        params.append(due_date if due_date else None)
    if notes is not None:
        update_fields.append("notes = ?")
        params.append(notes)

    if not update_fields:
        return task

    update_fields.append("updated_at = CURRENT_TIMESTAMP")

    conn = get_connection()
    cursor = conn.cursor()
    query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE task_id = ?"
    params.append(task_id)
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()

    return get_task(task_id)


def delete_task(task_id: str) -> bool:
    """Delete a task by task ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_tasks(status: Optional[str] = None, employee_id: Optional[str] = None) -> List[Dict]:
    """Get tasks with optional status and employee filters."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM tasks"
    params = []
    clauses = []

    if status:
        clauses.append("status = ?")
        params.append(status)

    if employee_id:
        clauses.append("assigned_to_employee_id = ?")
        params.append(employee_id)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY created_at DESC"
    cursor.execute(query, tuple(params))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_overdue_tasks() -> List[Dict]:
    """Get tasks past due date that are not done."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """SELECT * FROM tasks
        WHERE due_date IS NOT NULL
        AND datetime(due_date) < datetime('now')
        AND status != 'done'
        ORDER BY due_date ASC"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_employee_workload(employee_id: Optional[str] = None) -> List[Dict]:
    """Get workload summary per employee."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    base_query = """
    SELECT
        e.employee_id,
        e.full_name,
        e.email,
        e.role,
        COUNT(t.task_id) as total_tasks,
        SUM(CASE WHEN t.status = 'todo' THEN 1 ELSE 0 END) as todo_tasks,
        SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_tasks,
        SUM(CASE WHEN t.status = 'blocked' THEN 1 ELSE 0 END) as blocked_tasks,
        SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as done_tasks
    FROM employees e
    LEFT JOIN tasks t ON e.employee_id = t.assigned_to_employee_id
    WHERE e.is_active = 1
    """

    params = []
    if employee_id:
        base_query += " AND e.employee_id = ?"
        params.append(employee_id)

    base_query += " GROUP BY e.employee_id, e.full_name, e.email, e.role ORDER BY total_tasks DESC"

    cursor.execute(base_query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# Initialize database on import
init_database()
