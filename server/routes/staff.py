"""Profesionales (barberos). Cada uno puede tener su propio calendario de
Google (ver calendar_sync.py) y un color para identificarlo en la agenda."""
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


@register("GET", r"^/api/staff/public$")
def list_public(h, **kwargs):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, color FROM staff WHERE active = 1 ORDER BY name ASC"
        ).fetchall()
    h.send_json(200, {"staff": [dict(r) for r in rows]})


@register("GET", r"^/api/staff$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM staff ORDER BY name ASC").fetchall()
    h.send_json(200, {"staff": [_row_to_dict(r) for r in rows]})


@register("POST", r"^/api/staff$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    name = str(body.get("name", "")).strip()[:80]
    if not name:
        return h.send_json(400, {"error": "El nombre es obligatorio"})

    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO staff (name, phone, email, role_title, color, calendar_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                name,
                str(body.get("phone", "")).strip()[:20],
                str(body.get("email", "")).strip()[:120],
                str(body.get("role_title", "")).strip()[:60],
                str(body.get("color", "#101012")).strip()[:20],
                str(body.get("calendar_id", "")).strip()[:200],
            ),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("PATCH", r"^/api/staff/(?P<id>\d+)$")
def update(h, id, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})

    allowed = {
        "name": ("name", lambda v: str(v).strip()[:80]),
        "phone": ("phone", lambda v: str(v).strip()[:20]),
        "email": ("email", lambda v: str(v).strip()[:120]),
        "role_title": ("role_title", lambda v: str(v).strip()[:60]),
        "color": ("color", lambda v: str(v).strip()[:20]),
        "calendar_id": ("calendar_id", lambda v: str(v).strip()[:200]),
        "active": ("active", lambda v: 1 if v else 0),
    }
    fields, values = [], []
    for key, (column, coerce) in allowed.items():
        if key in body:
            fields.append(f"{column} = ?")
            values.append(coerce(body[key]))

    if not fields:
        return h.send_json(400, {"error": "Nada para actualizar"})

    values.append(int(id))
    with db_conn() as conn:
        cur = conn.execute(f"UPDATE staff SET {', '.join(fields)} WHERE id = ?", values)
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/staff/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM staff WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})
