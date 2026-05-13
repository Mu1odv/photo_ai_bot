import sqlite3
from datetime import date
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_db()

    def get_connection(self):
        """Bazaga ulanish"""
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
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
                order_date TEXT,
                daily_seq INTEGER,
                admin_notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._ensure_orders_columns(cursor)

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
            order_date = date.today().isoformat()
            cursor.execute(
                "SELECT COALESCE(MAX(daily_seq), 0) as max_seq FROM orders WHERE order_date = ?",
                (order_date,)
            )
            max_seq = cursor.fetchone()[0] or 0
            daily_seq = max_seq + 1
            cursor.execute(
                """
                INSERT INTO orders (user_id, username, full_name, order_type, details, price, status, order_date, daily_seq)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, full_name, order_type, details, price, status, order_date, daily_seq)
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

    def get_orders(self, status=None, order_date=None, limit=None):
        """Buyurtmalarni filtr bilan olish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM orders"
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status)
            if order_date:
                conditions.append("order_date = ?")
                params.append(order_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    def get_orders_count(self, status=None, order_date=None):
        """Buyurtmalar sonini olish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT COUNT(*) as count FROM orders"
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status)
            if order_date:
                conditions.append("order_date = ?")
                params.append(order_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()

    def _ensure_orders_columns(self, cursor):
        cursor.execute("PRAGMA table_info(orders)")
        columns = {row["name"] for row in cursor.fetchall()}

        if "order_date" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN order_date TEXT")

        if "daily_seq" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN daily_seq INTEGER")

        if "admin_notified" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN admin_notified INTEGER DEFAULT 0")

        cursor.execute("UPDATE orders SET admin_notified = 0 WHERE admin_notified IS NULL")

        self._backfill_order_meta(cursor)

    def _backfill_order_meta(self, cursor):
        cursor.execute(
            "SELECT id, created_at, order_date, daily_seq FROM orders ORDER BY created_at ASC, id ASC"
        )
        rows = cursor.fetchall()
        if not rows:
            return

        seq_by_date = {}
        updates = []

        for row in rows:
            order_date = row["order_date"] or self._extract_order_date(row["created_at"]) or date.today().isoformat()
            daily_seq = row["daily_seq"]

            if daily_seq is None:
                seq_by_date.setdefault(order_date, 0)
                seq_by_date[order_date] += 1
                daily_seq = seq_by_date[order_date]
            else:
                seq_by_date[order_date] = max(seq_by_date.get(order_date, 0), daily_seq)

            updates.append((order_date, daily_seq, row["id"]))

        cursor.executemany(
            "UPDATE orders SET order_date = ?, daily_seq = ? WHERE id = ?",
            updates,
        )

    @staticmethod
    def _extract_order_date(created_at):
        if not created_at:
            return None

        text = str(created_at)
        if len(text) >= 10 and text[4] == "-":
            return text[:10]
        return None

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

    def set_admin_notified(self, order_id, notified: bool):
        """Admin xabardor qilinganini belgilash"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET admin_notified = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (1 if notified else 0, order_id)
            )
            conn.commit()
        finally:
            conn.close()


# Global database instance
db = Database() 


