import hashlib
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from urllib.parse import urlsplit
from fastapi import Depends, HTTPException, Request
from backend.app.storage.models import BrowserSession, Workspace

_attempts = defaultdict(deque)
_rate_lock = Lock()


def origin_key(value):
    """Compare exact origins without trusting arbitrary forwarded headers."""
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.path not in {'', '/'} or parsed.query or parsed.fragment):
            return None
        return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == 'https' else 80)
    except ValueError:
        return None


def get_db(request: Request):
    with request.app.state.db_session() as db:
        yield db


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def limit_attempts(request: Request, action: str, maximum: int, seconds: int):
    key=(request.client.host if request.client else 'unknown', action)
    current=time.monotonic()
    with _rate_lock:
        for old_key in list(_attempts):
            if not _attempts[old_key] or current-_attempts[old_key][-1]>3600:
                del _attempts[old_key]
        bucket=_attempts[key]
        while bucket and current-bucket[0]>seconds:
            bucket.popleft()
        if len(bucket)>=maximum:
            raise HTTPException(429, 'Demasiados intentos. Espera antes de volver a intentarlo.')
        bucket.append(current)


def get_workspace(request: Request, db=Depends(get_db)):
    token=request.cookies.get('aura_browser','')
    auth=db.get(BrowserSession,digest(token)) if token else None
    if auth is None or auth.expires_at<=int(time.time()):
        raise HTTPException(401,'El espacio de este navegador caducó. Actualiza la página para abrir uno nuevo automáticamente.')
    if request.method not in {'GET','HEAD','OPTIONS'}:
        if not secrets.compare_digest(request.headers.get('x-csrf-token',''),auth.csrf):
            raise HTTPException(403,'La sesión cambió. Actualiza la página antes de continuar.')
    workspace=db.get(Workspace,auth.workspace_id)
    if workspace is None:
        raise HTTPException(401,'No se pudo recuperar este espacio. Actualiza la página.')
    return workspace
