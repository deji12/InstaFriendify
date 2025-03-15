from CloseFriends.celery import app
from celery.utils.log import get_task_logger
from bot.bot import InstagramBot

logger = get_task_logger(__name__)

@app.task(name='get_account_followers', time_limit=36000, soft_time_limit=34200)
def get_account_followers(user, username):

    bot = InstagramBot(user=user)
    # bot.get_followers_via_instagrapi(username=username)
    bot.get_followers_via_hiker(username=username)

@app.task(name='add_followers_to_close_freinds', time_limit=36000, soft_time_limit=34200)
def add_followers_to_close_freinds(user, username):

    bot = InstagramBot(user=user)
    bot.add_to_close_friends(username=username)