import os

from constants import BotConstants


def check_if_database_is_healthy():
    print("Helper to check if database is healthy")
    print(os.path.exists(BotConstants.DATABASE_PATH))  # Should be True
    print(os.access(BotConstants.DATABASE_PATH, os.W_OK))  # Should also be True


if __name__ == "__main__":
    check_if_database_is_healthy()


# To use it go to:
#  /home/rocazzar/X_to_Telegram_bot
# And then run:
# /home/rocazzar/.local/bin/python -m pythonanywhere_helpers.check_if_database_file_exists