"""
Koop-AI — Agent Testleri
Çalıştır: pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.db import Base
from database.models import Product, Order, Employee, Task, Shipment


# ── Test Veritabanı ───────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Test ürünleri ekle
    p1 = Product(name="Test Salça", price=85.0, stock_quantity=50, unit="adet", category="Salça")
    p2 = Product(name="Az Stoklu Ürün", price=100.0, stock_quantity=5, unit="adet", category="Test")
    db.add_all([p1, p2])

    # Test çalışanı ekle
    emp = Employee(name="Test Kişi", role="Test Uzmanı", department="Test")
    db.add(emp)
    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)


# ── Order Agent Testleri ──────────────────────────────────────────────────────
class TestOrderAgent:
    def test_create_order_success(self, test_db):
        from agents.order_inventory.agent import create_order
        result = create_order(
            db=test_db,
            customer_name="Ali Veli",
            customer_email="ali@test.com",
            customer_phone="",
            product_id=1,
            quantity=3,
        )
        assert result["success"] is True
        assert "order_id" in result
        assert "tracking_no" in result
        assert result["tracking_no"].startswith("KOOP")
        assert result["total_price"] == 85.0 * 3

    def test_create_order_insufficient_stock(self, test_db):
        from agents.order_inventory.agent import create_order
        result = create_order(
            db=test_db,
            customer_name="Ali Veli",
            customer_email="",
            customer_phone="",
            product_id=1,
            quantity=9999,
        )
        assert result["success"] is False
        assert "Yetersiz stok" in result["error"]

    def test_create_order_product_not_found(self, test_db):
        from agents.order_inventory.agent import create_order
        result = create_order(
            db=test_db,
            customer_name="Ali Veli",
            customer_email="",
            customer_phone="",
            product_id=9999,
            quantity=1,
        )
        assert result["success"] is False

    def test_stock_decrements_after_order(self, test_db):
        from agents.order_inventory.agent import create_order, check_stock
        initial = check_stock(test_db, 1)
        initial_qty = initial["stock_quantity"]

        create_order(
            db=test_db,
            customer_name="Test Müşteri",
            customer_email="",
            customer_phone="",
            product_id=1,
            quantity=5,
        )

        after = check_stock(test_db, 1)
        assert after["stock_quantity"] == initial_qty - 5

    def test_low_stock_warning(self, test_db):
        from agents.order_inventory.agent import check_stock
        result = check_stock(test_db, 2)
        assert result["low_stock_warning"] is True

    def test_update_order_status(self, test_db):
        from agents.order_inventory.agent import create_order, update_order_status
        order = create_order(
            db=test_db,
            customer_name="Test",
            customer_email="",
            customer_phone="",
            product_id=1,
            quantity=1,
        )
        result = update_order_status(test_db, order["order_id"], "shipped")
        assert result["success"] is True
        assert result["new_status"] == "shipped"

    def test_get_orders(self, test_db):
        from agents.order_inventory.agent import create_order, get_orders
        create_order(test_db, "Müşteri A", "", "", 1, 1)
        create_order(test_db, "Müşteri B", "", "", 1, 2)
        orders = get_orders(test_db)
        assert len(orders) >= 2

    def test_get_all_stock(self, test_db):
        from agents.order_inventory.agent import get_all_stock
        stock = get_all_stock(test_db)
        assert len(stock) == 2
        assert all("low_stock_warning" in p for p in stock)


# ── Cargo Agent Testleri ──────────────────────────────────────────────────────
class TestCargoAgent:
    def test_assign_cargo(self, test_db):
        from agents.order_inventory.agent import create_order
        from agents.cargo.agent import get_cargo_status

        order = create_order(test_db, "Kargo Test", "", "", 1, 1)
        tracking_no = order["tracking_no"]

        result = get_cargo_status(test_db, tracking_no)
        assert result["success"] is True
        assert result["tracking_no"] == tracking_no
        assert "timeline" in result
        assert len(result["timeline"]) == 5

    def test_cargo_not_found(self, test_db):
        from agents.cargo.agent import get_cargo_status
        result = get_cargo_status(test_db, "KOOP999999")
        assert result["success"] is False


# ── Workflow Agent Testleri ───────────────────────────────────────────────────
class TestWorkflowAgent:
    def test_add_employee(self, test_db):
        from agents.workflow.agent import add_employee, get_employees
        result = add_employee(test_db, "Yeni Kişi", "Uzman", "Satış")
        assert result["success"] is True
        employees = get_employees(test_db)
        names = [e["name"] for e in employees]
        assert "Yeni Kişi" in names

    def test_assign_task(self, test_db):
        from agents.workflow.agent import assign_task, get_tasks
        from datetime import date, timedelta
        result = assign_task(
            test_db,
            employee_id=1,
            title="Test Görevi",
            description="Test açıklaması",
            due_date=date.today() + timedelta(days=7),
        )
        assert result["success"] is True
        assert result["task"]["title"] == "Test Görevi"

    def test_update_task_status(self, test_db):
        from agents.workflow.agent import assign_task, update_task_status
        from datetime import date, timedelta
        task = assign_task(test_db, 1, "Durum Testi", "", date.today() + timedelta(days=1))
        task_id = task["task"]["id"]
        result = update_task_status(test_db, task_id, "in_progress")
        assert result["success"] is True
        assert result["task"]["status"] == "in_progress"

    def test_overdue_tasks(self, test_db):
        from agents.workflow.agent import assign_task, get_overdue_tasks
        from datetime import date, timedelta
        assign_task(test_db, 1, "Gecikmiş Görev", "", date.today() - timedelta(days=5))
        overdue = get_overdue_tasks(test_db)
        assert len(overdue) >= 1
        assert any(t["title"] == "Gecikmiş Görev" for t in overdue)

    def test_invalid_task_status(self, test_db):
        from agents.workflow.agent import assign_task, update_task_status
        from datetime import date, timedelta
        task = assign_task(test_db, 1, "Test", "", date.today() + timedelta(days=1))
        result = update_task_status(test_db, task["task"]["id"], "invalid_status")
        assert result["success"] is False

    def test_employee_workload(self, test_db):
        from agents.workflow.agent import get_employee_workload
        workload = get_employee_workload(test_db)
        assert isinstance(workload, list)


# ── Analytics Agent Testleri ──────────────────────────────────────────────────
class TestAnalyticsAgent:
    def test_load_sample_data(self):
        from agents.analytics.agent import load_dataframe
        df = load_dataframe()
        assert not df.empty
        assert "date" in df.columns
        assert "total" in df.columns

    def test_compute_metrics(self):
        from agents.analytics.agent import load_dataframe, compute_metrics
        df = load_dataframe()
        metrics = compute_metrics(df)
        assert metrics["total_revenue"] > 0
        assert metrics["total_orders"] > 0
        assert "top_products_by_quantity" in metrics
        assert "monthly_revenue" in metrics

    def test_full_analysis_structure(self):
        from agents.analytics.agent import get_full_analysis
        result = get_full_analysis()
        assert "metrics" in result
        assert "charts" in result
        assert "summary" in result
        # Summary API key olmasa bile string dönmeli
        assert isinstance(result["summary"], str)
