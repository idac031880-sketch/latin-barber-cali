"""Campañas de marketing. Se guardan y organizan por estado — el envío
real (WhatsApp/email) no está conectado, es para planear y llevar registro."""
from db import db_conn

ROUTES = []
STATUSES = {"borrador", "programada", "enviada"}


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


@register("GET", r"^/api/campaigns$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
    h.send_json(200, {"campaigns": [dict(r) for r in rows]})


@register("POST", r"^/api/campaigns$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    name = str(body.get("name", "")).strip()[:80]
    message = str(body.get("message", "")).strip()[:500]
    if not name or not message:
        return h.send_json(400, {"error": "Nombre y mensaje son obligatorios"})

    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO campaigns (name, message, channel, starts_at, ends_at) VALUES (?, ?, ?, ?, ?)",
            (
                name, message,
                str(body.get("channel", "whatsapp")).strip()[:20] or "whatsapp",
                str(body.get("starts_at", "")).strip() or None,
                str(body.get("ends_at", "")).strip() or None,
            ),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("PATCH", r"^/api/campaigns/(?P<id>\d+)$")
def update(h, id, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    status = str(body.get("status", "")).strip()
    if status not in STATUSES:
        return h.send_json(400, {"error": "Estado inválido"})
    with db_conn() as conn:
        cur = conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", (status, int(id)))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrada"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/campaigns/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM campaigns WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrada"})
    h.send_json(200, {"ok": True})
