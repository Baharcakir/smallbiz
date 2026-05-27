import sqlite3
import os
import hashlib
import binascii
import time
from typing import Optional, Dict
import streamlit as st

DATABASE_PATH = "orders.db"

# Users table creation (id, email unique, password_hash, company_name, created_at)
CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    company_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _get_conn():
    return sqlite3.connect(DATABASE_PATH)


def init_auth():
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.executescript(CREATE_USERS_SQL)
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    # PBKDF2-HMAC-SHA256
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split('$')
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(hash_hex)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
        return hmac_compare(dk, expected)
    except Exception:
        return False


def hmac_compare(a: bytes, b: bytes) -> bool:
    # constant-time comparison
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def create_user(email: str, password: str, company_name: str) -> Optional[Dict]:
    init_auth()
    conn = _get_conn()
    cursor = conn.cursor()
    password_hash = _hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, company_name) VALUES (?, ?, ?)",
            (email, password_hash, company_name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT id, email, company_name, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "email": row[1], "company_name": row[2], "created_at": row[3]}
    except sqlite3.IntegrityError:
        conn.close()
        return None
    return None


def get_user_by_email(email: str) -> Optional[Dict]:
    init_auth()
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, company_name, created_at FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def verify_user(email: str, password: str) -> Optional[Dict]:
    user = get_user_by_email(email)
    if not user:
        return None
    if _verify_password(password, user["password_hash"]):
        return {"id": user["id"], "email": user["email"], "company_name": user["company_name"], "created_at": user["created_at"]}
    return None


def require_login():
    # Call at top of pages that require authentication
    # Directly redirect to login page if not authenticated
    if not st.session_state.get("user_authenticated"):
        st.switch_page("pages/login_register.py")


def logout():
    keys = [k for k in list(st.session_state.keys()) if k.startswith("user_") or k == "user_authenticated"]
    for k in keys:
        del st.session_state[k]
    st.experimental_rerun()
