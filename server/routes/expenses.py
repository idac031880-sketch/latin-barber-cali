"""Gastos y reportes simples."""
import re

from db import db_conn

ROUTES = []
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


@register("GET", r"^/api/expenses$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC").fetchall()
    h.send_json(200, {"expenses": [dict(r) for r in rows]})


@register("POST", r"^/api/expenses$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    description = str(body.get("description", "")).strip()[:200]
    expense_date = str(body.get("expense_date", "")).strip()
    if not description:
        return h.send_json(400, {"error": "La descripción es obligatoria"})
    if not DATE_RE.match(expense_date):
        return h.send_json(400, {"error": "La fecha no es válida"})
    try:
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError):
        return h.send_json(400, {"error": "Monto inválido"})

    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (description, amount, category, expense_date) VALUES (?, ?, ?, ?)",
            (description, amount, str(body.get("category", "general")).strip()[:40] or "general", expense_date),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("DELETE", r"^/api/expenses/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})
