import json
import asyncio
from collections import defaultdict
from datetime import datetime

from twscrape import API, gather
from twscrape.logger import set_log_level

from constants import ScraperConstants, TwitterAccountsConstants
from database_controller import DatabaseController
from google.google_search import get_random_google_image
from scheduler import Scheduler

set_log_level("DEBUG")


class TwitterScraper:
    user_dict = None
    latest_tweet_id = None
    api = None

    def __init__(self):
        self._load_user_dict()
        self.controller = DatabaseController()

    def save_monitored_user(self, data_json):
        try:
            with open(ScraperConstants.MONITORED_USER_DATA_FILE, 'w') as file:
                json.dump(data_json, file)
            return True
        except Exception as e:
            print(f"Error saving dictionary to file: {e}")
            return False

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

    async def reset_user(self, username):
        user = None
        for i in range(10):
            user = await self.api.user_by_login(username)
            if user is not None:
                break

        self.user_dict = user.dict()
        self.save_monitored_user(user.json())

    async def save_latest_tweets(self, username):
        if self.api is None:
            self.api = await initialize_twscrape_api()

        if not self.user_dict or self.user_dict.get('username') != username:
            await self.reset_user(username)

        tweets = await gather(self.api.user_tweets(self.user_dict['id'], limit=10))
        tweets = sorted(tweets, key=lambda tweet: tweet.date, reverse=True)

        for tweet in tweets:
            self.controller.insert_tweet(tweet)

    async def get_unposed_tweet_messages_and_mark_the_tweets_as_posted(self, username, keywords):
        important_message_to_keywords = defaultdict(list)

        for tweet in self.controller.retrieve_today_unposted_tweets(username):
            self.controller.mark_tweet_as_posted(tweet.tweet_id)

            tweet_datetime = datetime.strptime(tweet.date, self.controller.DATETIME_FORMAT)
            if not Scheduler.is_datetime_from_today(tweet_datetime) \
                    or not Scheduler.is_datetime_in_time_range(tweet_datetime):
                continue

            message = tweet.message
            message = message.replace('&amp;', '&')
            for keyword in keywords:
                if keyword in message:
                    matching_keywords = important_message_to_keywords[message]
                    matching_keywords.append(keyword)

        list_of_messages_and_google_urls = []
        for message, keywords in important_message_to_keywords.items():
            google_url = get_random_google_image(keywords[0])
            list_of_messages_and_google_urls.append((message, google_url))

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

    test_username = 'DeItaone'
    asyncio.run(scraper.save_latest_tweets(test_username))
    messages_and_urls = asyncio.run(scraper.get_unposed_tweet_messages_and_mark_the_tweets_as_posted(
        test_username, ['$TSLA', 'Gold', '$AAPL', 'OIL', '$AMZN', '$INTC']))
    print(messages_and_urls)
