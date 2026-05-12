"""
SQLAlchemy ORM modelleri.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    unit = Column(String, default="adet")
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="product")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock_quantity": self.stock_quantity,
            "unit": self.unit,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    customer_phone = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, shipped, delivered
    cargo_tracking_no = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="orders")
    shipment = relationship("Shipment", back_populates="order", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "total_price": self.total_price,
            "status": self.status,
            "cargo_tracking_no": self.cargo_tracking_no,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    role = Column(String)
    department = Column(String)
    status = Column(String, default="active")  # active, on_leave, inactive
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="employee")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")  # pending, in_progress, done
    due_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    tracking_no = Column(String, unique=True, nullable=False)
    carrier = Column(String, default="Yurtiçi Kargo")
    status = Column(String, default="preparing")
    # preparing, picked_up, in_transit, out_for_delivery, delivered
    last_location = Column(String)
    estimated_delivery = Column(Date)
    updated_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="shipment")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "tracking_no": self.tracking_no,
            "carrier": self.carrier,
            "status": self.status,
            "last_location": self.last_location,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
