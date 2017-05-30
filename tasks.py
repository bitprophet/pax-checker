from invoke import task
import pypd
import tweepy


@task(name='check-loop')
def check_loop(c):
    # TODO:
    # - check PAX public twitter feed
    # - loop
    # - when any public tweet:
    # - send page
    # - link to the tweet itself probably
    pass


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
    def on_status(self, status):
        # Only alert on real tweets, not replies, PAX acct definitely replies
        # to @-messages sometimes and I don't want to get paged on those!
        if not status.in_reply_to_status_id:
            print("Status: {}".format(status))

    def on_error(self, status_code):
        print("Error {}!".format(status_code))


@task(name='stream-tweets')
def stream_tweets(c):
    auth = twitter_auth(c)
    stream = tweepy.Stream(auth=auth, listener=Anxious())
    stream.filter(follow=[str(c.twitter.follow_id)])


@task(name='send-page')
def send_page(c, url):
    # This is how to configure pypd. Mehhhhh
    pypd.api_key = c.pagerduty.api_key
    pypd.Event.create(data={
        'service_key': c.pagerduty.service_key,
        'event_type': 'trigger',
        'description': 'o shit pax tweeted?!',
        'contexts': [
              {
                  'type': 'link',
                  'href': url,
                  'text': 'Link to tweet!',
              },
        ],
    })
