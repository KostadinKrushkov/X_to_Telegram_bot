from collections import namedtuple
import os
import pytz


class ScraperConstants:
    LAST_TWEET_ID_FILE = "data/last_tweet_id.txt"
    MONITORED_USER_DATA_FILE = "data/user_data.txt"


class BotConstants:
    BOT_NAME = os.getenv("BOT_NAME")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    AUTOMATIC_POLL_AND_MSG_JOB_NAME = "Poll twitter and send messsage"

    SUBSCRIBED_CHAT_IDS_FILE = 'data/subscribed_chat_ids.json'
    MONITORED_USER_FILE = 'data/monitored_user.txt'
    FILTER_KEYWORDS_FILE = 'data/filter_keywords.txt'


TwitterAccount = namedtuple('TwitterAccount', ['username', 'password', 'email', 'email_password'])


class TwitterAccountsConstants:
    FIRST_USERNAME = os.getenv("FIRST_USERNAME")
    FIRST_PASSWORD = os.getenv("FIRST_PASSWORD")
    FIRST_EMAIL = os.getenv("FIRST_EMAIL")
    FIRST_EMAIL_PASSWORD = os.getenv("FIRST_EMAIL_PASSWORD")

    SECOND_USERNAME = os.getenv("SECOND_USERNAME")
    SECOND_PASSWORD = os.getenv("SECOND_PASSWORD")
    SECOND_EMAIL = os.getenv("SECOND_EMAIL")
    SECOND_EMAIL_PASSWORD = os.getenv("SECOND_EMAIL_PASSWORD")

    THIRD_USERNAME = os.getenv("THIRD_USERNAME")
    THIRD_PASSWORD = os.getenv("THIRD_PASSWORD")
    THIRD_EMAIL = os.getenv("THIRD_EMAIL")
    THIRD_EMAIL_PASSWORD = os.getenv("THIRD_EMAIL_PASSWORD")

    twitter_accounts = [
        TwitterAccount(username=FIRST_USERNAME, password=FIRST_PASSWORD,
                       email=FIRST_EMAIL, email_password=FIRST_EMAIL_PASSWORD),
        TwitterAccount(username=SECOND_USERNAME, password=SECOND_PASSWORD,
                       email=SECOND_EMAIL, email_password=SECOND_EMAIL_PASSWORD),
        TwitterAccount(username=THIRD_USERNAME, password=THIRD_PASSWORD,
                       email=THIRD_EMAIL, email_password=THIRD_EMAIL_PASSWORD),
    ]


DESIRED_TIMEZONE = pytz.timezone("Europe/Istanbul")
