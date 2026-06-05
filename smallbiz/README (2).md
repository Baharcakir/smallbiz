# Koop-AI — Multi-Agent System for Cooperative Management

> Google Hackathon Project · Python · FastAPI · LangChain · ChromaDB · Gemini · Streamlit

---

## Project Overview

Koop-AI is a multi-agent AI system designed for small cooperatives (specifically disaster-region women's cooperatives in Hatay, Turkey). It eliminates manual workload from order management, customer support, analytics, cargo tracking, and workforce coordination — all accessible through a single Streamlit dashboard.

**Core Problem:** Cooperative members spend most of their time manually answering WhatsApp messages, tracking orders in notebooks, and generating no insights from their sales data.

**Solution:** Six specialized AI agents, each owning a domain, communicating through a shared SQLite database and FastAPI backend.

---

## Repository Structure

```
koop-ai/
├── README.md                  ← this file
├── requirements.txt
├── .env.example
├── main.py                    ← FastAPI app entry point
├── database/
│   ├── db.py                  ← SQLite connection & session
│   ├── models.py              ← SQLAlchemy models
│   └── seed.py                ← Hatay cooperative demo data
├── agents/
│   ├── customer_support/
│   │   ├── agent.py           ← RAG chain (LangChain + ChromaDB)
│   │   ├── ingest.py          ← Document ingestion to vector store
│   │   └── docs/              ← FAQ.txt, product_info.txt, policies.txt
│   ├── order_inventory/
│   │   ├── agent.py           ← Order CRUD, stock check, mail trigger
│   │   └── mailer.py          ← smtplib email sender
│   ├── analytics/
│   │   ├── agent.py           ← pandas parser + Gemini summarizer
│   │   └── sample_sales.csv   ← Demo sales data
│   ├── cargo/
│   │   └── agent.py           ← Cargo status mock API
│   └── workflow/
│       └── agent.py           ← Employee task tracker
├── dashboard/
│   └── app.py                 ← Streamlit multi-tab dashboard
└── tests/
    └── test_agents.py
```

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| LLM | Gemini 1.5 Flash | Free tier, generous quota for students |
| RAG Framework | LangChain | Chain orchestration |
| Vector Database | ChromaDB | Local persistent store |
| Backend | FastAPI + Python 3.11 | REST API for all agents |
| Database | SQLite + SQLAlchemy | Single file, no server needed |
| Frontend | Streamlit | Multi-tab dashboard |
| Email | smtplib (stdlib) | No external dependency |
| Data Processing | pandas | Sales CSV parsing |

---

## Database Schema

### `products`
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- e.g. "Hatay Biber Salçası"
    description TEXT,
    price REAL NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    unit TEXT DEFAULT 'adet',     -- adet, kg, litre
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `orders`
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    customer_email TEXT,
    customer_phone TEXT,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, confirmed, shipped, delivered
    cargo_tracking_no TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `employees`
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT,
    department TEXT,
    status TEXT DEFAULT 'active',  -- active, on_leave, inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `tasks`
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER REFERENCES employees(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending', -- pending, in_progress, done
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `shipments`
```sql
CREATE TABLE shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    tracking_no TEXT UNIQUE NOT NULL,
    carrier TEXT DEFAULT 'Yurtiçi Kargo',
    status TEXT DEFAULT 'preparing', -- preparing, in_transit, delivered, failed
    last_location TEXT,
    estimated_delivery DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Agent Specifications

---

### Agent 1 — Customer Support (RAG)

**File:** `agents/customer_support/agent.py`

**Purpose:** Answer customer questions about products, prices, ingredients, policies using RAG over uploaded cooperative documents.

**How it works:**
1. On startup, `ingest.py` reads all `.txt` and `.pdf` files from `agents/customer_support/docs/`
2. Splits them into chunks (chunk_size=500, overlap=50)
3. Embeds with `GoogleGenerativeAIEmbeddings` and stores in ChromaDB
4. On query, retrieves top-3 relevant chunks and passes to Gemini Flash with a Turkish-language system prompt

**Implementation:**
```python
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter

def build_rag_chain():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
    return RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

def answer_customer_query(query: str) -> str:
    chain = build_rag_chain()
    return chain.invoke(query)["result"]
```

**Documents to create in `docs/`:**
- `faq.txt` — Sık sorulan sorular (kargo süresi, iade politikası, ödeme yöntemleri)
- `products.txt` — Ürün listesi, fiyatlar, içerikler, gramaj bilgileri
- `about.txt` — Kooperatif hakkında, üretim yöntemi, hikaye

**FastAPI endpoint:**
```
POST /api/support/query
Body: { "question": "Salçanızda koruyucu var mı?" }
Response: { "answer": "...", "sources": [...] }
```

---

### Agent 2 — Order & Inventory

**File:** `agents/order_inventory/agent.py`

**Purpose:** Create orders, check stock availability, update inventory, send confirmation emails.

**Key functions:**

```python
def create_order(customer_name, customer_email, product_id, quantity) -> dict:
    # 1. Check stock: SELECT stock_quantity FROM products WHERE id = product_id
    # 2. If stock >= quantity: create order record, decrement stock
    # 3. Generate cargo tracking number
    # 4. Send confirmation email via mailer.py
    # 5. Return order summary

def get_orders(status=None) -> list:
    # Return all orders, optionally filtered by status

def update_order_status(order_id, new_status) -> dict:
    # Update status, trigger email if shipped

def check_stock(product_id) -> dict:
    # Return current stock level + low stock warning if < 10
```

**Stock alert logic:** If `stock_quantity < 10` after an order, automatically log a warning. Display this warning prominently on the Dashboard.

**Email template (mailer.py):**
```
Konu: Siparişiniz Alındı — Koop-AI
İçerik:
  Sayın {customer_name},
  {product_name} x{quantity} siparişiniz alındı.
  Kargo takip no: {tracking_no}
  Tahmini teslimat: 2-3 iş günü
```

**FastAPI endpoints:**
```
POST   /api/orders/create
GET    /api/orders/list?status=pending
PATCH  /api/orders/{order_id}/status
GET    /api/inventory/stock
```

---

### Agent 3 — Analytics & Insights

**File:** `agents/analytics/agent.py`

**Purpose:** Parse sales CSV/Excel data with pandas, compute key metrics, and generate a Turkish-language business summary using Gemini Flash.

**Input:** CSV file with columns: `date, product_name, quantity, unit_price, total, customer_region`

**Metrics to compute:**
```python
import pandas as pd

def compute_metrics(df: pd.DataFrame) -> dict:
    return {
        "total_revenue": df["total"].sum(),
        "total_orders": len(df),
        "top_products": df.groupby("product_name")["quantity"].sum().nlargest(3).to_dict(),
        "weekly_revenue": df.resample("W", on="date")["total"].sum().to_dict(),
        "avg_order_value": df["total"].mean(),
        "best_week": df.resample("W", on="date")["total"].sum().idxmax(),
    }
```

**Gemini summary prompt:**
```python
SUMMARY_PROMPT = """
Sen bir kooperatif danışmanısın. Aşağıdaki satış metriklerini analiz et ve
kooperatif sahibinin anlayabileceği sade Türkçe ile 4-5 madde halinde özetle.
Önemli trendleri, uyarıları ve önerileri belirt.

Metrikler:
{metrics_json}

Çıktı formatı:
✅ [pozitif trend]
⚠️ [dikkat edilmesi gereken nokta]
💡 [öneri]
"""
```

**FastAPI endpoints:**
```
POST /api/analytics/upload     ← CSV upload
GET  /api/analytics/summary    ← Returns metrics + Gemini text summary
GET  /api/analytics/charts     ← Returns chart-ready JSON data
```

---

### Agent 4 — Dashboard (Streamlit)

**File:** `dashboard/app.py`

**Purpose:** Single-page Streamlit app with 5 tabs, each connected to an agent's FastAPI endpoint.

**Tab structure:**
```python
import streamlit as st
import requests

st.set_page_config(page_title="Koop-AI Dashboard", layout="wide")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Siparişler",
    "📊 Satış Analizi",
    "💬 Müşteri Destek",
    "👥 Çalışanlar",
    "🚚 Kargo"
])
```

**Tab 1 — Orders:** Table of recent orders, status badges, stock warning alerts  
**Tab 2 — Analytics:** Bar chart (weekly revenue), pie chart (product breakdown), Gemini summary text in large font  
**Tab 3 — Support:** Chat interface — user types question, calls `/api/support/query`, shows answer  
**Tab 4 — Employees:** Employee list, task statuses, workload overview  
**Tab 5 — Cargo:** Tracking number search, shipment status timeline  

**Key rule:** Dashboard only displays data. It does NOT contain business logic — all logic lives in the FastAPI agents.

---

### Agent 5 — Cargo Tracking

**File:** `agents/cargo/agent.py`

**Purpose:** Assign tracking numbers to orders, simulate cargo status updates, return status on query.

**Status flow:**
```
preparing → picked_up → in_transit → out_for_delivery → delivered
```

**Implementation approach (mock):**
```python
import random
from datetime import datetime, timedelta

