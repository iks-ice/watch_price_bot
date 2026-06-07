import os
import sqlite3
from logger_config import get_logger

logger = get_logger("database")

class DatabaseManager:
    """Manages the lifetime and configuration of the SQLite database connections."""
    
    def __init__(self):
        # Fetch path from environment variable or fallback to local default
        self.db_path = os.getenv("DATABASE_PATH", "tracker.db")
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured connection instance with WAL mode enabled."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for asynchronous concurrent access safely inside Docker
            conn.execute("PRAGMA journal_mode=WAL;")
            return conn
        except sqlite3.Error:
            logger.exception(f"Failed to establish database connection to {self.db_path}")
            raise

    def _init_db(self) -> None:
        """Executes initial schema migrations for products and users tables."""
        try:
            with self.get_connection() as conn:
                # Create tables sequentially using standard cursor execution
                cursor = conn.cursor()
                
                # Products metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        url TEXT NOT NULL,
                        last_price REAL DEFAULT 0
                    );
                """)
                
                # Users tracking registration table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT
                    );
                """)
                
                conn.commit()
            logger.info("Database schema initialized successfully.")
        except sqlite3.Error:
            logger.exception("Critical error during database schema initialization")
            raise
