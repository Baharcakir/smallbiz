import streamlit as st
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load .env so pages can access API keys / SMTP creds when opened directly
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Sidebar ---
with st.sidebar:

    st.title("Navigation")

    if st.button("💬 Back to Chat", use_container_width=True):
        st.switch_page("main.py")
    
    if st.button("📦 View Orders", use_container_width=True):
        st.switch_page("pages/order_inventory.py")

    if st.button("🧭 Workflow", use_container_width=True):
        st.switch_page("pages/workflow_manager.py")

# --- Dashboard Header ---
st.title("📊 AI Operations Dashboard")
st.caption("Fake analytics overview for your Gemini-style assistant")

# --- Top Metrics ---
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Conversations", "12,483", "+12%")
col2.metric("Active Users", "1,284", "+8%")
col3.metric("Avg Response Time", "1.2s", "-0.3s")
col4.metric("Satisfaction Score", "94%", "+2%")

st.divider()

# --- Charts Section ---
chart_col1, chart_col2 = st.columns(2)

# Fake conversation data
dates = pd.date_range(start="2025-01-01", periods=30)

conversation_data = pd.DataFrame({
    "Date": dates,
    "Conversations": np.random.randint(100, 500, size=30)
})

agent_data = pd.DataFrame({
    "Agent": [
        "General Assistant",
        "Stock Manager",
        "Order Tracker",
        "Data Analyst",
        "Copywriter"
    ],
    "Usage": [45, 20, 15, 12, 8]
})

with chart_col1:
    st.subheader("Daily Conversations")
    st.line_chart(
        conversation_data.set_index("Date")
    )

with chart_col2:
    st.subheader("Agent Usage Distribution")
    st.bar_chart(
        agent_data.set_index("Agent")
    )

st.divider()

# --- Recent Activity Table ---
st.subheader("Recent Activity")

activity_df = pd.DataFrame({
    "User": ["Alice", "Bob", "Charlie", "David", "Emma"],
    "Agent Used": [
        "Data Analyst",
        "Copywriter",
        "General Assistant",
        "Stock Manager",
        "Order Tracker"
    ],
    "Request": [
        "Analyze sales trends",
        "Write marketing copy",
        "General help",
        "Inventory update",
        "Track shipment"
    ],
    "Status": [
        "Completed",
        "Completed",
        "In Progress",
        "Completed",
        "Pending"
    ]
})

st.dataframe(activity_df, use_container_width=True)

st.divider()

# --- Footer ---
st.caption("Demo dashboard with mock analytics")