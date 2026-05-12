import streamlit as st
import pandas as pd
import database
from dotenv import load_dotenv
import os

from agents.order_agent import create_order_agent
from agents.workflow_manager_agent import (
    create_workflow_manager_agent,
    run_workflow_manager_agent,
)

load_dotenv()

st.set_page_config(
    page_title="Workflow Manager",
    page_icon="🧭",
    layout="wide",
)

if "order_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    st.session_state.order_agent = create_order_agent(api_key) if api_key else None

if "workflow_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    st.session_state.workflow_agent = create_workflow_manager_agent(
        api_key=api_key,
        order_agent=st.session_state.order_agent,
    )

if "workflow_messages" not in st.session_state:
    st.session_state.workflow_messages = []


def _send_workflow_prompt(prompt: str):
    st.session_state.workflow_messages.append({"role": "user", "content": prompt})
    response = run_workflow_manager_agent(st.session_state.workflow_agent, prompt)
    st.session_state.workflow_messages.append({"role": "assistant", "content": response})

with st.sidebar:
    st.title("Navigation")
    if st.button("💬 Back to Chat", use_container_width=True):
        st.switch_page("main.py")
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/dashboard.py")
    if st.button("📦 Orders", use_container_width=True):
        st.switch_page("pages/order_inventory.py")

    st.divider()
    view_option = st.radio(
        "Workflow View",
        ["Workflow Dashboard", "Employees", "Tasks", "Workflow Agent"],
    )

st.title("🧭 Workflow Manager")

if view_option == "Workflow Dashboard":
    employees = database.get_employees(active_only=True)
    tasks = database.get_tasks()
    overdue = database.get_overdue_tasks()
    workload = database.get_employee_workload()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Employees", len(employees))
    col2.metric("Total Tasks", len(tasks))
    col3.metric("Overdue Tasks", len(overdue))
    col4.metric("Tasks In Progress", len([t for t in tasks if t["status"] == "in_progress"]))

    st.divider()

    if workload:
        chart_df = pd.DataFrame(
            [
                {
                    "Employee": item["full_name"],
                    "Total": item["total_tasks"],
                    "In Progress": item["in_progress_tasks"],
                    "Blocked": item["blocked_tasks"],
                }
                for item in workload
            ]
        )
        st.subheader("Team Workload")
        st.bar_chart(chart_df.set_index("Employee")[["Total", "In Progress", "Blocked"]])

if view_option == "Employees":
    st.subheader("Employees")

    with st.form("add_worker_form"):
        col1, col2, col3 = st.columns(3)
        full_name = col1.text_input("Full Name")
        email = col2.text_input("Email")
        role = col3.text_input("Role", value="Staff")
        submitted = st.form_submit_button("Add Worker", type="primary")

        if submitted:
            worker = database.add_employee(full_name=full_name, email=email, role=role)
            if worker:
                st.success(f"Added {worker['full_name']} ({worker['employee_id']})")
            else:
                st.error("Could not add worker. Email may already exist.")

    employees = database.get_employees(active_only=True)
    if employees:
        st.dataframe(pd.DataFrame(employees), use_container_width=True)
    else:
        st.info("No employees found.")

