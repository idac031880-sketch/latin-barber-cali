"""Ficha e historial de cliente. Se crean solos cuando alguien reserva
(por teléfono), pero también se pueden agregar y editar a mano."""
from db import db_conn

ROUTES = []


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


def upsert_from_appointment(conn, name, phone):
    """Crea o actualiza el cliente al vuelo cuando entra una cita nueva."""
    existing = conn.execute("SELECT id FROM clients WHERE phone = ?", (phone,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE clients SET name = ?, updated_at = datetime('now') WHERE id = ?",
            (name, existing["id"]),
        )
    else:
        conn.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", (name, phone))


@register("GET", r"^/api/clients$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM appointments a WHERE a.phone = c.phone) AS visits,
                   (SELECT MAX(a.date) FROM appointments a WHERE a.phone = c.phone) AS last_visit
            FROM clients c ORDER BY c.updated_at DESC
        """).fetchall()
    h.send_json(200, {"clients": [dict(r) for r in rows]})


@register("GET", r"^/api/clients/(?P<id>\d+)/appointments$")
def history(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        client = conn.execute("SELECT * FROM clients WHERE id = ?", (int(id),)).fetchone()
        if not client:
            return h.send_json(404, {"error": "No encontrado"})
        rows = conn.execute(
            "SELECT id, service, date, time, notes, status FROM appointments "
            "WHERE phone = ? ORDER BY date DESC, time DESC",
            (client["phone"],),
        ).fetchall()
    h.send_json(200, {"client": dict(client), "appointments": [dict(r) for r in rows]})


@register("POST", r"^/api/clients$")
def create(h, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    name = str(body.get("name", "")).strip()[:80]
    phone = str(body.get("phone", "")).strip()[:20]
    if not name or not phone:
        return h.send_json(400, {"error": "Nombre y teléfono son obligatorios"})

    with db_conn() as conn:
        if conn.execute("SELECT id FROM clients WHERE phone = ?", (phone,)).fetchone():
            return h.send_json(409, {"error": "Ya existe un cliente con ese teléfono"})
        cur = conn.execute(
            "INSERT INTO clients (name, phone, email, notes) VALUES (?, ?, ?, ?)",
            (name, phone, str(body.get("email", "")).strip()[:120], str(body.get("notes", "")).strip()[:500]),
        )
        new_id = cur.lastrowid
    h.send_json(201, {"id": new_id})


@register("PATCH", r"^/api/clients/(?P<id>\d+)$")
def update(h, id, **kwargs):
    if not h.require_auth():
        return
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})

    allowed = {
        "name": ("name", lambda v: str(v).strip()[:80]),
        "email": ("email", lambda v: str(v).strip()[:120]),
        "notes": ("notes", lambda v: str(v).strip()[:500]),
    }
    fields, values = [], []
    for key, (column, coerce) in allowed.items():
        if key in body:
            fields.append(f"{column} = ?")
            values.append(coerce(body[key]))
    if not fields:
        return h.send_json(400, {"error": "Nada para actualizar"})
    fields.append("updated_at = datetime('now')")

    values.append(int(id))
    with db_conn() as conn:
        cur = conn.execute(f"UPDATE clients SET {', '.join(fields)} WHERE id = ?", values)
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/clients/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM clients WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrado"})
    h.send_json(200, {"ok": True})
