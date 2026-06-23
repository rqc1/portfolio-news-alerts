"""
Autenticación y gestión de usuarios (capa de producción).

Implementa registro/login con contraseña hasheada (bcrypt vía passlib) y
emisión/verificación de JSON Web Tokens (jose). Expone dependencias de FastAPI
para proteger endpoints y recuperar el usuario autenticado.

Diseño:
  - `AUTH_ENABLED=false` (por defecto): la API permanece abierta; las
    dependencias devuelven un usuario anónimo. Mantiene compatibilidad con el
    frontend actual y los tests.
  - `AUTH_ENABLED=true`: los endpoints protegidos exigen `Authorization:
    Bearer <token>` válido.

Seguridad (OWASP):
  - Contraseñas nunca en claro: hash bcrypt con sal por usuario.
  - Tokens firmados HMAC-SHA256 con secreto de entorno (`JWT_SECRET`).
  - Validación de email y longitud mínima de contraseña en la frontera.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, EmailStr, Field

import config
from database.mongodb import MongoDB

logger = logging.getLogger(__name__)

# Usamos la librería `bcrypt` directamente: passlib 1.7.x es incompatible con
# bcrypt >= 4 (lee `bcrypt.__about__`, eliminado en versiones nuevas).

# bcrypt solo procesa los primeros 72 bytes de la contraseña; truncamos de
# forma explícita y consistente para hash y verificación.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]

# tokenUrl apunta al endpoint de login; auto_error=False para poder degradar
# a usuario anónimo cuando AUTH_ENABLED=false.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field("", max_length=120)


class UserPublic(BaseModel):
    id: str
    email: str
    name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    """Identidad resuelta en cada request (real o anónima)."""
    id: str
    email: str = ""
    is_anonymous: bool = False


# ---------------------------------------------------------------------------
# Hash y tokens
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(plain), hashed.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return False


def create_access_token(subject: str, email: str = "") -> tuple[str, int]:
    """Devuelve (token, expires_in_segundos)."""
    expire_minutes = config.JWT_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "email": email, "exp": expire}
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token, expire_minutes * 60


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Servicio de usuarios
# ---------------------------------------------------------------------------
class AuthService:
    @staticmethod
    async def register(data: UserCreate) -> UserPublic:
        existing = await MongoDB.users().find_one({"email": data.email.lower()})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado",
            )
        doc = {
            "email": data.email.lower(),
            "name": data.name,
            "password_hash": hash_password(data.password),
            "created_at": datetime.now(timezone.utc),
        }
        result = await MongoDB.users().insert_one(doc)
        return UserPublic(id=str(result.inserted_id), email=doc["email"], name=doc["name"])

    @staticmethod
    async def authenticate(email: str, password: str) -> Optional[dict]:
        user = await MongoDB.users().find_one({"email": email.lower()})
        if not user or not verify_password(password, user.get("password_hash", "")):
            return None
        return user


# ---------------------------------------------------------------------------
# Dependencias FastAPI
# ---------------------------------------------------------------------------
async def get_current_user(token: Optional[str] = Depends(_oauth2_scheme)) -> CurrentUser:
    """Resuelve la identidad del request.

    - Si AUTH_ENABLED=false → usuario anónimo (compatibilidad).
    - Si AUTH_ENABLED=true  → exige token válido o lanza 401.
    """
    if not config.AUTH_ENABLED:
        return CurrentUser(id="anonymous", is_anonymous=True)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(id=payload["sub"], email=payload.get("email", ""))
