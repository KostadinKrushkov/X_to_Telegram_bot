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
            logging.FileHandler(log_file_path, 'a', 'utf-8'),
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

    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Sending quick start info in response to /help."
                f"Command issued by {str(update.effective_user)}")
    await update.message.reply_text("""This is the Twitter to Telegram Bot

Quickstart:
1. To set the keywords that you want to match in the latest tweets use:
/set_keywords - '$NVDA' '$TSLA' '$AMZN' '$APPL' '$NIO' '$MSFT' '$NFLX' '$META' 'Gold' 'Silver' 'NASDAQ' 'S&P 500' 'OIL' - <bot normal command password>

2. To monitor an individual twitter user use:
/monitor @DeItaone <bot normal command password>

# Choose chat or channel
3.1. To officially make the bot start posting the new tweets to your chat:
/start_sharing <bot sharing password>

To make the bot start posting the new tweets to your channel.
3.2.1. Add the @X_to_telegram_bot to your channel with admin rights and then write /post_to_channel in your channel chat.

3.2.2. Forward that message to the bot privately (right click message -> forward -> @X_to_twitter_bot). 
This will show you the channel id that you need to pass on the next command.

Finally execute:
3.2.3. /start_sharing_on_channel <channel id> <bot sharing password>


If you are annoyed or want to stop the sharing of tweets
- For chats send this command:
/stop_sharing <bot sharing password>

- For channels send this command to the bot privately (using the channel id that you get. It will not start notifying until correct password is received when you forwarded the /post_to_channel message)
/stop_sharing_to_channel <channel id> <bot sharing password>

""" + current_configuration)


async def set_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not await validate_args_and_password_for_normal_command(chat_id, update, context):
        return

    processor = context.application.injected_bot_data_processor
    text = update.message.text

    try:
        pattern = r"'([^']*)'"
        keywords = re.findall(pattern, text.split('-')[1])
        print(keywords)
    except Exception as e:
        logger.error(f"{BotConstants.IMPORTANT_LOG_MARKER}| Failed to change the bot keywords. Reason: '{str(e)}'."
                     f"Command issued by {str(update.effective_user)}")
        return await update.message.reply_text("The commands needs to have a dash before the keywords and quotes for each one. "
                                               f"e.g: \n/set_keywords <bot normal command password> {BotConstants.BOT_NAME} - '$TSLA' 'gold' 'S&P 500'")

    if keywords:
        logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}| The changing the bots keywords to: '{str(keywords)}'. "
                    f"Command issued by {str(update.effective_user)}")
        processor.set_filter_keywords(keywords)
        await update.message.reply_text(f"Successfully updated the keywords to be {keywords}")
    else:
        await update.message.reply_text(
            f"No keywords were found in your command, please try again using the following example\n"
            f"/set_keywords <bot normal command password> {BotConstants.BOT_NAME} - '$TSLA' 'gold' 'S&P")


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.edited_message or update.channel_post or update.edited_channel_post or (update.callback_query.message if update.callback_query else None)
    if not message:
        logger.error("Could not find message to reply to.")

    chat_id = message.chat_id
    if not await validate_args_and_password_for_normal_command(chat_id, update, context, num_required_args=2):
        return

    processor = context.application.injected_bot_data_processor
    twitter_user = context.args[-2]

    if not twitter_user or not str(twitter_user).startswith('@'):
        logger.error(f"{BotConstants.IMPORTANT_LOG_MARKER}| Failed to change the person to monitor. "
                     f"The twitter user needs to start with @."
                     f"Command issued by {str(update.effective_user)}")

        return await message.reply_text(f"The commands need to have a @user and password."
                                               f"e.g. /monitor {BotConstants.BOT_NAME} @DeItaone <bot normal command password>")

    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}| Changing the person to monitor to: '{str(twitter_user)}'. "
                f"Command issued by {str(update.effective_user)}")
    processor.set_monitored_user(twitter_user)
    await message.reply_text(f"Successfully started monitoring the user {twitter_user}.")


async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Starting scheduled message.")
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

    await scraper.save_latest_tweets(username)
    messages_and_urls = await scraper.get_unposed_tweet_messages_and_mark_the_tweets_as_posted(
        username, processor.filter_keywords)

    for chat_id in processor.subscribed_chat_ids:
        for message, url in messages_and_urls:
            logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Sending scheduled message: '{message}' to chat '{str(chat_id)}'")
            await context.bot.send_message(chat_id=chat_id, text=str(message), disable_web_page_preview=True)
            # await context.bot.send_photo(chat_id, url, caption=message)  # send photo of google search as well


