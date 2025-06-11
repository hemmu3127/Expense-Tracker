# src/database.py
import sqlite3
import pandas as pd
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import threading
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations with thread safety."""
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._init_database()
    
    # Add this method inside the DatabaseManager class in src/database.py

    def get_user_expense_years(self, user_id: int) -> list:
        """Gets a list of unique years from a user's expenses."""
        with self.get_connection() as conn:
            years = conn.execute(
                "SELECT DISTINCT STRFTIME('%Y', date) as year FROM expenses WHERE user_id = ? ORDER BY year DESC",
                (user_id,)
            ).fetchall()
            return [row['year'] for row in years]

    def _init_database(self):
        """Initialize database with required tables and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date DATE NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gemini_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # --- REMOVED: sessions table ---
            conn.commit()
            logger.info("Database initialized successfully.")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    # Add this method inside the DatabaseManager class in src/database.py

    def delete_expense(self, expense_id: int, user_id: int) -> bool:
        """
        Deletes a specific expense entry, ensuring it belongs to the user.
        Returns True if deletion was successful, False otherwise.
        """
        with self.lock, self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM expenses WHERE id = ? AND user_id = ?",
                (expense_id, user_id)
            )
            conn.commit()
            # The cursor.rowcount will be > 0 only if a row was actually deleted.
            if cursor.rowcount > 0:
                logger.info(f"User {user_id} deleted expense {expense_id}.")
                return True
            else:
                logger.warning(f"User {user_id} failed to delete non-existent or unauthorized expense {expense_id}.")
                return False
    def _hash_value(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def create_user(self, username: str, password: str) -> bool:
        password_hash = self._hash_value(password)
        with self.lock, self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        password_hash = self._hash_value(password)
        with self.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password_hash)).fetchone()
            return dict(user) if user else None

    # --- REMOVED: All session management methods (create, validate, delete) ---

    def save_expense(self, expense_data: dict):
        with self.lock, self.get_connection() as conn:
            conn.execute(
                "INSERT INTO expenses (user_id, category, title, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (expense_data['user_id'], expense_data['category'], expense_data['title'], expense_data['amount'], expense_data['date'], expense_data.get('notes', ''))
            )
            conn.commit()

    def get_filtered_expenses(self, user_id: int, start_date, end_date, categories: list, amount_range: tuple) -> pd.DataFrame:
        query = "SELECT * FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ?"
        params = [user_id, start_date, end_date]
        if categories:
            query += f" AND category IN ({','.join(['?']*len(categories))})"
            params.extend(categories)
        if amount_range:
            query += " AND amount BETWEEN ? AND ?"
            params.extend(amount_range)
        query += " ORDER BY date DESC"
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        return df

    def get_user_categories(self, user_id: int) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            categories = cursor.execute("SELECT DISTINCT category FROM expenses WHERE user_id = ? ORDER BY category", (user_id,)).fetchall()
            return [cat['category'] for cat in categories]

    def get_max_expense_amount(self, user_id: int) -> float:
        with self.get_connection() as conn:
            result = conn.execute("SELECT MAX(amount) as max_amount FROM expenses WHERE user_id = ?", (user_id,)).fetchone()
            return result['max_amount'] or 1000.0

    def get_cached_response(self, prompt: str) -> Optional[str]:
        prompt_hash = self._hash_value(prompt)
        with self.get_connection() as conn:
            result = conn.execute("SELECT response_json FROM gemini_cache WHERE prompt_hash = ?", (prompt_hash,)).fetchone()
            return result['response_json'] if result else None

    def cache_response(self, prompt: str, response: str):
        prompt_hash = self._hash_value(prompt)
        with self.lock, self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO gemini_cache (prompt_hash, response_json) VALUES (?, ?)", (prompt_hash, response))
            conn.commit()