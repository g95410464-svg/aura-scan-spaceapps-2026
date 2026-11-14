import hashlib
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import Depends, HTTPException, Request
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import select
from backend.app.storage.models import AuthSession, User

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_attempts = defaultdict(deque)
_rate_lock = Lock()


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


def verify_password(password, encoded):
    try:
        return hasher.verify(encoded,password)
    except (VerificationError,InvalidHashError):
        return False


def authorize(request: Request, db=Depends(get_db)):
    token=request.cookies.get('aura_session','')
    auth=db.get(AuthSession,digest(token)) if token else None
    if auth is None or auth.expires_at<=int(time.time()):
        raise HTTPException(401,'Inicia sesión para continuar.')
    if request.method not in {'GET','HEAD','OPTIONS'}:
        if not secrets.compare_digest(request.headers.get('x-csrf-token',''),auth.csrf):
            raise HTTPException(403,'La sesión cambió. Actualiza la página antes de continuar.')
    return db.scalar(select(User).where(User.id==auth.user_id))
