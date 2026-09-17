"""SQLite helpers for Spendly: connection factory, schema creation, and demo seed data."""

import os
import sqlite3
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "expense_tracker.db")


def get_db():
    """Open a new SQLite connection with row access by column name and FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_by_email(email):
    """Return the user row matching email, or None if no such user exists."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    """Hash password and insert a new user. Returns the new id, or None on a duplicate email."""
    password_hash = generate_password_hash(password)
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def verify_user(email, password):
    """Return the user row if email and password match, or None if the email is unknown
    or the password is wrong (both cases collapse to None on purpose)."""
    user = get_user_by_email(email)
    if user is None:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def init_db():
    """Create the users and expenses tables if they don't already exist."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user and 8 sample expenses, but only if the users table is empty."""
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if row["count"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        today = date.today()

        def on_day(day):
            return date(today.year, today.month, day).isoformat()

        sample_expenses = [
            (user_id, 45.50, "Food", on_day(2), "Grocery shopping"),
            (user_id, 18.00, "Transport", on_day(4), "Bus pass top-up"),
            (user_id, 120.00, "Bills", on_day(5), "Electricity bill"),
            (user_id, 35.75, "Health", on_day(9), "Pharmacy"),
            (user_id, 60.00, "Entertainment", on_day(12), "Movie night"),
            (user_id, 89.99, "Shopping", on_day(16), "New shoes"),
            (user_id, 25.00, "Other", on_day(20), "Miscellaneous"),
            (user_id, 32.40, "Food", on_day(24), "Restaurant dinner"),
        ]

        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            sample_expenses,
        )
        conn.commit()
    finally:
        conn.close()
