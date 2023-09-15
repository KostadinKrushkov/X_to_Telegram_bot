from dotenv import load_dotenv
load_dotenv()

import os
import logging
import sys
import re
from datetime import datetime
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from bot_data_processor import BotDataProcessor
from constants import BotConstants
from scheduler import Scheduler
from twitter_scraper import TwitterScraper


def setup_logging(log_directory='log'):
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file_path = os.path.join(log_directory, 'bot.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(),
        ],
        datefmt='%m/%d/%Y %I:%M:%S %p',
    )

    logger = logging.getLogger(BotConstants.BOT_NAME)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
    return logger


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_currently_sharing = update.message.chat_id in context.application.injected_bot_data_processor.subscribed_chat_ids
    current_configuration = f"""
Current configuration:
    Monitoring: @{context.application.injected_bot_data_processor.get_formatted_monitored_username()}
    Keywords: {context.application.injected_bot_data_processor.get_formatted_keywords()}
    Sharing {'disabled' if not is_currently_sharing else 'enabled'} for current chat.
    {f'Sharing enabled for chats {context.application.injected_bot_data_processor.get_formatted_subscribed_chat_ids()}' 
    if context.application.injected_bot_data_processor.subscribed_chat_ids else ''}
"""
    await update.message.reply_text("""This is the Twitter to Telegram Bot

Quickstart:
1. To set the keywords that you want to match in the latest tweets use:
/set_keywords - '$NVDA' '$TSLA' '$AMZN' '$APPL' '$NIO' '$MSFT' '$NFLX' '$META' 'Gold' 'Silver' 'NASDAQ' 'S&P 500' 'OIL'

2. To monitor an individual twitter user use:
/monitor @DeItaone @X_to_telegram_bot

# Choose chat or channel
3.1. To officially make the bot start posting the new tweets to your chat:
/start_sharing @X_to_telegram_bot <bot Password>

To make the bot start posting the new tweets to your channel.
3.2.1. Add the @X_to_telegram_bot to your channel with admin rights and then write /post_to_channel in your channel chat.

3.2.2. Forward that message to the bot privately (right click message -> forward -> @X_to_twitter_bot). 
This will show you the channel id that you need to pass on the next command.

Finally execute:
3.2.3. /start_sharing <channel id> <bot Password>


If you are annoyed or want to stop the sharing of tweets
- For chats send this command:
/stop_sharing @X_to_telegram_bot

- For channels send this command to the bot privately (using the channel id that yoWill not start notifying until correct password is entered.u received when you forwarded the /post_to_channel message)
/stop_sharing_to_channel <channel id> <Bot Password>

""" + current_configuration)


async def set_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processor = context.application.injected_bot_data_processor
    text = update.message.text

    try:
        pattern = r"'([^']*)'"
        keywords = re.findall(pattern, text.split('-')[1])
        print(keywords)
    except Exception:
        return await update.message.reply_text("The commands needs to have a dash before the keywords and quotes for each one. "
                                               f"e.g: \n/set_keywords {BotConstants.BOT_NAME} - '$TSLA' 'gold' 'S&P 500'")

    if keywords:
        processor.set_filter_keywords(keywords)
        await update.message.reply_text(f"Successfully updated the keywords to be {keywords}")
    else:
        await update.message.reply_text(
            f"No keywords were found in your command, please try again using the following example\n"
            f"/set_keywords {BotConstants.BOT_NAME} - '$TSLA' 'gold' 'S&P")


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processor = context.application.injected_bot_data_processor
    twitter_user = context.args[-1]

    if not twitter_user or not str(twitter_user).startswith('@'):
        return await update.message.reply_text(f"The commands need to have a @user at the end "
                                               f"e.g. /monitor {BotConstants.BOT_NAME} @DeItaone")

    processor.set_monitored_user(twitter_user)
    await update.message.reply_text(f"Successfully started monitoring the user {twitter_user}.")


async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Starting scheduled message.")
    if not Scheduler.is_datetime_in_time_range(datetime.now()):
        return

    processor = context.application.injected_bot_data_processor
    scraper = context.application.injected_scraper

    username = processor.get_formatted_monitored_username()
    if not username or not processor.filter_keywords or not processor.subscribed_chat_ids:
        for chat_id in processor.subscribed_chat_ids:
            await send_bot_not_configured(chat_id, context)
        remove_repeating_job(context)
        return

    messages_and_urls = await scraper.poll_latest_tweets(username, processor.filter_keywords)

    for chat_id in processor.subscribed_chat_ids:
        for message, url in messages_and_urls:
            await context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
            # await context.bot.send_photo(chat_id, url, caption=message)  # send photo of google search as well


