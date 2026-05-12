import streamlit as st
import pandas as pd
import json
from datetime import datetime
import database
import email_service
from agents.order_agent import create_order_agent, run_order_agent
import os
from dotenv import load_dotenv

# Load .env for API keys and SMTP credentials
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Order Tracking",
    page_icon="📦",
    layout="wide"
)

# --- Initialize Session State ---
if "order_agent" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            st.session_state.order_agent = create_order_agent(api_key)
        except Exception as e:
            st.session_state.order_agent = None
            st.warning(f"⚠️ Could not initialize Order Agent: {str(e)}")
    else:
        st.session_state.order_agent = None
        st.warning("⚠️ GOOGLE_API_KEY not set. Agent features will be disabled.")

# --- Sidebar ---
with st.sidebar:
    st.title("Navigation")
    
    if st.button("💬 Back to Chat", use_container_width=True):
        st.switch_page("main.py")
    
    st.divider()
    
    # View options
    view_option = st.radio(
        "Select View",
        ["Dashboard", "All Orders", "Order Details", "Order Agent"]
    )
    
    # Email sending mode
    if "real_email" not in st.session_state:
        st.session_state.real_email = False

    st.session_state.real_email = st.checkbox(
        "Enable real email sending (requires SENDER_EMAIL & SENDER_PASSWORD in .env)",
        value=st.session_state.real_email
    )

# --- Main Content ---
st.title("📦 Order Tracking System")

if view_option == "Dashboard":
    st.header("Dashboard")
    
    # Get statistics
    all_orders = database.get_all_orders()
    
    if all_orders:
        col1, col2, col3, col4 = st.columns(4)
        
        total_orders = len(all_orders)
        total_revenue = sum(order["total_amount"] for order in all_orders)
        delivered_count = len([o for o in all_orders if o["status"] == "delivered"])
        pending_count = len([o for o in all_orders if o["status"] == "pending"])
        
        col1.metric("Total Orders", total_orders)
        col2.metric("Total Revenue", f"${total_revenue:.2f}")
        col3.metric("Delivered", delivered_count)
        col4.metric("Pending", pending_count)
        
        st.divider()
        
        # Status breakdown
        status_breakdown = {}
        for order in all_orders:
            status = order["status"]
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Orders by Status")
            status_df = pd.DataFrame(
                list(status_breakdown.items()),
                columns=["Status", "Count"]
            )
            st.bar_chart(status_df.set_index("Status"))
        
        with col2:
            st.subheader("Recent Orders")
            recent_orders = all_orders[:5]
            recent_df = pd.DataFrame([
                {
                    "Order ID": o["order_id"],
                    "Customer": o["customer_name"],
                    "Amount": f"${o['total_amount']:.2f}",
                    "Status": o["status"],
                    "Date": o["created_at"]
                }
                for o in recent_orders
            ])
            st.dataframe(recent_df, use_container_width=True)
    else:
        st.info("No orders found in the system")

