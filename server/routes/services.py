"""Catálogo de servicios y precios. GET /public sin auth (lo usa el sitio
y el formulario de reserva); el resto detrás de requireAuth."""
from db import db_conn

ROUTES = []


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


def _row_to_dict(row):
    d = dict(row)
    d["active"] = bool(d["active"])
    return d


@register("GET", r"^/api/services/public$")
def list_public(h, **kwargs):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, description, price, duration_minutes FROM services "
            "WHERE active = 1 ORDER BY name ASC"
        ).fetchall()
    h.send_json(200, {"services": [dict(r) for r in rows]})


@register("GET", r"^/api/services$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM services ORDER BY name ASC").fetchall()
    h.send_json(200, {"services": [_row_to_dict(r) for r in rows]})


@register("POST", r"^/api/services$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    name = str(body.get("name", "")).strip()[:80]
    if not name:
        return h.send_json(400, {"error": "El nombre es obligatorio"})
    description = str(body.get("description", "")).strip()[:300]
    try:
        price = max(0, int(body.get("price", 0)))
        duration = max(5, int(body.get("duration_minutes", 45)))
    except (TypeError, ValueError):
        return h.send_json(400, {"error": "Precio o duración inválidos"})

    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO services (name, description, price, duration_minutes) VALUES (?, ?, ?, ?)",
            (name, description, price, duration),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("PATCH", r"^/api/services/(?P<id>\d+)$")
def update(h, id, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})

    fields, values = [], []
    if "name" in body:
        fields.append("name = ?"); values.append(str(body["name"]).strip()[:80])
    if "description" in body:
        fields.append("description = ?"); values.append(str(body["description"]).strip()[:300])
    if "price" in body:
        try:
            values.append(max(0, int(body["price"])))
        except (TypeError, ValueError):
            return h.send_json(400, {"error": "Precio inválido"})
        fields.append("price = ?")
    if "duration_minutes" in body:
        try:
            values.append(max(5, int(body["duration_minutes"])))
        except (TypeError, ValueError):
            return h.send_json(400, {"error": "Duración inválida"})
        fields.append("duration_minutes = ?")
    if "active" in body:
        fields.append("active = ?"); values.append(1 if body["active"] else 0)

    if not fields:
        return h.send_json(400, {"error": "Nada para actualizar"})

    values.append(int(id))
    with db_conn() as conn:
        cur = conn.execute(f"UPDATE services SET {', '.join(fields)} WHERE id = ?", values)
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/services/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM services WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})
