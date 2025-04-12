import sqlite3

from constants import BotConstants

print("Running VACUUM...")
conn = sqlite3.connect(BotConstants.DATABASE_PATH)
conn.execute('VACUUM')
conn.close()
print("VACUUM completed.")
