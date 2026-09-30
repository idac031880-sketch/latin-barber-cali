"""Citas: alta pública con chequeo de disponibilidad, gestión interna,
sincronización a Google Calendar. El núcleo del sistema."""
import re
from datetime import date

import calendar_sync
from db import db_conn
from routes import clients as clients_routes

ROUTES = []

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
STATUSES = {"pendiente", "confirmada", "cancelada", "completada"}


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


def _validate(body, conn):
    if not isinstance(body, dict):
        return "Solicitud inválida"
    name = str(body.get("name", "")).strip()
    phone = str(body.get("phone", "")).strip()
    service = str(body.get("service", "")).strip()
    appt_date = str(body.get("date", "")).strip()
    appt_time = str(body.get("time", "")).strip()

    if not name or len(name) > 80:
        return "El nombre no es válido"
    if not phone or len(phone) > 20:
        return "El teléfono no es válido"
    service_row = conn.execute(
        "SELECT id FROM services WHERE name = ? AND active = 1", (service,)
    ).fetchone()
    if not service_row:
        return "Elige un servicio válido"
    if not DATE_RE.match(appt_date):
        return "La fecha no es válida"
    if not TIME_RE.match(appt_time):
        return "La hora no es válida"
    if len(str(body.get("barber", ""))) > 60:
        return "El nombre del barbero no es válido"
    try:
        y, m, d = (int(x) for x in appt_date.split("-"))
        if date(y, m, d) < date.today():
            return "Elige una fecha desde hoy en adelante"
    except ValueError:
        return "La fecha no es válida"
    return None


@register("GET", r"^/api/appointments$")
def list_all(h, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT a.id, a.name, a.phone, a.service, a.date, a.time, a.notes, "
            "a.barber, a.staff_id, a.status, a.created_at, "
            "s.name AS staff_name, s.color AS staff_color "
            "FROM appointments a LEFT JOIN staff s ON s.id = a.staff_id "
            "ORDER BY a.date ASC, a.time ASC"
        ).fetchall()
    h.send_json(200, {"appointments": [dict(r) for r in rows]})


@register("POST", r"^/api/appointments$")
def create(h, **kwargs):
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})

    with db_conn() as conn:
        error = _validate(body, conn)
        if error:
            return h.send_json(400, {"error": error})

        name = str(body["name"]).strip()[:80]
        phone = str(body["phone"]).strip()[:20]
        service = str(body["service"]).strip()
        appt_date = str(body["date"]).strip()
        appt_time = str(body["time"]).strip()
        notes = str(body.get("notes", "")).strip()[:300]
        barber = str(body.get("barber", "")).strip()[:60]
        staff_id = body.get("staff_id")
        try:
            staff_id = int(staff_id) if staff_id else None
        except (TypeError, ValueError):
            staff_id = None

        clash = conn.execute(
            "SELECT id FROM appointments WHERE date = ? AND time = ? AND status != 'cancelada'"
            + (" AND staff_id = ?" if staff_id else ""),
            (appt_date, appt_time, staff_id) if staff_id else (appt_date, appt_time),
        ).fetchone()
        if clash:
            return h.send_json(409, {"error": "Ese horario ya está ocupado. Elige otra hora."})

        cur = conn.execute(
            "INSERT INTO appointments (name, phone, service, date, time, notes, barber, staff_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, phone, service, appt_date, appt_time, notes, barber or None, staff_id),
        )
        new_id = cur.lastrowid
        clients_routes.upsert_from_appointment(conn, name, phone)

    try:
        calendar_sync.sync_appointment({
            "name": name, "phone": phone, "service": service,
            "date": appt_date, "time": appt_time, "notes": notes, "barber": barber,
        })
    except Exception as e:
        print(f"[calendar] Error inesperado sincronizando: {e}")

    h.send_json(201, {"id": new_id, "message": "Cita agendada"})


@register("PATCH", r"^/api/appointments/(?P<id>\d+)$")
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
        cur = conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, int(id)))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrada"})
    h.send_json(200, {"ok": True})


@register("DELETE", r"^/api/appointments/(?P<id>\d+)$")
def delete(h, id, **kwargs):
    if not h.require_auth():
        return
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM appointments WHERE id = ?", (int(id),))
    if cur.rowcount == 0:
        return h.send_json(404, {"error": "No encontrada"})
    h.send_json(200, {"ok": True})
