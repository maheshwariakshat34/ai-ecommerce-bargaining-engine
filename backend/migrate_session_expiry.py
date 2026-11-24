"""
One-off migration script: adds session-expiry columns to bargaining_sessions
and creates the bargaining_rate_limits table.

Run from the project root:
    python backend/migrate_session_expiry.py
    python -m backend.migrate_session_expiry
"""

import os
import sqlite3

# ---------------------------------------------------------------------------
# DB path: script lives in backend/, DB lives in ../instance/ecommerce.db
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "instance", "ecommerce.db"))


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found at: {DB_PATH}")
        print("Make sure the Flask app has been started at least once so SQLite creates the DB.")
        return

    print(f"Connecting to database: {DB_PATH}")

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # ---------------------------------------------------------------
        # 1. Add missing columns to bargaining_sessions
        # ---------------------------------------------------------------
        cursor.execute("PRAGMA table_info(bargaining_sessions);")
        existing_columns = {row[1] for row in cursor.fetchall()}

        new_columns = [
            ("created_at",       "ALTER TABLE bargaining_sessions ADD COLUMN created_at DATETIME;"),
            ("last_activity_at", "ALTER TABLE bargaining_sessions ADD COLUMN last_activity_at DATETIME;"),
            ("expires_at",       "ALTER TABLE bargaining_sessions ADD COLUMN expires_at DATETIME;"),
        ]

        for col_name, alter_sql in new_columns:
            if col_name not in existing_columns:
                cursor.execute(alter_sql)
                print(f"  [+] Added column '{col_name}' to bargaining_sessions.")
            else:
                print(f"  [=] Column '{col_name}' already exists — skipped.")

        # ---------------------------------------------------------------
        # 2. Create bargaining_rate_limits table if it does not exist
        # ---------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bargaining_rate_limits (
                id              INTEGER  PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER  NOT NULL,
                product_id      INTEGER  NOT NULL,
                date            DATE     NOT NULL,
                session_count   INTEGER  NOT NULL DEFAULT 0,
                last_session_at DATETIME NOT NULL,
                UNIQUE(user_id, product_id, date)
            );
        """)

        # Detect whether the table was just created or already existed
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bargaining_rate_limits';"
        )
        if cursor.fetchone():
            print("  [=] Table 'bargaining_rate_limits' is ready (created or already existed).")

        # ---------------------------------------------------------------
        # 3. Commit and close
        # ---------------------------------------------------------------
        conn.commit()
        print("\nMigration completed successfully.")

    except sqlite3.Error as exc:
        print(f"\nERROR during migration: {exc}")
        if conn:
            conn.rollback()
            print("All changes rolled back — database is unchanged.")

    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
