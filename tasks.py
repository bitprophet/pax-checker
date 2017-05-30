import logging
import os
import time
import traceback

from invoke import task
import pypd
import tweepy


logger = logging.getLogger(__file__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(getattr(logging, os.environ.get('LOGLEVEL', 'INFO')))


@task(name='check-loop')
def check_loop(c):
    # The stream listener will, sans any issues, block/loop internally
    # forever. Here, we just want to kickstart it if it gets disconnected.
    while True:
        try:
            logger.info("Starting to stream tweets...")
            stream_tweets(c)
        # TODO: what's recoverable exactly?
        except Exception as e:
            logger.error("Got exception! {!r}".format(e))
            traceback.print_exc()
            logger.error("Trying to recover...back to top of loop, after sleep")
        # >60s sleep to ensure we don't hit rate limiting
        time.sleep(120)


def twitter_auth(c):
    auth = tweepy.OAuthHandler(
        c.twitter.consumer_key,
        c.twitter.consumer_secret,
    )
    auth.set_access_token(
        c.twitter.access_token,
        c.twitter.access_secret,
    )
    return auth


class Anxious(tweepy.StreamListener):
    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context')
        super(Anxious, self).__init__(*args, **kwargs)

    def on_status(self, status):
        url = "https://twitter.com/{}/status/{}".format(
            status.user.screen_name,
            status.id,
        )
        # Only alert on real tweets, not replies, PAX acct definitely replies
        # to @-messages sometimes and I don't want to get paged on those!
        if status.in_reply_to_status_id:
            logger.debug("Skipping a mention ({})".format(url))
            return
        # ALSO skip anything sent TO that account, which inexplicably shows up
        # here too...oh, Twitter.
        if status.user.id != self.context.twitter.follow_id:
            logger.debug("Skipping a non-reply mention ({})".format(url))
            return
        text = status.text.encode('ascii', errors='replace')
        logger.info("Tweet seen: {} ({})".format(text, url))
        send_page(self.context, url, text)

    def on_error(self, status_code):
        logger.error("Error {}!".format(status_code))
        if status_code == 420:
            logger.critical("Got a 420 (rate limit warning), disconnecting!")
            return False


@task(name='stream-tweets')
def stream_tweets(c):
    auth = twitter_auth(c)
    stream = tweepy.Stream(auth=auth, listener=Anxious(context=c))
    # This will block until disconnected...
    stream.filter(follow=[str(c.twitter.follow_id)])


@task(name='send-page')
def send_page(c, url, text=None):
    # This is how to configure pypd. Mehhhhh
    pypd.api_key = c.pagerduty.api_key
    pypd.Event.create(data={
        'service_key': c.pagerduty.service_key,
        'event_type': 'trigger',
        'description': 'Tweet alert!',
        'contexts': [
              {
                  'type': 'link',
                  'href': url,
                  'text': text,
              },
        ],
    })


# TODO: invocations?

@task(name='lock-deps')
def lock_deps(c):
    c.run("pip-compile --no-index")
    c.run("pip-sync")


@task(name='push-config')
def push_config(c):
    # Push any updated .env file contents (...ALSO triggers restart)
    c.run("heroku config:push -o")


@task
def deploy(c):
    # Push to my own repo
    c.run("git push", pty=True)
    # Push to heroku (triggers restart)
    c.run("git push heroku HEAD", pty=True)