async def validate_password_or_send_error_message(password, context, chat_id):
    if password != os.getenv("BOT_PASSWORD"):
        await context.bot.send_message(
            chat_id, 'Incorrect password. Will not change behavior until correct password is entered.')
        return False
    return True


async def _start_sharing_tweets_on_chat_id(chat_id, context):
    processor = context.application.injected_bot_data_processor
    processor.add_subscribed_chat_id(chat_id)

    remove_repeating_job(context)

    if not processor.monitored_twitter_user or not processor.filter_keywords or not processor.subscribed_chat_ids:
        await send_bot_not_configured(chat_id, context)
    else:
        start_repeating_job()
        await context.bot.send_message(
            chat_id=chat_id,
            text='Successfully started bot. '
                 f'Every minute the latest tweets will be read and you will be notified if it hits your keywords at the scheduled time ({Scheduler.get_available_zone()} UTC)!')


async def start_sharing_tweets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.args:
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the command in the following format:'
                     '/start_sharing <bot password>')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, context, chat_id):
        return

    await _start_sharing_tweets_on_chat_id(chat_id, context)


async def start_sharing_tweets_on_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.args or len(context.args) > 2:
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the command in the following format:'
                     '/start_sharing_on_channel <channel_id> <bot password>')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, context, chat_id):
        return

    if len(context.args) == 2:
        chat_id = context.args[-2]
    await _start_sharing_tweets_on_chat_id(chat_id, context)


async def _stop_sharing_tweets(chat_id, context):
    if chat_id not in context.application.injected_bot_data_processor.subscribed_chat_ids:
        await context.bot.send_message(chat_id=chat_id, text='You have already stopped the automatic messages.')
    else:
        context.application.injected_bot_data_processor.remove_subscribed_chat_id(chat_id)
        await context.bot.send_message(chat_id=chat_id, text='Stopping automatic messages!')
    remove_repeating_job(context)

    if context.application.injected_bot_data_processor.subscribed_chat_ids:
        start_repeating_job()


async def stop_sharing_tweets(update, context):
    chat_id = update.message.chat_id
    await _stop_sharing_tweets(chat_id, context)


async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = None
    try:
        channel_id = update.message.forward_from_chat.id
    except:
        pass

    if channel_id:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text=f'Please remember this channel id "{channel_id}". \n'
                                            f'Enter the following command with the bot password to finalize.'
                                            f'\n/start_sharing_on_channel {channel_id} <bot password>')
    else:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text='Please forward this message from the channel you want to follow to the bot. (after you have added the bot as an admin.)')


async def stop_sharing_to_channel(update, context):
    chat_id = update.message.chat_id
    if not context.args or len(context.args) > 2:
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the command in the following format:'
                     '\n/stop_sharing_to_channel <channel_id> <bot password>. '
                     '\nIf you have forgotten the channel id send "/post_to_channel" in your channel and forward it to this bot again. ')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, context, chat_id):
        return

    if len(context.args) == 2:
        chat_id = context.args[-2]
    await _stop_sharing_tweets(chat_id, context)


async def send_bot_not_configured(chat_id, context):
    return await context.bot.send_message(
        chat_id=chat_id,
        text="""The bot is not yet fully configured. You need to: 
1. Monitor a user. 
2. Set keywords to match in tweets. 
3. Start sharing tweets.

Please refer to the commands /help /monitor /set_keywords and /start_sharing""")


def remove_repeating_job(context):
    for job in context.job_queue.jobs():
        job.schedule_removal()


def start_repeating_job():
    job_queue.run_repeating(send_scheduled_message, 45, name=BotConstants.AUTOMATIC_POLL_AND_MSG_JOB_NAME)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
        os.chdir(sys.argv[1])

    logger = setup_logging()
    bot_data_processor = BotDataProcessor()

    app = Application.builder().token(BotConstants.BOT_TOKEN).build()
    app.injected_bot_data_processor = bot_data_processor

    app.injected_scraper = TwitterScraper()

    job_queue = app.job_queue
    start_repeating_job()

    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("set_keywords", set_keywords))
    app.add_handler(CommandHandler("start_sharing", start_sharing_tweets))
    app.add_handler(CommandHandler("stop_sharing", stop_sharing_tweets))
    app.add_handler(CommandHandler("start_sharing_on_channel", start_sharing_tweets_on_channel))
    app.add_handler(CommandHandler("stop_sharing_to_channel", stop_sharing_to_channel))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CommandHandler("post_to_channel", post_to_channel))
    logger.info("Starting bot!")
    app.run_polling(poll_interval=3)
