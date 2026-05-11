import sqlite3
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_db()

    def get_connection(self):
        """Bazaga ulanish"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Jadvallar yaratish"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY UNIQUE,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                order_type TEXT,
                details TEXT,
                price INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id, username=None, full_name=None):
        """Foydalanuvchini yaratish yoki ma'lumotlarini yangilash"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name)
            )
            cursor.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE id = ?",
                (username, full_name, user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_user(self, user_id):
        """Foydalanuvchi ma'lumotlarini olish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def get_balance(self, user_id):
        """Foydalanuvchi balansini olish."""
        user = self.get_user(user_id)
        return user['balance'] if user else 0

    def add_balance(self, user_id, amount, username=None, full_name=None):
        """Foydalanuvchi balansini yangilash."""
        self.add_user(user_id, username, full_name)

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (amount, user_id)
            )
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            conn.commit()
            return result['balance'] if result else 0
        finally:
            conn.close()

    def set_balance(self, user_id, amount):
        """Balansni to'g'ridan-to'g'ri o'rnatish."""
        self.add_user(user_id)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (amount, user_id))
            conn.commit()
            return amount
        finally:
            conn.close()

    def add_order(self, user_id, username, full_name, order_type, details, price, status="pending"):
        """Yangi buyurtma qo'shish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO orders (user_id, username, full_name, order_type, details, price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, full_name, order_type, details, price, status)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_order(self, order_id):
        """ID bo'yicha buyurtma olish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def get_pending_orders(self):
        """Kutayotgan buyurtmalarni olish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", ("pending",))
            return cursor.fetchall()
        finally:
            conn.close()

    def update_order_status(self, order_id, status):
        """Buyurtma holatini yangilash"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, order_id)
            )
            conn.commit()
        finally:
            conn.close()

    def update_order_details(self, order_id, details):
        """Buyurtma tafsilotlarini yangilash"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET details = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (details, order_id)
            )
            conn.commit()
        finally:
            conn.close()


# Global database instance
db = Database()