# src/database.py
import sqlite3
import pandas as pd
import hashlib
import logging
from datetime import datetime, date
from pathlib import Path
from contextlib import contextmanager
import threading
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations with thread safety and wallet integration."""
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize or migrate the database with required tables and columns."""
        with self.lock, self.get_connection() as conn:
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
                CREATE TABLE IF NOT EXISTS gemini_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wallets (
                    user_id INTEGER PRIMARY KEY,
                    upi_balance REAL NOT NULL DEFAULT 0,
                    cash_balance REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    category TEXT NOT NULL, title TEXT NOT NULL, amount REAL NOT NULL,
                    date DATE NOT NULL, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute("PRAGMA table_info(expenses)")
            columns = [col['name'] for col in cursor.fetchall()]
            if 'payment_method' not in columns:
                cursor.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'Cash'")
                logger.info("Migrated 'expenses' table: added 'payment_method' column.")

            conn.commit()
            logger.info("Database initialized/validated successfully.")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _hash_value(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def create_user(self, username: str, password: str) -> bool:
        password_hash = self._hash_value(password)
        with self.lock, self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                user_id = cursor.lastrowid
                cursor.execute("INSERT OR IGNORE INTO wallets (user_id, upi_balance, cash_balance) VALUES (?, 0, 0)", (user_id,))
                conn.commit()
                logger.info(f"User '{username}' and their wallet created successfully.")
                return True
            except sqlite3.IntegrityError:
                logger.warning(f"Failed to create user '{username}': username likely already exists.")
                return False

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        password_hash = self._hash_value(password)
        with self.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password_hash)).fetchone()
            if user:
                with self.lock:
                    conn.execute("INSERT OR IGNORE INTO wallets (user_id) VALUES (?)", (user['id'],))
                    conn.commit()
                return dict(user)
            return None

    def save_expense(self, expense_data: dict) -> str:
        user_id = expense_data['user_id']
        amount = expense_data['amount']
        method = expense_data.get('payment_method', 'Cash')
        
        with self.lock, self.get_connection() as conn:
            cursor = conn.cursor()
            wallet = cursor.execute("SELECT upi_balance, cash_balance FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
            if method == 'UPI' and wallet['upi_balance'] < amount:
                return f"Insufficient UPI balance. Current: ${wallet['upi_balance']:.2f}, Required: ${amount:.2f}."
            if method == 'Cash' and wallet['cash_balance'] < amount:
                return f"Insufficient Cash balance. Current: ${wallet['cash_balance']:.2f}, Required: ${amount:.2f}."

            try:
                if method == 'UPI':
                    cursor.execute("UPDATE wallets SET upi_balance = upi_balance - ? WHERE user_id = ?", (amount, user_id))
                else:
                    cursor.execute("UPDATE wallets SET cash_balance = cash_balance - ? WHERE user_id = ?", (amount, user_id))

                cursor.execute(
                    "INSERT INTO expenses (user_id, category, title, amount, date, notes, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, expense_data['category'], expense_data['title'], amount, expense_data['date'], expense_data.get('notes', ''), method)
                )
                conn.commit()
                return ""
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed in save_expense: {e}")
                return "A database error occurred. Transaction rolled back."

    def delete_expense(self, expense_id: int, user_id: int) -> bool:
        with self.lock, self.get_connection() as conn:
            cursor = conn.cursor()
            expense = cursor.execute("SELECT amount, payment_method FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)).fetchone()
            if not expense: return False
            try:
                if expense['payment_method'] == 'UPI':
                    cursor.execute("UPDATE wallets SET upi_balance = upi_balance + ? WHERE user_id = ?", (expense['amount'], user_id))
                else:
                    cursor.execute("UPDATE wallets SET cash_balance = cash_balance + ? WHERE user_id = ?", (expense['amount'], user_id))
                
                cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed in delete_expense: {e}")
                return False

    def update_expense(self, expense_id: int, user_id: int, updated_data: dict) -> str:
        with self.lock, self.get_connection() as conn:
            cursor = conn.cursor()
            old_expense = cursor.execute("SELECT amount, payment_method FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)).fetchone()
            if not old_expense: return "Transaction not found."

            wallet = cursor.execute("SELECT upi_balance, cash_balance FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
            temp_upi, temp_cash = wallet['upi_balance'], wallet['cash_balance']

            if old_expense['payment_method'] == 'UPI': temp_upi += old_expense['amount']
            else: temp_cash += old_expense['amount']
            
            new_amount, new_method = updated_data['amount'], updated_data['payment_method']

            if new_method == 'UPI' and temp_upi < new_amount: return f"Insufficient UPI balance for update. Available: ${temp_upi:.2f}, Required: ${new_amount:.2f}."
            if new_method == 'Cash' and temp_cash < new_amount: return f"Insufficient Cash balance for update. Available: ${temp_cash:.2f}, Required: ${new_amount:.2f}."
            
            try:
                if old_expense['payment_method'] == 'UPI':
                    cursor.execute("UPDATE wallets SET upi_balance = upi_balance + ? WHERE user_id = ?", (old_expense['amount'], user_id))
                else:
                    cursor.execute("UPDATE wallets SET cash_balance = cash_balance + ? WHERE user_id = ?", (old_expense['amount'], user_id))

                if new_method == 'UPI':
                    cursor.execute("UPDATE wallets SET upi_balance = upi_balance - ? WHERE user_id = ?", (new_amount, user_id))
                else:
                    cursor.execute("UPDATE wallets SET cash_balance = cash_balance - ? WHERE user_id = ?", (new_amount, user_id))

                cursor.execute(
                    "UPDATE expenses SET category=?, title=?, amount=?, date=?, notes=?, payment_method=? WHERE id=? AND user_id=?",
                    (updated_data['category'], updated_data['title'], new_amount, updated_data['date'], updated_data.get('notes', ''), new_method, expense_id, user_id)
                )
                conn.commit()
                return ""
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed in update_expense: {e}")
                return "A database error occurred during update. Transaction rolled back."

    def get_wallet_balances(self, user_id: int) -> Optional[dict]:
        with self.get_connection() as conn:
            wallet = conn.execute("SELECT upi_balance, cash_balance FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
            return dict(wallet) if wallet else {'upi_balance': 0.0, 'cash_balance': 0.0}

    def set_wallet_balances(self, user_id: int, upi_balance: float, cash_balance: float) -> bool:
        with self.lock, self.get_connection() as conn:
            try:
                conn.execute("UPDATE wallets SET upi_balance = ?, cash_balance = ? WHERE user_id = ?", (upi_balance, cash_balance, user_id))
                conn.commit()
                return True
            except Exception:
                return False

    def get_filtered_expenses(self, user_id: int, start_date, end_date, categories: list, amount_range: tuple) -> pd.DataFrame:
        query = "SELECT * FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ?"
        params = [user_id, start_date, end_date]
        if categories:
            query += f" AND category IN ({','.join(['?']*len(categories))})"
            params.extend(categories)
        if amount_range:
            query += " AND amount BETWEEN ? AND ?"
            params.extend(amount_range)
        query += " ORDER BY date DESC, id DESC"
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        return df

    def get_expense_by_id(self, expense_id: int, user_id: int) -> Optional[dict]:
        with self.get_connection() as conn:
            expense_row = conn.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)).fetchone()
            if not expense_row: return None
            expense_dict = dict(expense_row)
            if isinstance(expense_dict.get('date'), str):
                 expense_dict['date'] = datetime.strptime(expense_dict['date'], '%Y-%m-%d').date()
            return expense_dict
            
    def get_user_categories(self, user_id: int) -> list:
        with self.get_connection() as conn:
            categories = conn.execute("SELECT DISTINCT category FROM expenses WHERE user_id = ? ORDER BY category", (user_id,)).fetchall()
            return [cat['category'] for cat in categories]
            
    def get_user_expense_years(self, user_id: int) -> list:
        with self.get_connection() as conn:
            years = conn.execute(
                "SELECT DISTINCT STRFTIME('%Y', date) as year FROM expenses WHERE user_id = ? ORDER BY year DESC",
                (user_id,)
            ).fetchall()
            return [row['year'] for row in years]
            
    # --- CACHING METHODS (Restored) ---
    def get_cached_response(self, prompt: str) -> Optional[str]:
        """Retrieves a cached Gemini response from the database."""
        prompt_hash = self._hash_value(prompt)
        with self.get_connection() as conn:
            result = conn.execute("SELECT response_json FROM gemini_cache WHERE prompt_hash = ?", (prompt_hash,)).fetchone()
            return result['response_json'] if result else None

    def cache_response(self, prompt: str, response: str):
        """Saves a Gemini response to the cache table."""
        prompt_hash = self._hash_value(prompt)
        with self.lock, self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO gemini_cache (prompt_hash, response_json) VALUES (?, ?)", (prompt_hash, response))
            conn.commit()