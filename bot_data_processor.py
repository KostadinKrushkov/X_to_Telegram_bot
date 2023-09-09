import json
import os

from constants import BotConstants


class BotDataProcessor:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_subscribed_chat_ids()
        self._load_monitored_user()
        self._load_filter_keywords()

    def _load_subscribed_chat_ids(self):
        subscribed_chat_ids = set()
        try:
            with open(BotConstants.SUBSCRIBED_CHAT_IDS_FILE, 'r') as file:
                data = json.load(file)
                subscribed_chat_ids = set(data.get('chat_ids', []))
        except FileNotFoundError:
            pass
        except Exception:
            # File was corrupted, clear file
            os.remove(BotConstants.SUBSCRIBED_CHAT_IDS_FILE)
        self.subscribed_chat_ids = subscribed_chat_ids

    def _load_monitored_user(self):
        monitored_user = None
        try:
            with open(BotConstants.MONITORED_USER_FILE, 'r') as file:
                monitored_user = file.read()
        except FileNotFoundError:
            pass
        self.monitored_twitter_user = monitored_user

    def _load_filter_keywords(self):
        filter_keywords = set()
        try:
            with open(BotConstants.FILTER_KEYWORDS_FILE, 'r') as file:
                filter_keywords = set(line.strip() for line in file)
        except FileNotFoundError:
            pass
        self.filter_keywords = filter_keywords

    def _save_subscribed_chat_ids(self):
        data = {'chat_ids': list(self.subscribed_chat_ids)}
        with open(BotConstants.SUBSCRIBED_CHAT_IDS_FILE, 'w') as file:
            json.dump(data, file)

    def add_subscribed_chat_id(self, chat_id):
        self.subscribed_chat_ids.add(chat_id)
        self._save_subscribed_chat_ids()

    def remove_subscribed_chat_id(self, chat_id):
        self.subscribed_chat_ids.remove(chat_id)
        self._save_subscribed_chat_ids()

    def set_filter_keywords(self, keywords):
        self.filter_keywords = set(keywords)
        with open(BotConstants.FILTER_KEYWORDS_FILE, 'w') as file:
            file.write('\n'.join(self.filter_keywords))

    def get_formatted_keywords(self):
        return ','.join([f"'{keyword}'" for keyword in self.filter_keywords])

    def set_monitored_user(self, username):
        self.monitored_twitter_user = username
        with open(BotConstants.MONITORED_USER_FILE, 'w') as file:
            file.write(f"{username}")

    def get_formatted_monitored_username(self):
        if self.monitored_twitter_user is None:
            return None
        return self.monitored_twitter_user[1:]
