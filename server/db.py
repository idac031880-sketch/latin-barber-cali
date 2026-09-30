"""Conexión y esquema de la base de datos. Un solo archivo SQLite,
server/data.db, con una tabla por recurso de la intranet."""
from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import auth

DB_PATH = Path(__file__).resolve().parent / "data.db"


@contextmanager
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _add_column_if_missing(conn, table, column, decl):
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    except sqlite3.OperationalError:
        pass  # ya existe


def init_db():
    with db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin'
            )
        """)
        _add_column_if_missing(conn, "admins", "role", "TEXT NOT NULL DEFAULT 'admin'")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL DEFAULT 0,
                duration_minutes INTEGER NOT NULL DEFAULT 45,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                role_title TEXT,
                color TEXT NOT NULL DEFAULT '#101012',
                calendar_id TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                notes TEXT,
                barber TEXT,
                staff_id INTEGER REFERENCES staff(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'pendiente',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        _add_column_if_missing(conn, "appointments", "barber", "TEXT")
        _add_column_if_missing(conn, "appointments", "staff_id", "INTEGER REFERENCES staff(id)")
        _add_column_if_missing(conn, "appointments", "status", "TEXT NOT NULL DEFAULT 'pendiente'")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'unidad',
                min_stock REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount INTEGER NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                expense_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                status TEXT NOT NULL DEFAULT 'borrador',
                starts_at TEXT,
                ends_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                percent_off INTEGER,
                amount_off INTEGER,
                expires_at TEXT,
                max_uses INTEGER,
                used_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        row = conn.execute("SELECT COUNT(*) AS n FROM admins").fetchone()
        if row["n"] == 0:
            username = os.environ.get("ADMIN_USER", "admin")
            password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(9)
            salt, pw_hash = auth.hash_password(password)
            conn.execute(
                "INSERT INTO admins (username, salt, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (username, salt, pw_hash),
            )
            print("=" * 58)
            print(" Cuenta de la intranet creada")
            print(f"   Usuario:    {username}")
            print(f"   Contraseña: {password}")
            print(" Guárdala ahora — no se vuelve a mostrar.")
            print(" (Para elegirla tú, define ADMIN_USER y ADMIN_PASSWORD")
            print("  antes de la primera ejecución.)")
            print("=" * 58)

        row = conn.execute("SELECT COUNT(*) AS n FROM services").fetchone()
        if row["n"] == 0:
            conn.executemany(
                "INSERT INTO services (name, description, price, duration_minutes) VALUES (?, ?, ?, ?)",
                [
                    ("Barbería", "Cortes con navaja, diseño de barba y afeitado tradicional.", 35000, 45),
                    ("Peluquería", "Color, alisados y peinados.", 60000, 60),
                    ("Uñas", "Manicure, pedicure y nail art.", 40000, 45),
                ],
            )
