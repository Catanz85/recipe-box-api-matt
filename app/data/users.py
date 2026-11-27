def get_role(db, user_id):
    return db.execute(
        "SELECT role FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
