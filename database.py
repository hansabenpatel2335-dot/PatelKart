import hashlib
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "patelkart.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
        return secrets.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


def initialize_database():
    with closing(connect()) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                address TEXT,
                birthday TEXT,
                profile_picture TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS carts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                UNIQUE(user_id, product_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                unit_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            );
        """)

        demo = connection.execute("SELECT id FROM users WHERE username = ?", ("customer",)).fetchone()
        if demo is None:
            connection.execute("""
                INSERT INTO users(username, password_hash, name, phone, address, birthday)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("customer", hash_password("patel123"), "Customer", "", "", ""))
        connection.commit()


def create_user(username: str, password: str, name: str, phone: str, address: str, birthday: str) -> tuple[bool, str]:
    username = username.strip()
    if len(username) < 3:
        return False, "Username must contain at least 3 characters."
    if len(password) < 6:
        return False, "Password must contain at least 6 characters."

    with closing(connect()) as connection:
        if connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            return False, "That username already exists."
        connection.execute("""
            INSERT INTO users(username, password_hash, name, phone, address, birthday)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, hash_password(password), name.strip(), phone.strip(), address.strip(), birthday))
        connection.commit()
    return True, "Account created. You can now log in."


def authenticate(username: str, password: str):
    with closing(connect()) as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def recover_password(username: str, phone: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 6:
        return False, "Password must contain at least 6 characters."
    with closing(connect()) as connection:
        row = connection.execute("SELECT id, phone FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if row is None:
            return False, "No account was found for that username."
        if not row["phone"] or row["phone"] != phone.strip():
            return False, "The username and phone number do not match."
        connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), row["id"]))
        connection.commit()
    return True, "Password updated. You can now log in."


def get_user(username: str):
    with closing(connect()) as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username,),).fetchone()
    return dict(row) if row else None


def update_profile(username: str, name: str, phone: str, address: str, birthday: str, picture_bytes: bytes | None = None, picture_name: str = "") -> dict:
    picture_path = None
    if picture_bytes:
        suffix = Path(picture_name).suffix.lower() or ".png"
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            suffix = ".png"
        picture_path = UPLOAD_DIR / f"{username}{suffix}"
        picture_path.write_bytes(picture_bytes)

    with closing(connect()) as connection:
        if picture_path:
            connection.execute("""
                UPDATE users SET name=?, phone=?, address=?, birthday=?, profile_picture=? WHERE username=?
            """, (name.strip(), phone.strip(), address.strip(), birthday, str(picture_path), username))
        else:
            connection.execute("""
                UPDATE users SET name=?, phone=?, address=?, birthday=? WHERE username=?
            """, (name.strip(), phone.strip(), address.strip(), birthday, username))
        connection.commit()
    return get_user(username)


def load_cart(username: str) -> dict[int, int]:
    with closing(connect()) as connection:
        user = connection.execute("SELECT id FROM users WHERE username = ?", (username,),).fetchone()
        if not user:
            return {}
        rows = connection.execute("SELECT product_id, quantity FROM carts WHERE user_id = ?", (user["id"],)).fetchall()
    return {row["product_id"]: row["quantity"] for row in rows}


def set_cart(username: str, cart: dict[int, int]):
    with closing(connect()) as connection:
        user = connection.execute("SELECT id FROM users WHERE username = ?", (username,),).fetchone()
        if not user:
            return
        connection.execute("DELETE FROM carts WHERE user_id = ?", (user["id"],))
        connection.executemany("""
            INSERT INTO carts(user_id, product_id, quantity) VALUES (?, ?, ?)
        """, [(user["id"], product_id, quantity) for product_id, quantity in cart.items() if quantity > 0])
        connection.commit()


def create_order(username: str, cart: dict[int, int], products: list[dict]) -> int:
    total = sum(next(p["price"] for p in products if p["id"] == product_id) * quantity for product_id, quantity in cart.items())
    with closing(connect()) as connection:
        user = connection.execute("SELECT id FROM users WHERE username = ?", (username,),).fetchone()
        if not user:
            raise ValueError("User does not exist")
        cursor = connection.execute("INSERT INTO orders(user_id, total, status) VALUES (?, ?, ?)", (user["id"], total, "Confirmed"))
        order_id = cursor.lastrowid
        for product_id, quantity in cart.items():
            product = next(p for p in products if p["id"] == product_id)
            connection.execute("""
                INSERT INTO order_items(order_id, product_id, product_name, unit_price, quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, product_id, product["name"], product["price"], quantity))
        connection.execute("DELETE FROM carts WHERE user_id = ?", (user["id"],))
        connection.commit()
    return order_id


def get_orders(username: str):
    with closing(connect()) as connection:
        user = connection.execute("SELECT id FROM users WHERE username = ?", (username,),).fetchone()
        if not user:
            return []
        orders = connection.execute("""
            SELECT id, total, status, created_at FROM orders WHERE user_id = ? ORDER BY id DESC
        """, (user["id"],)).fetchall()
        result = []
        for order in orders:
            items = connection.execute("""
                SELECT product_name, unit_price, quantity FROM order_items WHERE order_id = ?
            """, (order["id"],)).fetchall()
            result.append({"id": order["id"], "total": order["total"], "status": order["status"], "created_at": order["created_at"], "items": [dict(item) for item in items]})
    return result
