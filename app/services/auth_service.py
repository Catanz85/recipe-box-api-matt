from datetime import datetime, timedelta, timezone

import jwt

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app.data import users as repository


class AuthError(Exception):
    def __init__(self, code, message, detail=None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


def register_user(db, username, password):
    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(password, str)
        or not password
    ):
        raise AuthError(
            "invalid",
            "username and password are required"
        )

    username = username.strip()
    email = f"{username}@example.com"

    password_hash = generate_password_hash(password)

    try:
        user_id = repository.create_user(
            db,
            username,
            email,
            password_hash
        )

    except repository.UserIntegrityError as exc:
        detail = str(exc)

        if (
            "users.username" in detail
            or "users.email" in detail
        ):
            raise AuthError(
                "conflict",
                "username already exists"
            ) from exc

        raise AuthError(
            "registration_failed",
            "registration failed",
            detail
        ) from exc

    return {
        "id": user_id,
        "username": username
    }


def authenticate_user(db, username, password, jwt_secret):
    if (
        not isinstance(username, str)
        or not isinstance(password, str)
    ):
        raise AuthError(
            "invalid",
            "username and password are required"
        )

    user = repository.find_by_username(db, username)

    if not user or not check_password_hash(
        user["password_hash"], password
    ):
        raise AuthError(
            "unauthorized",
            "Invalid credentials"
        )

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(hours=1),
    }

    token = jwt.encode(
        payload,
        jwt_secret,
        algorithm="HS256"
    )

    return {
        "id": user["id"],
        "username": user["username"],
        "access_token": token,
        "token_type": "Bearer",
    }
