"""
Authentication (WHO are you) and authorization (WHAT are you allowed to
do). This is the assignment's section 2.

Plain-English picture:
  - Login is a wristband counter at a concert. You show ID once (username
    + password), they hand you a wristband (JWT). After that, you flash
    the wristband at every gate instead of showing ID again.
  - The wristband has a colour (the `role` claim inside the JWT). Staff
    gates only let in orange wristbands (admin), general gates let in
    any wristband (user), etc. That colour-check is RBAC.

For this take-home, three demo users are seeded in the database at
startup (see main.py) instead of a signup flow, since the brief only
asks for login + JWT, not full user management.
"""
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import User, get_db

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str, role: str) -> str:
    """Builds the JWT. `exp` is the wristband's expiry time — after this,
    the token stops working and the user must log in again."""
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: every protected endpoint declares
    `user: User = Depends(get_current_user)` and FastAPI runs this first,
    checking the wristband before the endpoint's own code ever runs."""
    payload = decode_token(token)
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*allowed_roles: str):
    """Factory for a role-gate dependency, e.g. Depends(require_role('admin')).
    This is the RBAC part: it doesn't just check 'is there a valid token',
    it checks 'is this wristband the right colour for this gate'."""

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to access this resource",
            )
        return user

    return role_checker


def seed_demo_users(db: Session) -> None:
    """Creates 3 demo accounts (admin/user/readonly) the first time the
    app starts, so there's something to log in with out of the box."""
    demo_users = [
        ("admin", "admin123", "admin"),
        ("alice", "alice123", "user"),
        ("viewer", "viewer123", "readonly"),
    ]
    for username, password, role in demo_users:
        if not db.query(User).filter(User.username == username).first():
            db.add(User(username=username, hashed_password=hash_password(password), role=role))
    db.commit()