async def validate_password_or_send_error_message(password, update, context, chat_id, is_start_stop_sharing_command=False):
    bot_password = os.getenv("BOT_SHARING_PASSWORD") if is_start_stop_sharing_command else os.getenv("BOT_OTHER_COMMANDS_PASSWORD")
    if password != bot_password:
        logger.error(f"{BotConstants.IMPORTANT_LOG_MARKER}|The validation failed because user passed incorrect password."
                     f"Command issued by {str(update.effective_user)}")
        await context.bot.send_message(
            chat_id, 'Incorrect password. Will not change behavior until correct password is entered.')
        return False
    return True


async def validate_args_and_password_for_normal_command(chat_id, update, context, num_required_args=None):
    # Check if password was passed as an argument
    if not context.args or (len(context.args) != num_required_args if num_required_args else False):
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the template for the command shown when you execute /help')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, update, context, chat_id):
        return
    return True


async def _start_sharing_tweets_on_chat_id(chat_id, update, context):
    processor = context.application.injected_bot_data_processor
    processor.add_subscribed_chat_id(chat_id)

    remove_repeating_job(context)

    if not processor.monitored_twitter_user or not processor.filter_keywords or not processor.subscribed_chat_ids:
        await send_bot_not_configured(chat_id, context)
    else:
        start_repeating_job()
        logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Successfully started bot."
                    f"Command issued by {str(update.effective_user)}")
        await context.bot.send_message(
            chat_id=chat_id,
            text='Successfully started bot. '
                 f'Every minute the latest tweets will be read and you will be notified if it hits your keywords at the scheduled time ({Scheduler.get_available_zone()} UTC)!')


async def start_sharing_tweets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.args:
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the command in the following format:'
                     '/start_sharing <bot sharing password>')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, update, context, chat_id, is_start_stop_sharing_command=True):
        return

    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Started sharing tweets on chat id {str(chat_id)}."
                f"Command issued by {str(update.effective_user)}")
    await _start_sharing_tweets_on_chat_id(chat_id, update, context)


async def start_sharing_tweets_on_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.args or len(context.args) > 2:
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the command in the following format:'
                     '/start_sharing_on_channel <channel_id> <bot sharing password>')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, update, context, chat_id, is_start_stop_sharing_command=True):
        return

    if len(context.args) == 2:
        chat_id = context.args[-2]

    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Started sharing tweets on chat id {str(chat_id)}."
                f"Command issued by {str(update.effective_user)}")
    await _start_sharing_tweets_on_chat_id(chat_id, update, context)


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
    if not context.args:
        logger.error(
            f"{BotConstants.IMPORTANT_LOG_MARKER}|Failed to execute stop_sharing for chat_id: {str(chat_id)} "
            f"due to incorrect parameters passed. Please use the template for this command shown in the /help. "
            f"Command issued by {str(update.effective_user)}")

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, update, context, chat_id, is_start_stop_sharing_command=True):
        return

    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Request to shop sharing tweets for chat_id: {str(chat_id)}."
                f"Command issued by {str(update.effective_user)}")
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
                                            f'Enter the following command with the bot sharing password to finalize.'
                                            f'\n/start_sharing_on_channel {channel_id} <bot sharing password>')
    else:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text='Please forward this message from the channel you want to follow to the bot. (after you have added the bot as an admin.)')


async def stop_sharing_to_channel(update, context):
    chat_id = update.message.chat_id
    if not context.args or len(context.args) > 2:
        logger.error(
            f"{BotConstants.IMPORTANT_LOG_MARKER}|Failed to execute stop_sharing_to_channel for chat_id: {str(chat_id)} "
            f"due to incorrect parameters passed. Please use the template for this command shown in the /help. "
            f"Command issued by {str(update.effective_user)}")
        await context.bot.send_message(
            chat_id, 'Incorrect data passed. Please use the command in the following format:'
                     '\n/stop_sharing_to_channel <channel_id> <bot sharing password>. '
                     '\nIf you have forgotten the channel id send "/post_to_channel" in your channel and forward it to this bot again. ')
        return

    password = context.args[-1]
    if not await validate_password_or_send_error_message(password, update, context, chat_id, is_start_stop_sharing_command=True):
        return

    if len(context.args) == 2:
        chat_id = context.args[-2]

    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Stopped sharing tweets to chat_id: {str(chat_id)}")
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
    logger.info(f"{BotConstants.IMPORTANT_LOG_MARKER}|Starting bot!")
    app.run_polling(poll_interval=3)
