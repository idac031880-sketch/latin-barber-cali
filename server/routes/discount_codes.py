"""Códigos de descuento."""
from db import db_conn

ROUTES = []


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


@register("GET", r"^/api/discount-codes$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM discount_codes ORDER BY created_at DESC").fetchall()
    h.send_json(200, {"discount_codes": [dict(r) for r in rows]})


@register("POST", r"^/api/discount-codes$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    code = str(body.get("code", "")).strip().upper()[:30]
    if not code:
        return h.send_json(400, {"error": "El código es obligatorio"})
    percent_off = body.get("percent_off")
    amount_off = body.get("amount_off")
    try:
        percent_off = int(percent_off) if percent_off not in (None, "") else None
        amount_off = int(amount_off) if amount_off not in (None, "") else None
        max_uses = int(body["max_uses"]) if body.get("max_uses") not in (None, "") else None
    except (TypeError, ValueError):
        return h.send_json(400, {"error": "Valores numéricos inválidos"})
    if percent_off is None and amount_off is None:
        return h.send_json(400, {"error": "Define un porcentaje o un monto de descuento"})

    with db_conn() as conn:
        if conn.execute("SELECT id FROM discount_codes WHERE code = ?", (code,)).fetchone():
            return h.send_json(409, {"error": "Ese código ya existe"})
        cur = conn.execute(
            "INSERT INTO discount_codes (code, percent_off, amount_off, expires_at, max_uses) "
            "VALUES (?, ?, ?, ?, ?)",
            (code, percent_off, amount_off, str(body.get("expires_at", "")).strip() or None, max_uses),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("PATCH", r"^/api/discount-codes/(?P<id>\d+)$")
def update(h, id, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    if "active" not in body:
        return h.send_json(400, {"error": "Nada para actualizar"})
    with db_conn() as conn:
        cur = conn.execute(
            "UPDATE discount_codes SET active = ? WHERE id = ?",
            (1 if body["active"] else 0, int(id)),
        )
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/discount-codes/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM discount_codes WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})
