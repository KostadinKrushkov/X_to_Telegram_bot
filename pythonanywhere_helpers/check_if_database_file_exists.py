import os

from constants import BotConstants

print("Helper to check if database is healthy")
print(os.path.exists(BotConstants.DATABASE_PATH))  # Should be True
print(os.access(BotConstants.DATABASE_PATH, os.W_OK))  # Should also be True