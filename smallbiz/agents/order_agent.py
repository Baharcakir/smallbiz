import json
from typing import List, Optional
from langchain_core.tools import tool
import database
import os
try:
    import google.generativeai as genai
except Exception:
    genai = None
import email_service


# Define tools for the agent
@tool
def get_order_status(order_id: str) -> str:
    """Get the status of a specific order by order ID."""
    order = database.get_order(order_id)
    if order:
        return json.dumps({
            "order_id": order["order_id"],
            "customer_name": order["customer_name"],
            "status": order["status"],
            "total_amount": order["total_amount"],
            "created_at": order["created_at"],
            "updated_at": order["updated_at"],
            "notes": order["notes"]
        })
    return f"Order {order_id} not found"


@tool
def get_customer_orders(email: str) -> str:
    """Get all orders for a customer by email address."""
    orders = database.get_orders_by_customer_email(email)
    if orders:
        result = []
        for order in orders:
            result.append({
                "order_id": order["order_id"],
                "status": order["status"],
                "total_amount": order["total_amount"],
                "created_at": order["created_at"]
            })
        return json.dumps(result)
    return f"No orders found for customer {email}"


@tool
def get_orders_by_status_filter(status: str) -> str:
    """Get all orders with a specific status (pending, processing, shipped, delivered)."""
    valid_statuses = ["pending", "processing", "shipped", "delivered"]
    if status.lower() not in valid_statuses:
        return f"Invalid status. Valid statuses are: {', '.join(valid_statuses)}"
    
    orders = database.get_orders_by_status(status.lower())
    if orders:
        result = []
        for order in orders:
            result.append({
                "order_id": order["order_id"],
                "customer_name": order["customer_name"],
                "total_amount": order["total_amount"],
                "created_at": order["created_at"]
            })
        return json.dumps(result)
    return f"No orders found with status: {status}"


@tool
def update_order_status_tool(order_id: str, new_status: str, notes: str = "") -> str:
    """Update the status of an order."""
    valid_statuses = ["pending", "processing", "shipped", "delivered"]
    if new_status.lower() not in valid_statuses:
        return f"Invalid status. Valid statuses are: {', '.join(valid_statuses)}"
    
    updated_order = database.update_order_status(order_id, new_status.lower(), notes)
    if updated_order:
        # Send notification emails for important status changes
        try:
            # Determine whether to attempt real sending: explicit env var or SMTP creds
            enable_env = os.getenv("ENABLE_REAL_EMAIL", "").lower() in ("1", "true", "yes")
            has_creds = bool(os.getenv("SENDER_EMAIL")) and bool(os.getenv("SENDER_PASSWORD"))
            use_real = enable_env or has_creds

            if new_status.lower() == "shipped":
                email_service.send_order_notification(updated_order, "shipped", use_real=use_real)
            elif new_status.lower() == "delivered":
                email_service.send_order_notification(updated_order, "delivered", use_real=use_real)
            elif new_status.lower() == "pending":
                # treat newly pending orders as created for notification purposes
                email_service.send_order_notification(updated_order, "created", use_real=use_real)
        except Exception:
            # don't raise on email failures from the agent tool
            pass

        return f"Order {order_id} status updated to {new_status.lower()}"
    return f"Failed to update order {order_id}"


@tool
def get_all_orders_summary() -> str:
    """Get a summary of all orders in the system."""
    orders = database.get_all_orders()
    if orders:
        total_revenue = sum(order["total_amount"] for order in orders)
        status_breakdown = {}
        for order in orders:
            status = order["status"]
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        return json.dumps({
            "total_orders": len(orders),
            "total_revenue": total_revenue,
            "status_breakdown": status_breakdown
        })
    return "No orders found in the system"


@tool
def get_order_items(order_id: str) -> str:
    """Get detailed items for a specific order."""
    order = database.get_order(order_id)
    if order:
        items = json.loads(order["items"])
        return json.dumps({
            "order_id": order_id,
            "items": items,
            "total_amount": order["total_amount"]
        })
    return f"Order {order_id} not found"


# Initialize tools
# Initialize tools list
tools_list = [
    get_order_status,
    get_customer_orders,
    get_orders_by_status_filter,
    update_order_status_tool,
    get_all_orders_summary,
    get_order_items
]


def create_order_agent(api_key: str):
    """Create and return the order tracking agent."""
    # Configure google generative API client if available
    if not api_key or genai is None:
        return None

    # normalize key
    api_key = api_key.strip() if isinstance(api_key, str) else api_key
    genai.configure(api_key=api_key)
    agent = {
        "api_key": api_key,
        "model": "gemini-1.5",
        "temperature": 0.7,
        "tools": tools_list,
    }

    return agent


