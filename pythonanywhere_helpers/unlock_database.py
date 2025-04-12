# pythonanywhere_helpers/unlock_database.py

import sqlite3
import os
from constants import BotConstants

db_path = BotConstants.DATABASE_PATH

print(f"Checking DB path: {db_path}")
if not os.path.exists(db_path):
    raise FileNotFoundError(f"Database not found at {db_path}")

print("Attempting WAL checkpoint...")
try:
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA wal_checkpoint(FULL)")
    print("Checkpoint successful.")
except Exception as e:
    print("Checkpoint failed:", e)
finally:
    conn.close()

print("Now running VACUUM...")
try:
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.execute("VACUUM")
    print("VACUUM completed.")
except Exception as e:
    print("VACUUM failed:", e)
finally:
    conn.close()
