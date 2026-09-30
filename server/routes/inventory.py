"""Stock de productos/insumos."""
from db import db_conn

ROUTES = []


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


@register("GET", r"^/api/inventory$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM inventory ORDER BY name ASC").fetchall()
    h.send_json(200, {"inventory": [dict(r) for r in rows]})


@register("POST", r"^/api/inventory$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    name = str(body.get("name", "")).strip()[:80]
    if not name:
        return h.send_json(400, {"error": "El nombre es obligatorio"})
    try:
        quantity = float(body.get("quantity", 0))
        min_stock = float(body.get("min_stock", 0))
    except (TypeError, ValueError):
        return h.send_json(400, {"error": "Cantidad inválida"})

    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO inventory (name, quantity, unit, min_stock) VALUES (?, ?, ?, ?)",
            (name, quantity, str(body.get("unit", "unidad")).strip()[:20] or "unidad", min_stock),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("PATCH", r"^/api/inventory/(?P<id>\d+)$")
def update(h, id, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})

    fields, values = [], []
    if "name" in body:
        fields.append("name = ?"); values.append(str(body["name"]).strip()[:80])
    if "unit" in body:
        fields.append("unit = ?"); values.append(str(body["unit"]).strip()[:20])
    for key in ("quantity", "min_stock"):
        if key in body:
            try:
                values.append(float(body[key]))
            except (TypeError, ValueError):
                return h.send_json(400, {"error": "Cantidad inválida"})
            fields.append(f"{key} = ?")
    if not fields:
        return h.send_json(400, {"error": "Nada para actualizar"})
    fields.append("updated_at = datetime('now')")

    values.append(int(id))
    with db_conn() as conn:
        cur = conn.execute(f"UPDATE inventory SET {', '.join(fields)} WHERE id = ?", values)
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/inventory/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM inventory WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})