def format_response(raw_response: str) -> str:
    """Convert JSON response into human-readable text."""
    if not raw_response:
        return raw_response
    
    # If it doesn't look like JSON, return as-is
    if not raw_response.startswith("{") and not raw_response.startswith("["):
        return raw_response
    
    try:
        data = json.loads(raw_response)
        
        # Handle single order
        if isinstance(data, dict) and "order_id" in data and "customer_name" in data:
            order_id = data.get("order_id", "Unknown")
            customer = data.get("customer_name", "Unknown")
            status = data.get("status", "Unknown").upper()
            amount = data.get("total_amount", 0)
            notes = data.get("notes", "")
            
            text = f"Order **{order_id}** for {customer} has a status of **{status}** with a total amount of **${amount:.2f}**."
            if notes:
                text += f" Notes: {notes}"
            return text
        
        # Handle list of orders
        if isinstance(data, list) and len(data) > 0:
            if "order_id" in data[0]:
                text = "Here are the orders:\n\n"
                for order in data:
                    order_id = order.get("order_id", "Unknown")
                    customer = order.get("customer_name", "Unknown")
                    status = order.get("status", "Unknown")
                    amount = order.get("total_amount", 0)
                    text += f"• **{order_id}** ({customer}): {status.upper()} - ${amount:.2f}\n"
                return text.strip()
        
        # Handle summary
        if isinstance(data, dict) and "total_orders" in data and "status_breakdown" in data:
            total = data.get("total_orders", 0)
            revenue = data.get("total_revenue", 0)
            breakdown = data.get("status_breakdown", {})
            
            text = f"You currently have **{total}** orders totaling **${revenue:.2f}** in revenue.\n\n"
            text += "Status breakdown:\n"
            for status, count in breakdown.items():
                text += f"• {status.capitalize()}: {count}\n"
            return text.strip()
        
        # Handle items
        if isinstance(data, dict) and "items" in data:
            order_id = data.get("order_id", "Unknown")
            items = data.get("items", [])
            total = data.get("total_amount", 0)
            
            text = f"Items in order **{order_id}** (Total: **${total:.2f}**):\n\n"
            for item in items:
                name = item.get("name", "Unknown")
                qty = item.get("quantity", 0)
                price = item.get("price", 0)
                text += f"• {name} (Qty: {qty}, Price: ${price:.2f})\n"
            return text.strip()
        
        # Fallback: return original JSON if we can't parse
        return raw_response
    except Exception:
        return raw_response


def run_order_agent(llm_with_tools, user_input: str) -> str:
    """Run the agent with user input and return the response."""
    try:
        # Tool mapping for direct execution
        # helper to call either the decorated tool or its underlying function
        def call_tool(t, *args, **kwargs):
            if hasattr(t, "func"):
                return t.func(*args, **kwargs)
            return t(*args, **kwargs)

        tool_map = {
            "get_order_status": get_order_status,
            "get_customer_orders": get_customer_orders,
            "get_orders_by_status_filter": get_orders_by_status_filter,
            "update_order_status_tool": update_order_status_tool,
            "get_all_orders_summary": get_all_orders_summary,
            "get_order_items": get_order_items
        }
        
        # Route based on user input keywords (stricter matching)
        user_lower = user_input.lower()
        result = None

        # Only trigger routing when the user explicitly mentions orders or status
        if any(word in user_lower for word in ["order", "status", "find", "get", "show"]):
            import re
            # 1) If an order ID is present, return that order immediately
            order_match = re.search(r'ORD-\d+', user_input, re.IGNORECASE)
            if order_match:
                order_id = order_match.group(0)
                result = call_tool(get_order_status, order_id)
            else:
                # 2) If an email is present, return orders for that customer
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_input)
                if email_match:
                    email = email_match.group(0)
                    result = call_tool(get_customer_orders, email)
                else:
                    # 3) If a concrete status word is present, filter by that status
                    for status in ["pending", "processing", "shipped", "delivered"]:
                        if re.search(rf'\b{status}\b', user_lower):
                            result = call_tool(get_orders_by_status_filter, status)
                            break
                    # 4) If the user explicitly asked for a summary, return it
                    if result is None and any(word in user_lower for word in ["summary", "all orders", "total", "count", "how many"]):
                        result = call_tool(get_all_orders_summary)
        
        if any(word in user_lower for word in ["update", "change", "mark", "set"]):
            import re
            order_match = re.search(r'ORD-\d+', user_input, re.IGNORECASE)
            if order_match:
                order_id = order_match.group(0)
                for status in ["pending", "processing", "shipped", "delivered"]:
                    if status in user_lower:
                        result = call_tool(update_order_status_tool, order_id, status, user_input)
                        break
        
        if result:
            return format_response(result)
        
        # If no routing matched, use Gemini (google.generativeai) to interpret, if configured
        try:
            if llm_with_tools and genai is not None:
                # 1. Get the model name and ensure it's a valid Gemini 1.5 model string
                model_name = llm_with_tools.get("model", "gemini-1.5-flash")
                if model_name == "gemini-1.5":
                    model_name = "gemini-1.5-flash"  # Fallback to flash if incomplete
                
                # 2. Instantiate the modern GenerativeModel
                model = genai.GenerativeModel(model_name)
                
                # 3. Generate the response
                response = model.generate_content(
                    user_input,
                    generation_config=genai.types.GenerationConfig(
                        temperature=llm_with_tools.get("temperature", 0.7)
                    )
                )
                
                # 4. Return the text directly
                if response.text:
                    return response.text
                return "No text response generated."
                
        except Exception as e:
            return f"Error calling Gemini API: {e}"

        #         # Extract text from response (handle multiple response shapes)
        #         try:
        #             if hasattr(resp, "candidates") and resp.candidates:
        #                 return resp.candidates[0].content
        #             if isinstance(resp, dict) and "candidates" in resp and resp["candidates"]:
        #                 first = resp["candidates"][0]
        #                 if isinstance(first, dict) and "content" in first:
        #                     return first["content"]
        #             if hasattr(resp, "output"):
        #                 return str(resp.output)
        #             if hasattr(resp, "content"):
        #                 return str(resp.content)
        #             return str(resp)
        #         except Exception as e:
        #             return f"Error parsing Gemini response: {e}"
        # except Exception as e:
        #     return f"Error calling Gemini API: {e}"

        return "I couldn't determine an action for that request. Try specifying an order ID (e.g., ORD-001) or a customer email."
        
    except Exception as e:
        return f"Error: {str(e)}"
