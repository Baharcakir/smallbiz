"""
Koop-AI — FastAPI Ana Uygulama
Tüm agent route'larını birleştirir.
Çalıştır: uvicorn main:app --reload --port 8000
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from database.db import get_db, init_db
from agents.customer_support import agent as support_agent
from agents.order_inventory import agent as order_agent
from agents.analytics import agent as analytics_agent
from agents.cargo import agent as cargo_agent
from agents.workflow import agent as workflow_agent

# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Koop-AI API",
    description="Hatay Kadınlar Kooperatifi — Çok Ajanlı Yönetim Sistemi",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Şemaları ─────────────────────────────────────────────────────────
class SupportQuery(BaseModel):
    question: str

class CreateOrderRequest(BaseModel):
    customer_name: str
    customer_email: str = ""
    customer_phone: str = ""
    product_id: int
    quantity: int
    notes: str = ""

class UpdateOrderStatusRequest(BaseModel):
    status: str

class AssignTaskRequest(BaseModel):
    employee_id: int
    title: str
    description: str = ""
    due_date: str  # YYYY-MM-DD

class UpdateTaskStatusRequest(BaseModel):
    status: str

class AddEmployeeRequest(BaseModel):
    name: str
    role: str
    department: str


# ── Sağlık Kontrolü ───────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def root():
    return {
        "status": "ok",
        "app": "Koop-AI",
        "version": "1.0.0",
        "docs": "/docs",
    }

@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — MÜŞTERİ DESTEK
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/support/query", tags=["Müşteri Destek"])
def customer_support_query(payload: SupportQuery):
    """Müşteri sorusunu RAG ile yanıtla (Gemini + ChromaDB)."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")
    try:
        result = support_agent.answer_customer_query(payload.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG hatası: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — SİPARİŞ & STOK
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/orders/create", tags=["Siparişler"])
def create_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
    """Yeni sipariş oluştur."""
    result = order_agent.create_order(
        db=db,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        customer_phone=req.customer_phone,
        product_id=req.product_id,
        quantity=req.quantity,
        notes=req.notes,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/orders/list", tags=["Siparişler"])
def list_orders(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Siparişleri listele."""
    return {"orders": order_agent.get_orders(db, status)}


@app.patch("/api/orders/{order_id}/status", tags=["Siparişler"])
def update_order_status(
    order_id: int,
    req: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
):
    """Sipariş durumunu güncelle."""
    result = order_agent.update_order_status(db, order_id, req.status)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/inventory/stock", tags=["Stok"])
def get_stock(db: Session = Depends(get_db)):
    """Tüm ürün stoklarını getir."""
    return {"inventory": order_agent.get_all_stock(db)}


@app.get("/api/inventory/stock/{product_id}", tags=["Stok"])
def get_product_stock(product_id: int, db: Session = Depends(get_db)):
    """Belirli ürünün stok durumunu getir."""
    result = order_agent.check_stock(db, product_id)
    if not result.get("success", True) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — ANALİTİK
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/analytics/upload", tags=["Analitik"])
async def upload_sales_csv(file: UploadFile = File(...)):
    """CSV satış verisi yükle ve analiz et (Gemini özeti dahil)."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Yalnızca CSV dosyası kabul edilir.")
    try:
        content = (await file.read()).decode("utf-8")
        result = analytics_agent.get_full_analysis(csv_content=content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analiz hatası: {str(e)}")


@app.get("/api/analytics/summary", tags=["Analitik"])
def get_analytics_summary():
    """Örnek satış verisi üzerinden analiz + Gemini özeti döndür."""
    try:
        return analytics_agent.get_full_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/charts", tags=["Analitik"])
def get_chart_data():
    """Grafik için hazır JSON verisi."""
    try:
        result = analytics_agent.get_full_analysis()
        return {"charts": result["charts"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — KARGO TAKİP
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/cargo/{tracking_no}", tags=["Kargo"])
def get_cargo(tracking_no: str, db: Session = Depends(get_db)):
    """Kargo takip durumunu sorgula."""
    result = cargo_agent.get_cargo_status(db, tracking_no)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/cargo/assign", tags=["Kargo"])
def assign_cargo(order_id: int, db: Session = Depends(get_db)):
    """Siparişe kargo ata."""
    result = cargo_agent.assign_cargo(db, order_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/cargo", tags=["Kargo"])
def list_shipments(db: Session = Depends(get_db)):
    """Tüm kargo kayıtlarını getir."""
    return {"shipments": cargo_agent.get_all_shipments(db)}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 5 — İŞ AKIŞI & ÇALIŞANLAR
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/workflow/employees", tags=["Çalışanlar"])
def list_employees(db: Session = Depends(get_db)):
    """Tüm çalışanları getir."""
    return {"employees": workflow_agent.get_employees(db)}


@app.post("/api/workflow/employees", tags=["Çalışanlar"])
def add_employee(req: AddEmployeeRequest, db: Session = Depends(get_db)):
    """Yeni çalışan ekle."""
    return workflow_agent.add_employee(db, req.name, req.role, req.department)


@app.get("/api/workflow/tasks", tags=["Görevler"])
def list_tasks(
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Görevleri filtreli listele."""
    return {"tasks": workflow_agent.get_tasks(db, employee_id, status)}


@app.post("/api/workflow/tasks", tags=["Görevler"])
def assign_task(req: AssignTaskRequest, db: Session = Depends(get_db)):
    """Çalışana görev ata."""
    from datetime import date as date_cls
    try:
        due = date_cls.fromisoformat(req.due_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Tarih formatı: YYYY-MM-DD")
    result = workflow_agent.assign_task(db, req.employee_id, req.title, req.description, due)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.patch("/api/workflow/tasks/{task_id}", tags=["Görevler"])
def update_task(
    task_id: int,
    req: UpdateTaskStatusRequest,
    db: Session = Depends(get_db),
):
    """Görev durumunu güncelle."""
    result = workflow_agent.update_task_status(db, task_id, req.status)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/workflow/overdue", tags=["Görevler"])
def get_overdue(db: Session = Depends(get_db)):
    """Gecikmiş görevleri getir."""
    return {"overdue_tasks": workflow_agent.get_overdue_tasks(db)}


@app.get("/api/workflow/workload", tags=["Görevler"])
def get_workload(db: Session = Depends(get_db)):
    """Çalışan görev yükü dağılımı."""
    return {"workload": workflow_agent.get_employee_workload(db)}
