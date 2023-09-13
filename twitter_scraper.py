import os
import json
import asyncio
from twscrape import API, gather
from twscrape.logger import set_log_level

from constants import ScraperConstants, TwitterAccountsConstants
from google.google_search import get_random_google_image
from scheduler import Scheduler

set_log_level("DEBUG")


class TwitterScraper:
    user_dict = None
    last_tweet_id = None
    api = None

    def __init__(self):
        self._load_user_dict()
        self._load_last_tweet_id()

    def save_monitored_user(self, data_json):
        try:
            with open(ScraperConstants.MONITORED_USER_DATA_FILE, 'w') as file:
                json.dump(data_json, file)
            return True
        except Exception as e:
            print(f"Error saving dictionary to file: {e}")
            return False

    def save_last_tweet_id(self):
        with open(ScraperConstants.LAST_TWEET_ID_FILE, "w") as file:
            file.write(str(self.last_tweet_id) if self.last_tweet_id else '')

    def _load_user_dict(self):
        try:
            with open(ScraperConstants.MONITORED_USER_DATA_FILE, 'r') as file:
                data_dict = json.load(file)
            user_dict = json.loads(data_dict)
        except FileNotFoundError:
            print(f"File '{ScraperConstants.MONITORED_USER_DATA_FILE}' not found.")
            user_dict = None
        except Exception as e:
            print(f"Error reading dictionary from file: {e}")
            user_dict = None
        self.user_dict = user_dict

    def _load_last_tweet_id(self):
        last_tweet_id = None
        if os.path.exists(ScraperConstants.LAST_TWEET_ID_FILE):
            with open(ScraperConstants.LAST_TWEET_ID_FILE, "r") as file:
                input = file.read()
                if input:
                    last_tweet_id = int(input)

        self.last_tweet_id = last_tweet_id

    async def reset_user(self, username):
        user = None
        for i in range(10):
            user = await self.api.user_by_login(username)
            if user is not None:
                break

        self.user_dict = user.dict()
        self.save_monitored_user(user.json())

    async def poll_latest_tweets(self, username, keywords):
        if self.api is None:
            self.api = await initialize_twscrape_api()

        if not self.user_dict or self.user_dict.get('username') != username:
            await self.reset_user(username)

        important_message_to_keywords = {}
        tweets = await gather(self.api.user_tweets(self.user_dict['id'], limit=50))
        for tweet in tweets:
            if not Scheduler.is_datetime_in_time_range(tweet.date):
                continue

            if self.last_tweet_id and tweet.id == self.last_tweet_id:
                break

            message = tweet.rawContent
            message = message.replace('&amp;', '&')
            for keyword in keywords:
                if keyword in message:
                    matching_keywords = important_message_to_keywords.get(message, [])
                    matching_keywords.append(keyword)
                    important_message_to_keywords[message] = matching_keywords

        message_prefix = f"""Twitter (https://twitter.com/{username})
{self.user_dict['displayname']} (@{username}) / X

"""

        self.last_tweet_id = tweets[0].id
        self.save_last_tweet_id()

        list_of_messages_and_google_urls = []
        for message, keywords in important_message_to_keywords.items():
            google_url = get_random_google_image(keywords[0])
            list_of_messages_and_google_urls.append((message_prefix + message, google_url))

        return list_of_messages_and_google_urls


async def initialize_twscrape_api():
    api = API()

    for account in TwitterAccountsConstants.twitter_accounts:
        if account.username:
            await api.pool.add_account(account.username, account.password, account.email, account.email_password)
    await api.pool.login_all()
    return api


if __name__ == "__main__":
    scraper = TwitterScraper()
    messages_and_urls = asyncio.run(scraper.poll_latest_tweets('DeItaone', ['$TSLA', 'Gold', '$AAPL', 'OIL']))
    print(messages_and_urls)
