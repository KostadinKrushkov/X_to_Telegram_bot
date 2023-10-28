import sqlite3
from datetime import datetime
from sqlite3.dbapi2 import IntegrityError


class Tweet:
    def __init__(self, tweet_id, date, is_posted, message, author):
        self.tweet_id = tweet_id
        self.date = date
        self.is_posted = is_posted
        self.message = message
        self.author = author


class DatabaseController:
    DB_NAME = 'data/database'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    DATE_FORMAT = '%Y-%m-%d'

    def __init__(self):
        self.conn = sqlite3.connect(self.DB_NAME)
        self.cursor = self.conn.cursor()
        self.create_tweets_table()  # Ensure the table exists

    def create_tweets_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY,
                tweet_id INTEGER UNIQUE,
                is_posted INTEGER,
                date TEXT,
                message TEXT,
                author TEXT
            )
        ''')
        self.conn.commit()

    def insert_tweet(self, tweet):
        tweet_id = tweet.id
        date = tweet.date.strftime(self.DATETIME_FORMAT)
        message = tweet.rawContent
        author = tweet.user.username
        is_posted = False

        try:
            self.cursor.execute('''
                INSERT INTO tweets (tweet_id, date, is_posted, message, author)
                VALUES (?, ?, ?, ?, ?)
            ''', (tweet_id, date, is_posted, message, author))
            self.conn.commit()
        except IntegrityError:  # expected to fail on duplicate tweet insert
            pass

    def retrieve_tweets_by_author(self, author):
        self.cursor.execute('SELECT tweet_id, date, is_posted, message, author FROM tweets WHERE author = ?', (author, ))
        return self.cursor.fetchall()

    def retrieve_today_unposted_tweets(self, author):
        today = datetime.now().strftime(self.DATE_FORMAT)
        self.cursor.execute('''
            SELECT tweet_id, date, is_posted, message, author FROM tweets
            WHERE author = ? AND strftime('%Y-%m-%d', date) = ? AND is_posted = 0
            ORDER BY date
        ''', (author, today))

        tweet_list = []
        for row in self.cursor.fetchall():
            tweet_list.append(Tweet(*row))
        return tweet_list

    def mark_tweet_as_posted(self, tweet_id):
        self.cursor.execute('''
            UPDATE tweets
            SET is_posted = 1
            WHERE tweet_id = ?
        ''', (tweet_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    controller = DatabaseController()
    for tweet in controller.retrieve_tweets_by_author('FinancialPear'):
        print(tweet)

    # from twitter_scraper import TwitterScraper
    # import asyncio
    # scraper = TwitterScraper()
    # tweets = asyncio.run(scraper.save_latest_tweets('DeItaone', ['$TSLA', 'Gold', '$AAPL', 'OIL']))
    #
    # for tweet in tweets:
    #     controller.insert_tweet(tweet)
    #
    # for tweet in controller.retrieve_today_unposted_tweets('DeItaone'):
    #     print(tweet.message)
    #     controller.mark_tweet_as_posted(tweet.tweet_id)
    #
    # for tweet in controller.retrieve_today_unposted_tweets('DeItaone'):
    #     print(tweet.message)