if view_option == "Tasks":
    st.subheader("Task Management")

    employees = database.get_employees(active_only=True)
    employee_options = {f"{e['full_name']} ({e['email']})": e for e in employees}

    with st.form("assign_task_form"):
        title = st.text_input("Task Title")
        description = st.text_area("Description")
        selected_label = st.selectbox("Assign To", options=list(employee_options.keys()) if employee_options else ["No employees"]) 
        priority = st.selectbox("Priority", ["low", "medium", "high"])
        due_date = st.text_input("Due Date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
        submitted = st.form_submit_button("Assign Task", type="primary")

        if submitted and employee_options:
            emp = employee_options[selected_label]
            task = database.assign_task(
                title=title,
                description=description,
                assigned_to_employee_id=emp["employee_id"],
                assigned_by="Business Owner",
                priority=priority,
                due_date=due_date,
            )
            if task:
                st.success(f"Task {task['task_id']} assigned to {emp['full_name']}")
            else:
                st.error("Task assignment failed.")

    st.divider()

    tasks = database.get_tasks()
    if tasks:
        st.dataframe(pd.DataFrame(tasks), use_container_width=True)

        st.subheader("Update Task Status")
        col1, col2, col3 = st.columns(3)
        task_id = col1.text_input("Task ID", placeholder="TASK-001")
        new_status = col2.selectbox("New Status", ["todo", "in_progress", "blocked", "done"])
        notes = col3.text_input("Notes")

        if st.button("Update Task", type="primary"):
            updated = database.update_task_status(task_id=task_id, status=new_status, notes=notes)
            if updated:
                st.success(f"Updated {task_id} to {new_status}")
            else:
                st.error("Could not update task.")

        st.subheader("Edit Task")
        task_ids = [t["task_id"] for t in tasks]
        with st.form("edit_task_form"):
            edit_col1, edit_col2 = st.columns(2)
            edit_task_id = edit_col1.selectbox("Task to Edit", options=task_ids)
            edit_status = edit_col2.selectbox(
                "Edit Status",
                ["", "todo", "in_progress", "blocked", "done"],
                help="Leave empty to keep current status.",
            )

            edit_col3, edit_col4 = st.columns(2)
            edit_priority = edit_col3.selectbox(
                "Edit Priority",
                ["", "low", "medium", "high"],
                help="Leave empty to keep current priority.",
            )
            edit_due_date = edit_col4.text_input("Edit Due Date (YYYY-MM-DD HH:MM:SS)")

            edit_title = st.text_input("Edit Title")
            edit_description = st.text_area("Edit Description")
            edit_notes = st.text_area("Edit Notes")

            assignee_options = {f"{e['employee_id']} - {e['full_name']}": e["employee_id"] for e in employees}
            selected_assignee = st.selectbox(
                "Reassign To",
                options=["Keep Current"] + list(assignee_options.keys()),
            )

            edit_submitted = st.form_submit_button("Save Task Changes", type="primary")
            if edit_submitted:
                reassigned_employee_id = ""
                if selected_assignee != "Keep Current":
                    reassigned_employee_id = assignee_options[selected_assignee]

                updated_task = database.update_task(
                    task_id=edit_task_id,
                    title=edit_title or None,
                    description=edit_description or None,
                    assigned_to_employee_id=reassigned_employee_id or None,
                    status=edit_status or None,
                    priority=edit_priority or None,
                    due_date=edit_due_date if edit_due_date else None,
                    notes=edit_notes or None,
                )
                if updated_task:
                    st.success(f"Updated {edit_task_id}")
                else:
                    st.error("Failed to edit task. Check input values.")

        st.subheader("Delete Task")
        del_col1, del_col2 = st.columns([2, 1])
        delete_task_id = del_col1.selectbox("Task to Delete", options=task_ids, key="delete_task_select")
        if del_col2.button("Delete Selected Task", type="secondary"):
            deleted = database.delete_task(delete_task_id)
            if deleted:
                st.success(f"Deleted {delete_task_id}")
            else:
                st.error("Task not found.")
    else:
        st.info("No tasks found.")

    overdue = database.get_overdue_tasks()
    st.subheader("Overdue Tasks")
    if overdue:
        st.dataframe(pd.DataFrame(overdue), use_container_width=True)
    else:
        st.success("No overdue tasks.")

    st.subheader("Employee Workload")
    workload = database.get_employee_workload()
    if workload:
        st.dataframe(pd.DataFrame(workload), use_container_width=True)

if view_option == "Workflow Agent":
    st.subheader("Workflow Manager Agent")
    st.info(
        "Ask the business workflow agent to add workers, assign tasks, update statuses, "
        "get tasks, get overdue tasks, and get employee workload."
    )

    st.caption(
        "Example: assign task title Follow up ORD-003 to selin.aras@smallbiz.com high due next friday"
    )

    st.subheader("Quick Actions")
    qa_col1, qa_col2, qa_col3 = st.columns(3)
    if qa_col1.button("List Employees", use_container_width=True):
        _send_workflow_prompt("get employees")
    if qa_col2.button("Show Overdue Tasks", use_container_width=True):
        _send_workflow_prompt("get overdue tasks")
    if qa_col3.button("Show Team Workload", use_container_width=True):
        _send_workflow_prompt("get employee workload")

    employees = database.get_employees(active_only=True)
    if employees:
        st.subheader("Employee-Specific Prompts")
        emp_lookup = {
            f"{e['full_name']} ({e['employee_id']})": e
            for e in employees
        }
        selected_emp_label = st.selectbox("Select Employee", options=list(emp_lookup.keys()))
        selected_emp = emp_lookup[selected_emp_label]

        emp_col1, emp_col2, emp_col3 = st.columns(3)
        if emp_col1.button("Get Employee Workload", use_container_width=True):
            _send_workflow_prompt(f"get employee workload for {selected_emp['employee_id']}")

        if emp_col2.button("Get Employee Tasks", use_container_width=True):
            _send_workflow_prompt(f"show tasks for {selected_emp['employee_id']}")

        if emp_col3.button("Assign Follow-up For Tomorrow", use_container_width=True):
            _send_workflow_prompt(
                f"assign task title Follow up customer tickets to {selected_emp['email']} medium due tomorrow"
            )

        st.caption(
            f"Prompt target: {selected_emp['full_name']} | {selected_emp['email']}"
        )

    for message in st.session_state.workflow_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Ask workflow manager...")
    if user_input:
        st.session_state.workflow_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.spinner("Workflow agent is thinking..."):
            response = run_workflow_manager_agent(st.session_state.workflow_agent, user_input)

        st.session_state.workflow_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)