CARGO_STATUSES = ["preparing", "picked_up", "in_transit", "out_for_delivery", "delivered"]

def get_cargo_status(tracking_no: str) -> dict:
    # In production: call real carrier API (Yurtiçi, Aras, PTT)
    # For demo: deterministic mock based on order age
    shipment = db.query(Shipment).filter_by(tracking_no=tracking_no).first()
    return {
        "tracking_no": tracking_no,
        "status": shipment.status,
        "last_location": shipment.last_location,
        "estimated_delivery": shipment.estimated_delivery,
        "carrier": shipment.carrier
    }

def generate_tracking_no() -> str:
    return f"KOOP{random.randint(100000, 999999)}"
```

**FastAPI endpoints:**
```
GET  /api/cargo/{tracking_no}
POST /api/cargo/assign          ← Called by Order Agent after order creation
```

---

### Agent 6 — Workflow Tracker

**File:** `agents/workflow/agent.py`

**Purpose:** Load employee list, assign tasks, track task statuses, surface overdue items.

**Key functions:**
```python
def add_employee(name, role, department) -> dict
def assign_task(employee_id, title, description, due_date) -> dict
def update_task_status(task_id, new_status) -> dict
def get_overdue_tasks() -> list   # due_date < today AND status != 'done'
def get_employee_workload() -> dict  # task counts per employee
```

**FastAPI endpoints:**
```
GET    /api/workflow/employees
POST   /api/workflow/employees
GET    /api/workflow/tasks?employee_id=&status=
POST   /api/workflow/tasks
PATCH  /api/workflow/tasks/{task_id}
GET    /api/workflow/overdue
```

---

## Demo Data (Seed)

`database/seed.py` must populate realistic Hatay cooperative data:

**Products:**
- Hatay Biber Salçası (450g) — 85 TL — stock: 120
- Hatay İsot Biberi (250g) — 65 TL — stock: 80
- Sızma Zeytinyağı (500ml) — 220 TL — stock: 45
- Antep Fıstıklı Sucuk (300g) — 150 TL — stock: 30 ← intentionally low stock for demo
- Doğal Defne Sabunu (100g) — 45 TL — stock: 200

**Sample orders:** 10-15 orders in various statuses (pending, shipped, delivered)

**Employees:** 5 employees with names, roles (Üretim, Paketleme, Muhasebe, Satış)

**Tasks:** Mix of pending, in_progress, done — include 2 overdue tasks for demo impact

---

## Demo Flow Script (5-minute presentation)

**Scene 1 — Customer Support (90 sec)**
> Go to Tab 3 (Destek). Type: *"Biber salçanızda koruyucu madde var mı, fiyatı ne kadar?"*
> Agent answers from FAQ + product docs. Show source document highlighted.

**Scene 2 — Order Creation (60 sec)**
> Call `POST /api/orders/create` via dashboard form or Streamlit sidebar.
> Show: stock decrements, confirmation email sent, tracking number generated.
> Note: Antep fıstıklı sucuk triggers low-stock warning.

**Scene 3 — Cargo Tracking (30 sec)**
> Go to Tab 5. Enter tracking number from Scene 2.
> Show status timeline: preparing → in_transit → out_for_delivery

**Scene 4 — Analytics (90 sec)**
> Go to Tab 2. Show weekly revenue bar chart.
> Show Gemini-generated Turkish summary with ✅⚠️💡 bullets.
> Point out: "Bu özeti üretmek 2 saniye sürdü."

**Scene 5 — Workflow (30 sec)**
> Go to Tab 4. Show overdue tasks highlighted in red.
> Show employee workload — who has the most tasks.

---

## Environment Variables

Create `.env` file (never commit to git):
```
GOOGLE_API_KEY=your_gemini_api_key_here
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
DATABASE_URL=sqlite:///./koop_ai.db
CHROMA_PERSIST_DIR=./chroma_db
```

---

## Installation & Run

```bash
# Clone and install
git clone https://github.com/your-team/koop-ai
cd koop-ai
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# → Edit .env with your Gemini API key