elif view_option == "All Orders":
    st.header("All Orders")
    
    # Filter options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "pending", "processing", "shipped", "delivered"]
        )
    
    with col2:
        sort_option = st.selectbox(
            "Sort by",
            ["Latest First", "Oldest First", "Highest Amount", "Lowest Amount"]
        )
    
    # Get orders
    if status_filter == "All":
        orders = database.get_all_orders()
    else:
        orders = database.get_orders_by_status(status_filter)
    
    # Sort
    if sort_option == "Latest First":
        orders.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_option == "Oldest First":
        orders.sort(key=lambda x: x["created_at"])
    elif sort_option == "Highest Amount":
        orders.sort(key=lambda x: x["total_amount"], reverse=True)
    else:  # Lowest Amount
        orders.sort(key=lambda x: x["total_amount"])
    
    # Display orders
    if orders:
        orders_data = []
        for order in orders:
            items = json.loads(order["items"])
            items_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in items])
            
            orders_data.append({
                "Order ID": order["order_id"],
                "Customer": order["customer_name"],
                "Email": order["customer_email"],
                "Items": items_str,
                "Amount": f"${order['total_amount']:.2f}",
                "Status": order["status"],
                "Date": order["created_at"]
            })
        
        df = pd.DataFrame(orders_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No orders found")

elif view_option == "Order Details":
    st.header("Order Details")
    
    order_id = st.text_input("Enter Order ID", placeholder="ORD-001")
    
    if order_id:
        order = database.get_order(order_id)
        
        if order:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(f"Order {order_id}")
                
                # Order info
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.write(f"**Customer Name:** {order['customer_name']}")
                    st.write(f"**Customer Email:** {order['customer_email']}")
                    st.write(f"**Created:** {order['created_at']}")
                
                with info_col2:
                    st.write(f"**Status:** {order['status'].upper()}")
                    st.write(f"**Updated:** {order['updated_at']}")
                    st.write(f"**Total Amount:** ${order['total_amount']:.2f}")
                
                if order['notes']:
                    st.write(f"**Notes:** {order['notes']}")
                
                st.divider()
                
                # Items
                st.subheader("Items")
                items = json.loads(order["items"])
                items_df = pd.DataFrame(items)
                st.dataframe(items_df, use_container_width=True)
            
            with col2:
                st.subheader("Actions")
                
                # Update status
                new_status = st.selectbox(
                    "Update Status",
                    ["pending", "processing", "shipped", "delivered"]
                )
                notes = st.text_area("Add Notes", height=100)
                
                if st.button("Update Order", use_container_width=True, type="primary"):
                    updated_order = database.update_order_status(order_id, new_status, notes)
                    if updated_order:
                        st.success(f"✅ Order {order_id} updated to {new_status}")
                        
                        # Send email notification (use real email if enabled in sidebar)
                        if new_status == "shipped":
                            email_service.send_order_notification(
                                updated_order,
                                "shipped",
                                use_real=bool(st.session_state.get("real_email", False)),
                            )
                            st.info("📧 Shipped notification sent")
                        elif new_status == "delivered":
                            email_service.send_order_notification(
                                updated_order,
                                "delivered",
                                use_real=bool(st.session_state.get("real_email", False)),
                            )
                            st.info("📧 Delivery notification sent")
                    else:
                        st.error("Failed to update order")
                
                st.divider()
                
                # Email logs
                st.subheader("Email History")
                email_logs = database.get_email_logs(order_id)
                if email_logs:
                    logs_df = pd.DataFrame([
                        {
                            "Type": log["email_type"],
                            "Status": log["status"],
                            "Sent": log["sent_at"]
                        }
                        for log in email_logs
                    ])
                    st.dataframe(logs_df, use_container_width=True)
                else:
                    st.info("No emails sent for this order")
        else:
            st.error(f"Order {order_id} not found")


elif view_option == "Order Agent":
    st.header("Order Tracking Agent")
    
    if st.session_state.order_agent is None:
        st.error("❌ Order Agent is not initialized. Please set GOOGLE_API_KEY in your environment.")
    else:
        st.info(
            "💡 **How to use:** Ask questions about orders, customers, or order statuses. "
            "The agent will help you find information and manage orders."
        )
        
        # Chat interface
        if "agent_messages" not in st.session_state:
            st.session_state.agent_messages = []
        
        # Display chat history
        for message in st.session_state.agent_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # User input
        user_input = st.chat_input("Ask about orders...")
        
        if user_input:
            # Add user message
            st.session_state.agent_messages.append({"role": "user", "content": user_input})
            
            with st.chat_message("user"):
                st.write(user_input)
            
            # Get agent response
            with st.spinner("Agent is thinking..."):
                response = run_order_agent(st.session_state.order_agent, user_input)
            
            # Add assistant message
            st.session_state.agent_messages.append({"role": "assistant", "content": response})
            
            with st.chat_message("assistant"):
                st.write(response)
