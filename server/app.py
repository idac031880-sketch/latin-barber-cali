#!/usr/bin/env python3
"""Servidor de Latin Barber Cali: sirve el sitio y la API de la intranet.

Ejecutar:
    python3 server/app.py

Luego abre:
    http://localhost:8890                 sitio público (con formulario de reserva)
    http://localhost:8890/intranet.html   panel del dueño (agenda, personal, clientes...)

No usa dependencias externas — solo la librería estándar de Python 3.
La base de datos vive en server/data.db (se crea sola la primera vez).

Un archivo por recurso, en routes/ — mismo patrón que la plantilla del
proyecto (auth, services, staff, clients, appointments, inventory,
expenses, campaigns, discount_codes, dashboard).
"""
from __future__ import annotations

import http.server
import mimetypes
import os
import re
import socketserver
from pathlib import Path
from urllib.parse import urlparse

import auth
import db
from routes import (
    auth_routes, services, staff, clients, appointments,
    inventory, expenses, campaigns, discount_codes, dashboard,
)

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("PORT", 8890))

STATIC_PAGES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/intranet.html": "intranet.html",
}
STATIC_DIRS = {
    "/css/": ROOT / "css",
    "/js/": ROOT / "js",
    "/images/": ROOT / "images",
}

ROUTE_MODULES = [
    auth_routes, services, staff, clients, appointments,
    inventory, expenses, campaigns, discount_codes, dashboard,
]
ROUTES_BY_METHOD: dict[str, list] = {"GET": [], "POST": [], "PATCH": [], "DELETE": []}
for module in ROUTE_MODULES:
    for method, pattern, fn in module.ROUTES:
        ROUTES_BY_METHOD[method].append((re.compile(pattern), fn))


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "LatinBarber/1.0"

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

    # -- helpers usados por los módulos de routes/ --
    def send_json(self, status: int, payload: dict):
        import json
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self, max_bytes: int = 20_000):
        import json
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return None
        if length <= 0 or length > max_bytes:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def require_auth(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            self.send_json(401, {"error": "No autorizado"})
            return None
        payload = auth.verify_token(header[7:].strip())
        if not payload:
            self.send_json(401, {"error": "No autorizado"})
            return None
        return payload

    def serve_static_file(self, base_dir: Path, rel_path: str):
        base_dir = base_dir.resolve()
        target = (base_dir / rel_path.lstrip("/")).resolve()
        if target != base_dir and base_dir not in target.parents:
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        content_type, _ = mimetypes.guess_type(str(target))
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self, method: str):
        path = urlparse(self.path).path

        if method == "GET":
            if path in STATIC_PAGES:
                self.serve_static_file(ROOT, STATIC_PAGES[path])
                return
            for prefix, base_dir in STATIC_DIRS.items():
                if path.startswith(prefix):
                    self.serve_static_file(base_dir, path[len(prefix):])
                    return

        for pattern, fn in ROUTES_BY_METHOD[method]:
            match = pattern.match(path)
            if match:
                fn(self, **match.groupdict())
                return

        self.send_error(404)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    db.init_db()
    try:
        with Server(("0.0.0.0", PORT), Handler) as httpd:
            httpd.daemon_threads = True
            print(f"Latin Barber Cali corriendo en http://localhost:{PORT}")
            print(f"Intranet en          http://localhost:{PORT}/intranet.html")
            httpd.serve_forever()
    except OSError as e:
        print(f"No se pudo iniciar el servidor en el puerto {PORT}: {e}")
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
