from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import User


class UserIntegrityError(Exception):
    pass


def get_role(user_id):
    user = db.session.get(User, user_id)

    if user is None:
        return None

    return {"role": user.role}


def find_by_username(username):
    user = db.session.scalar(
        select(User).where(User.username == username)
    )

    if user is None:
        return None

    return {
        "id": user.id,
        "username": user.username,
        "password_hash": user.password_hash,
        "role": user.role,
    }


def create_user(username, email, password_hash):
    user = User(
        username=username,
        email=email,
        password_hash=password_hash
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise UserIntegrityError(str(exc.orig)) from exc

    return user.id
