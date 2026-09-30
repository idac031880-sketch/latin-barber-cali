"""Resumen numérico para la pantalla principal de la intranet."""
from datetime import date, timedelta

from db import db_conn

ROUTES = []


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


@register("GET", r"^/api/dashboard$")
def summary(h, **kwargs):
    if not h.require_auth():
        return
    today_date = date.today()
    today = today_date.isoformat()
    week_end = (today_date + timedelta(days=7)).isoformat()
    month_start = today_date.replace(day=1).isoformat()
    next_month_start = (
        today_date.replace(year=today_date.year + 1, month=1, day=1)
        if today_date.month == 12
        else today_date.replace(month=today_date.month + 1, day=1)
    ).isoformat()

    with db_conn() as conn:
        today_count = conn.execute(
            "SELECT COUNT(*) AS n FROM appointments WHERE date = ? AND status != 'cancelada'", (today,)
        ).fetchone()["n"]
        week_count = conn.execute(
            "SELECT COUNT(*) AS n FROM appointments WHERE date BETWEEN ? AND ? AND status != 'cancelada'",
            (today, week_end),
        ).fetchone()["n"]
        clients_count = conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]

        month_revenue = conn.execute("""
            SELECT COALESCE(SUM(s.price), 0) AS total
            FROM appointments a
            JOIN services s ON s.name = a.service
            WHERE a.date >= ? AND a.date < ? AND a.status != 'cancelada'
        """, (month_start, next_month_start)).fetchone()["total"]

        month_expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE expense_date >= ? AND expense_date < ?",
            (month_start, next_month_start),
        ).fetchone()["total"]

        low_stock = conn.execute(
            "SELECT COUNT(*) AS n FROM inventory WHERE quantity <= min_stock"
        ).fetchone()["n"]

        active_codes = conn.execute(
            "SELECT COUNT(*) AS n FROM discount_codes WHERE active = 1"
        ).fetchone()["n"]

        next_appointments = conn.execute(
            "SELECT id, name, service, date, time FROM appointments "
            "WHERE date >= ? AND status != 'cancelada' ORDER BY date ASC, time ASC LIMIT 5",
            (today,),
        ).fetchall()

    h.send_json(200, {
        "today_count": today_count,
        "week_count": week_count,
        "clients_count": clients_count,
        "month_revenue": month_revenue,
        "month_expenses": month_expenses,
        "low_stock": low_stock,
        "active_codes": active_codes,
        "next_appointments": [dict(r) for r in next_appointments],
    })
