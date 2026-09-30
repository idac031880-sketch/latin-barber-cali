#!/usr/bin/env python3
"""Autorización única con Google Calendar. Se corre una sola vez, a mano.

Antes de correrlo:
  1. Crea un proyecto en https://console.cloud.google.com/
  2. Activa la "Google Calendar API".
  3. Crea credenciales -> "ID de cliente de OAuth" -> tipo "Aplicación de escritorio".
  4. Copia el "Client ID" y el "Client secret".
  5. Exporta esas dos variables antes de correr este script:

     export GOOGLE_CLIENT_ID="..."
     export GOOGLE_CLIENT_SECRET="..."
     python3 server/authorize_calendar.py

Abre la URL que imprime, entra con la cuenta de Google que administrará
el calendario del negocio, acepta el permiso. El script guarda el token
en server/google_token.json — ese archivo es el que necesita el servidor
para crear eventos. No lo compartas ni lo subas a git (ya está en .gitignore).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/oauth2callback"
SCOPE = "https://www.googleapis.com/auth/calendar.events"
TOKEN_PATH = Path(__file__).resolve().parent / "google_token.json"

received_code = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if code:
            received_code["code"] = code
            self.wfile.write("<h1>Listo</h1><p>Ya puedes cerrar esta pestaña.</p>".encode())
        else:
            self.wfile.write("<h1>Algo salió mal</h1><p>No llegó el código.</p>".encode())


def main():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Faltan GOOGLE_CLIENT_ID y/o GOOGLE_CLIENT_SECRET. Revisa las instrucciones arriba.")
        sys.exit(1)

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })

    print("=" * 60)
    print("Abre esta URL en tu navegador y acepta el permiso:")
    print(auth_url)
    print("=" * 60)
    print(f"Esperando en http://localhost:{REDIRECT_PORT} ...")

    server = HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    while "code" not in received_code:
        server.handle_request()

    code = received_code["code"]
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as res:
        payload = json.loads(res.read())

    if "refresh_token" not in payload:
        print("Google no devolvió un refresh_token. Vuelve a intentarlo:")
        print("revoca el acceso en https://myaccount.google.com/permissions y corre este script de nuevo.")
        sys.exit(1)

    TOKEN_PATH.write_text(json.dumps({"refresh_token": payload["refresh_token"]}, indent=2))
    print(f"Listo. Token guardado en {TOKEN_PATH}")
    print("Ahora define GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y GOOGLE_CALENDAR_ID")
    print("antes de iniciar el servidor (server/app.py) para activar la sincronización.")


if __name__ == "__main__":
    main()
