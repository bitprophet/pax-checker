import time
import traceback

from invoke import task
import pypd
import tweepy


@task(name='check-loop')
def check_loop(c):
    # The stream listener will, sans any issues, block/loop internally
    # forever. Here, we just want to kickstart it if it gets disconnected.
    while True:
        try:
            stream_tweets(c)
        # TODO: what's recoverable exactly?
        except Exception as e:
            print("Got exception! {!r}".format(e))
            traceback.print_exc()
            print("Trying to recover...back to top of loop, after sleep")
        time.sleep(60)


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
            print("Skipping a mention ({})".format(url))
            return
        print("Status: {} ({})".format(status, url))
        send_page(self.context, url, status.text)

    def on_error(self, status_code):
        print("Error {}!".format(status_code))
        if status_code == 420:
            print("Got a 420 (rate limit warning), disconnecting!")
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
