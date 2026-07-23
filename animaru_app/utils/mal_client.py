import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from animaru_app.utils.config import CONFIG_DIR

MAL_CLIENT_ID = "611b81c2b4a86c23a9e0f1b6e9f0a210"
MAL_REDIRECT_URI = "http://localhost:8543/callback"
MAL_AUTH_URL = "https://myanimelist.net/v1/oauth2/authorize"
MAL_TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"
MAL_API_BASE = "https://api.myanimelist.net/v2"

TOKEN_FILE = CONFIG_DIR / "mal_token.json"

_verifier = None


def _generate_pkce_pair():
    global _verifier
    _verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(_verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return _verifier, challenge


def get_auth_url() -> str:
    verifier, challenge = _generate_pkce_pair()
    params = {
        "response_type": "code",
        "client_id": MAL_CLIENT_ID,
        "redirect_uri": MAL_REDIRECT_URI,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{MAL_AUTH_URL}?{urllib.parse.urlencode(params)}"


def get_pkce_verifier() -> str | None:
    global _verifier
    return _verifier


def _load_token() -> dict | None:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _save_token(token: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(token, indent=2))


def get_valid_token() -> str | None:
    token = _load_token()
    if not token:
        return None
    access = token.get("access_token")
    if not access:
        return None
    return access


def exchange_code(code: str, verifier: str) -> dict | None:
    data = urllib.parse.urlencode({
        "client_id": MAL_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": MAL_REDIRECT_URI,
        "code_verifier": verifier,
    }).encode()

    try:
        req = urllib.request.Request(MAL_TOKEN_URL, data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        token = json.loads(resp.read())
        _save_token(token)
        return token
    except Exception as e:
        print(f"[MAL] Code exchange failed: {e}")
        return None


def is_authenticated() -> bool:
    return get_valid_token() is not None


def logout():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def _api_get(endpoint: str, params: dict | None = None) -> dict | None:
    token = get_valid_token()
    if not token:
        return None

    url = f"{MAL_API_BASE}{endpoint}"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return None
        return None
    except Exception:
        return None


def _api_patch(endpoint: str, data: dict) -> bool:
    token = get_valid_token()
    if not token:
        return False

    url = f"{MAL_API_BASE}{endpoint}"
    body = urllib.parse.urlencode(data).encode()

    req = urllib.request.Request(url, data=body, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return None
        return False
    except Exception:
        return False


def update_anime_progress(mal_id: int, episode_count: int, status: str = "watching"):
    return _api_patch(f"/anime/{mal_id}/my_list_status", {
        "num_watched_episodes": episode_count,
        "status": status,
    })


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = params.get("code", [None])[0]
        if code:
            self.server.code = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Animaru</h1>"
                b"<p>Authorization successful! You can close this window.</p>"
                b"</body></html>"
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization failed</h1></body></html>"
            )

    def log_message(self, fmt, *args):
        pass


def start_auth_server() -> str | None:
    server = http.server.HTTPServer(("127.0.0.1", 8543), _CallbackHandler)
    server.code = None

    def _serve():
        server.timeout = 300
        while server.code is None:
            server.handle_request()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    return server
