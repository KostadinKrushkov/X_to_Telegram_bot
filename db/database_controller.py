import sqlite3
import asyncio
from datetime import datetime
from sqlite3.dbapi2 import IntegrityError

from constants import BotConstants
from db.db_utilities import async_retry_on_lock


class Tweet:
    def __init__(self, tweet_id, date, is_posted, message, author):
        self.tweet_id = tweet_id
        self.date = date
        self.is_posted = is_posted
        self.message = message
        self.author = author


class DatabaseController:
    DB_NAME = BotConstants.DATABASE_PATH
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    DATE_FORMAT = '%Y-%m-%d'

    def __init__(self):
        self.lock = asyncio.Lock()
        # Note: init db sync since __init__ can't be async
        self._initialize_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.DB_NAME, timeout=10, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn

    def _initialize_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY,
                tweet_id INTEGER UNIQUE,
                is_posted INTEGER,
                date TEXT,
                message TEXT,
                author TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @async_retry_on_lock()
    async def insert_tweet(self, tweet):
        tweet_id = tweet.id
        date = tweet.date.strftime(self.DATETIME_FORMAT)
        message = tweet.rawContent
        author = tweet.user.username
        is_posted = False

        async with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO tweets (tweet_id, date, is_posted, message, author)
                    VALUES (?, ?, ?, ?, ?)
                ''', (tweet_id, date, is_posted, message, author))
                conn.commit()
            except IntegrityError:
                pass
            finally:
                conn.close()

    async def retrieve_tweets_by_author(self, author):
        async with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tweet_id, date, is_posted, message, author
                FROM tweets WHERE author = ?
            ''', (author,))
            rows = cursor.fetchall()
            conn.close()
        return rows

    async def retrieve_today_unposted_tweets(self, author):
        today = datetime.now().strftime(self.DATE_FORMAT)
        async with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tweet_id, date, is_posted, message, author
                FROM tweets
                WHERE author = ? AND strftime('%Y-%m-%d', date) = ? AND is_posted = 0
                ORDER BY date
            ''', (author, today))
            rows = cursor.fetchall()
            conn.close()

        return [Tweet(*row) for row in rows]

    async def mark_tweet_as_posted(self, tweet_id):
        async with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tweets
                SET is_posted = 1
                WHERE tweet_id = ?
            ''', (tweet_id,))
            conn.commit()
            conn.close()


if __name__ == "__main__":
    async def main():
        controller = DatabaseController()

        print("Tweets by 'FinancialPear':")
        tweets = await controller.retrieve_tweets_by_author('FinancialPear')
        for tweet in tweets:
            print(tweet)

        # Example: insert, retrieve, and mark tweets
        # from twitter_scraper import TwitterScraper
        # scraper = TwitterScraper()
        # tweets = await scraper.save_latest_tweets('DeItaone', ['$TSLA', 'Gold', '$AAPL', 'OIL'])
        #
        # for tweet in tweets:
        #     await controller.insert_tweet(tweet)
        #
        # unposted = await controller.retrieve_today_unposted_tweets('DeItaone')
        # for tweet in unposted:
        #     print(tweet.message)
        #     await controller.mark_tweet_as_posted(tweet.tweet_id)
        #
        # unposted = await controller.retrieve_today_unposted_tweets('DeItaone')
        # for tweet in unposted:
        #     print(tweet.message)

    asyncio.run(main())
