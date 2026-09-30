"""Login. La intranet solo tiene un rol por ahora (admin)."""
import auth
from db import db_conn

ROUTES = []


def register(method, pattern):
    def deco(fn):
        ROUTES.append((method, pattern, fn))
        return fn
    return deco


@register("POST", r"^/api/auth/login$")
def login(h, **kwargs):
    body = h.read_json_body()
    if body is None:
        return h.send_json(400, {"error": "Solicitud inválida"})
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    if not row or not auth.verify_password(password, row["salt"], row["password_hash"]):
        return h.send_json(401, {"error": "Usuario o contraseña incorrectos"})
    h.send_json(200, {"token": auth.make_token(username, row["role"]), "username": username, "role": row["role"]})
