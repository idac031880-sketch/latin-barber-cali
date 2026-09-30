"""Sincronización de citas con Google Calendar.

No usa librerías externas — solo la librería estándar de Python (urllib).
Se activa sola cuando existen las credenciales; si no existen, todas las
funciones no hacen nada y una reserva se sigue guardando con normalidad.

Configuración (variables de entorno, ver server/.env.example):
    GOOGLE_CLIENT_ID       ID del cliente OAuth (tipo "app de escritorio")
    GOOGLE_CLIENT_SECRET   secreto del cliente OAuth
    GOOGLE_CALENDAR_ID     calendario del negocio (todas las citas)
    GOOGLE_BARBER_CALENDARS  "Nombre=id,Nombre2=id2" — un calendario por barbero

El token de acceso se renueva solo a partir del refresh token que genera
server/authorize_calendar.py (se corre una sola vez, a mano).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_PATH = Path(__file__).resolve().parent / "google_token.json"
TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
TIMEZONE = "America/Bogota"

_access_token_cache = {"token": None, "expires_at": 0}


def _client_credentials():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    return client_id, client_secret


def is_configured() -> bool:
    client_id, client_secret = _client_credentials()
    return bool(client_id and client_secret and TOKEN_PATH.is_file())


def barber_calendars() -> dict:
    """Lee GOOGLE_BARBER_CALENDARS='Nombre=id,Nombre2=id2' -> {"Nombre": "id"}."""
    raw = os.environ.get("GOOGLE_BARBER_CALENDARS", "")
    result = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, calendar_id = pair.split("=", 1)
        result[name.strip()] = calendar_id.strip()
    return result


def _get_access_token() -> str | None:
    if not is_configured():
        return None
    if _access_token_cache["token"] and _access_token_cache["expires_at"] > time.time() + 30:
        return _access_token_cache["token"]

    client_id, client_secret = _client_credentials()
    refresh_token = json.loads(TOKEN_PATH.read_text())["refresh_token"]

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            payload = json.loads(res.read())
    except urllib.error.URLError as e:
        print(f"[calendar] No se pudo renovar el token: {e}")
        return None

    _access_token_cache["token"] = payload["access_token"]
    _access_token_cache["expires_at"] = time.time() + payload.get("expires_in", 3000)
    return _access_token_cache["token"]


def create_event(calendar_id: str, summary: str, description: str, date: str, time_str: str, duration_minutes: int = 45):
    """Crea un evento. No lanza excepciones — devuelve True/False."""
    token = _get_access_token()
    if not token:
        return False

    start_dt = f"{date}T{time_str}:00"
    start_h, start_m = (int(x) for x in time_str.split(":"))
    end_total = start_h * 60 + start_m + duration_minutes
    end_dt = f"{date}T{end_total // 60:02d}:{end_total % 60:02d}:00"

    body = json.dumps({
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_dt, "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt, "timeZone": TIMEZONE},
    }).encode()

    url = EVENTS_URL.format(calendar_id=urllib.parse.quote(calendar_id, safe=""))
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            res.read()
        return True
    except urllib.error.URLError as e:
        print(f"[calendar] No se pudo crear el evento en {calendar_id}: {e}")
        return False


def sync_appointment(appt: dict):
    """Registra la cita en el calendario del negocio y en el del barbero (si aplica)."""
    if not is_configured():
        return

    summary = f"{appt['service']} — {appt['name']}"
    description = f"Teléfono: {appt['phone']}\nServicio: {appt['service']}"
    if appt.get("notes"):
        description += f"\nNotas: {appt['notes']}"
    if appt.get("barber"):
        description += f"\nBarbero: {appt['barber']}"

    business_calendar = os.environ.get("GOOGLE_CALENDAR_ID")
    if business_calendar:
        create_event(business_calendar, summary, description, appt["date"], appt["time"])

    barber = appt.get("barber")
    calendars = barber_calendars()
    if barber and barber in calendars:
        create_event(calendars[barber], summary, description, appt["date"], appt["time"])
