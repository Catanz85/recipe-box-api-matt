import sqlite3


class UserIntegrityError(Exception):
    pass


def get_role(db, user_id):
    return db.execute(
        "SELECT role FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()


def find_by_username(db, username):
    row = db.execute(
        "SELECT id, username, password_hash, role "
        "FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    return dict(row) if row is not None else None


def create_user(db, username, email, password_hash):
    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash) "
            "VALUES (?, ?, ?)",
            (username, email, password_hash)
        )

        db.commit()

    except sqlite3.IntegrityError as exc:
        raise UserIntegrityError(str(exc)) from exc

    return cur.lastrowid