# Seed database
python database/seed.py

# Ingest documents into ChromaDB
python agents/customer_support/ingest.py

# Start FastAPI backend (port 8000)
uvicorn main:app --reload

# Start Streamlit dashboard (new terminal, port 8501)
streamlit run dashboard/app.py
```

---

## Requirements

```
fastapi
uvicorn
sqlalchemy
langchain
langchain-google-genai
langchain-community
chromadb
google-generativeai
pandas
streamlit
python-dotenv
requests
openpyxl
```

---

## Agent Communication Map

```
Streamlit Dashboard
       │
       ▼
   FastAPI (main.py)
   /api/support/*  ──► Customer Support Agent ──► ChromaDB
   /api/orders/*   ──► Order Agent ──────────────► SQLite + mailer
   /api/analytics/* ─► Analytics Agent ──────────► pandas + Gemini
   /api/cargo/*    ──► Cargo Agent ─────────────► SQLite
   /api/workflow/* ──► Workflow Agent ──────────► SQLite
```

All agents share the same SQLite database. No agent calls another agent directly — all cross-agent data flows through the database.

---

## Evaluation Criteria Notes (Hackathon)

- **Technical depth:** Multi-agent architecture + RAG + NLP all demonstrated
- **Real problem:** Directly addresses manual workload in disaster-region cooperatives
- **Working demo:** End-to-end flow runnable in under 5 minutes
- **Code quality:** Each agent is isolated, testable, and independently runnable
- **Impact:** Every feature shown maps to a real pain point (WhatsApp overload, paper notebooks, no insights)

---

*Built for Google Hackathon · Koop-AI Team*
